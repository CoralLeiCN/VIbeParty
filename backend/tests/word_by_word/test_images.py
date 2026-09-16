"""WW-CAT-01: round image ownership, source selection, and bounded Codex execution."""

import asyncio
import io
import json
import os
import sys

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.app import create_app
from backend.games.word_by_word import images, integration
from backend.games.word_by_word.domain import FIXTURE_TEXT
from backend.games.word_by_word.images import CodexImageGenerator, ImagePreparationError
from backend.games.word_by_word.live import LingBotProvider, LiveSettings
from backend.shared.config import Settings

API = "/api/games/word-by-word"
ORIGIN = "http://testserver"


def png():
    output = io.BytesIO()
    Image.new("RGB", (48, 32), "green").save(output, format="PNG")
    return output.getvalue()


@pytest.fixture
def client(tmp_path, monkeypatch):
    async def ready(_):
        return None

    monkeypatch.setattr("backend.games.word_by_word.service.codex_unavailable_reason", ready)
    settings = Settings(
        _env_file=None, media_root=tmp_path, public_origin=ORIGIN, browser_origin=ORIGIN
    )
    with TestClient(create_app(settings, [integration])) as client:
        client.headers["Origin"] = ORIGIN
        integration.game.live_reason = None
        integration.game.live_settings = LiveSettings(_env_file=None)
        yield client


def test_upload_auth_validation_round_isolation_and_explicit_source(client):
    state = client.post(API + "/host", json={}).json()
    host = client.cookies.get(integration.COOKIE)
    rid = state["round_id"]
    url = f"{API}/round/{rid}/starting-image"
    fields = {"round_id": rid}
    client.post(API + "/room/settings", json={**fields, "player_count": 1})
    assert (
        client.put(
            url, content=png(), headers={"Content-Type": "image/png", "Origin": "http://evil"}
        ).status_code
        == 403
    )
    assert client.put(url, content=png(), headers={"Content-Type": "text/plain"}).status_code == 415
    assert (
        client.put(
            url, content=b"\x89PNG\r\n\x1a\ninvalid", headers={"Content-Type": "image/png"}
        ).status_code
        == 422
    )
    assert (
        client.put(
            url, content=b"x" * (images.MAX_UPLOAD_BYTES + 1), headers={"Content-Type": "image/png"}
        ).status_code
        == 413
    )
    client.cookies.clear()
    assert client.put(url, content=png(), headers={"Content-Type": "image/png"}).status_code == 401
    player_state = client.post(API + "/join", json={"code": state["code"], "name": "Ada"}).json()
    player = client.cookies.get(integration.COOKIE)
    assert "image_sources" not in player_state
    assert client.put(url, content=png(), headers={"Content-Type": "image/png"}).status_code == 403
    assert client.get(url).status_code == 403
    client.cookies.clear()
    client.cookies.set(integration.COOKIE, host)
    assert (
        client.post(
            API + "/round/image-source", json={**fields, "image_source": "upload"}
        ).status_code
        == 200
    )
    assert (
        client.post(API + "/round/start", json={**fields, "mode": "live"}).json()["code"]
        == "image_source_unavailable"
    )
    response = client.put(url, content=png(), headers={"Content-Type": "image/png"})
    assert response.status_code == 200
    uploaded = response.json()
    assert uploaded["image_source"] == "upload" and uploaded["uploaded_image_url"]
    preview = client.get(uploaded["uploaded_image_url"])
    assert preview.status_code == 200 and preview.headers["cache-control"] == "no-store"
    assert Image.open(io.BytesIO(preview.content)).size == (48, 32)
    assert (
        client.post(API + "/round/image-source", json={**fields, "image_source": "api"}).status_code
        == 200
    )
    assert client.post(API + "/round/start", json={**fields, "mode": "live"}).status_code == 503
    client.post(API + "/round/image-source", json={**fields, "image_source": "upload"})
    assert client.post(API + "/round/start", json={**fields, "mode": "live"}).status_code == 200
    assert client.put(url, content=png(), headers={"Content-Type": "image/png"}).status_code == 409
    assert (
        client.post(
            API + "/round/image-source", json={**fields, "image_source": "codex"}
        ).status_code
        == 409
    )
    client.post(API + "/round/end", json=fields)
    next_round = client.post(API + "/round/new", json=fields).json()
    assert next_round["uploaded_image_url"] is None and next_round["image_source"] == "codex"
    assert client.get(url).status_code == 409
    assert client.put(url, content=png(), headers={"Content-Type": "image/png"}).status_code == 409
    assert list(integration.game.media.iterdir()) == []
    client.cookies.clear()
    client.cookies.set(integration.COOKIE, player)
    assert "uploaded_image_url" not in client.get(API + "/state").json()


@pytest.mark.parametrize("content", [b"not an image", b"<svg></svg>"])
def test_invalid_images_are_rejected(content):
    with pytest.raises(ImagePreparationError):
        images.validated_image(content)


@pytest.mark.parametrize("format", ["JPEG", "PNG", "WEBP"])
def test_supported_formats_are_normalized_and_metadata_removed(format):
    source = Image.new("RGB", (48, 32), "green")
    exif = Image.Exif()
    exif[274] = 6  # Rotate a phone photo upright.
    exif[315] = "Private metadata"
    buffer = io.BytesIO()
    source.save(buffer, format=format, exif=exif)
    with Image.open(io.BytesIO(images.validated_image(buffer.getvalue()))) as result:
        assert result.format == "PNG" and result.size == (32, 48)
        assert not result.getexif()


def test_oversize_pixels_and_animated_images_are_rejected(monkeypatch):
    monkeypatch.setattr(images, "MAX_PIXELS", 10)
    with pytest.raises(ImagePreparationError):
        images.validated_image(png())
    monkeypatch.setattr(images, "MAX_PIXELS", 16_000_000)
    output = io.BytesIO()
    Image.new("RGB", (32, 32), "red").save(
        output,
        format="PNG",
        save_all=True,
        append_images=[Image.new("RGB", (32, 32), "blue")],
        duration=100,
        loop=0,
    )
    with pytest.raises(ImagePreparationError):
        images.validated_image(output.getvalue())


async def test_selected_codex_ignores_configured_seed_and_receives_place_only(
    tmp_path, monkeypatch
):
    configured = tmp_path / "configured.png"
    configured.write_bytes(b"invalid override must not be read")
    calls = []

    async def generate(self, place, directory):
        calls.append(place)
        target = directory / "seed.png"
        target.write_bytes(png())
        return target

    monkeypatch.setattr(CodexImageGenerator, "generate", generate)
    provider = LingBotProvider(
        LiveSettings(_env_file=None, word_by_word_seed_image=configured), image_source="codex"
    )
    assert (await provider.starting_image(FIXTURE_TEXT[0], tmp_path)).read_bytes() == png()
    assert calls == ["Enchanted forest"]
    assert provider.evidence["seed_source"] == "codex"


def fake_codex(tmp_path, monkeypatch, mode="success"):
    # A standalone process exercises argv/stdin, schema output, termination and artifact boundaries.
    codex_home = tmp_path / "test-codex"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    command = tmp_path / "codex-fake"
    command.write_text(f"""#!{sys.executable}
import base64, json, os, sys, time
from pathlib import Path
args = sys.argv[1:]
prompt = sys.stdin.read()
request = {{"args": args, "prompt": prompt, "env": dict(os.environ), "pid": os.getpid()}}
Path({str(tmp_path / "invocation.json")!r}).write_text(json.dumps(request))
thread = "11111111-1111-1111-1111-111111111111"
folder = Path(os.environ["CODEX_HOME"]) / "generated_images" / thread
folder.mkdir(parents=True)
print(json.dumps({{"type": "thread.started", "thread_id": thread}}), flush=True)
if {mode!r} == "hang":
    time.sleep(60)
if {mode!r} == "failed":
    sys.exit(1)
path = folder / "image.png"
path.write_bytes(base64.b64decode({__import__("base64").b64encode(png()).decode()!r}))
if {mode!r} == "outside":
    path = Path({str(tmp_path / "unrelated.png")!r})
    path.write_bytes(b"do not read or delete")
if {mode!r} == "missing":
    path.unlink()
result = Path(args[args.index("--output-last-message") + 1])
result.write_text(json.dumps({{"image_path": str(path)}}))
print(json.dumps({{"type": "turn.completed"}}), flush=True)
""")
    command.chmod(0o700)
    return command, codex_home


async def test_codex_artifact_round_trip_and_restricted_execution(tmp_path, monkeypatch):
    monkeypatch.setenv("REACTOR_API_KEY", "must-not-leak")
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-leak")
    command, codex_home = fake_codex(tmp_path, monkeypatch)
    destination = await CodexImageGenerator(str(command)).generate(FIXTURE_TEXT[0], tmp_path)
    assert destination.read_bytes() == png()
    request = json.loads((tmp_path / "invocation.json").read_text())
    assert FIXTURE_TEXT[0] in request["prompt"]
    assert all(text not in request["prompt"] for text in FIXTURE_TEXT[1:])
    assert "must-not-leak" not in json.dumps(request)
    assert "read-only" in request["args"] and "--ignore-user-config" in request["args"]
    assert "shell_tool" in request["args"] and "apps" in request["args"]
    assert list((codex_home / "generated_images").iterdir()) == []


@pytest.mark.parametrize("mode", ["outside", "missing", "failed", "hang"])
async def test_codex_failure_is_bounded_and_cleans_artifacts(tmp_path, monkeypatch, mode):
    command, codex_home = fake_codex(tmp_path, monkeypatch, mode)
    with pytest.raises(ImagePreparationError):
        await CodexImageGenerator(str(command), timeout=2).generate(FIXTURE_TEXT[0], tmp_path)
    assert not (tmp_path / "seed.png").exists()
    request = json.loads((tmp_path / "invocation.json").read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(request["pid"], 0)
    assert list((codex_home / "generated_images").iterdir()) == []
    if mode == "outside":
        assert (tmp_path / "unrelated.png").read_bytes() == b"do not read or delete"


async def test_cancelling_codex_terminates_process(tmp_path, monkeypatch):
    command, codex_home = fake_codex(tmp_path, monkeypatch, "hang")
    task = asyncio.create_task(
        CodexImageGenerator(str(command)).generate(FIXTURE_TEXT[0], tmp_path)
    )
    async with asyncio.timeout(3):
        while not (tmp_path / "invocation.json").exists():
            await asyncio.sleep(0.01)
        await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    request = json.loads((tmp_path / "invocation.json").read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(request["pid"], 0)
    assert not (tmp_path / "seed.png").exists()
    assert list((codex_home / "generated_images").iterdir()) == []


@pytest.mark.parametrize("failure", ["missing", "login", "image_tool"])
async def test_codex_readiness_distinguishes_configuration(failure, monkeypatch):
    monkeypatch.setattr(images.shutil, "which", lambda _: None if failure == "missing" else "codex")

    async def output(*args):
        if "--help" in args:
            return 0, "--ignore-user-config"
        if "login" in args:
            return (1, "Not logged in") if failure == "login" else (0, "Logged in using ChatGPT")
        return 0, "image_generation stable false"

    monkeypatch.setattr(images, "cli_output", output)
    reason = await images.codex_unavailable_reason("codex")
    expected = {"missing": "Install", "login": "codex login", "image_tool": "image generation"}
    assert expected[failure] in reason
