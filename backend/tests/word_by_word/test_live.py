"""Protocol/transport checks. These do not judge generated visual quality."""

import asyncio
import base64
import io
import json
from pathlib import Path

import httpx
import pytest
from PIL import Image

from backend.games.word_by_word.domain import FIXTURE_TEXT, Clip
from backend.games.word_by_word.live import MODEL, LingBotProvider, LiveSettings
from backend.games.word_by_word.providers import scene_prompt
from backend.games.word_by_word.stream import StreamCapture


class FakeCapture:
    def __init__(self, directory):
        self.directory = directory
        self.frames = 1
        self.clock = 0
        self.stopped = False

    @property
    def seconds(self):
        self.clock += 1
        return self.clock

    def accept(self, *_):
        pass

    def start(self):
        pass

    def check(self):
        pass

    async def ready(self):
        pass

    async def finish(self):
        path = self.directory / "story.mp4"
        path.write_bytes(b"recording")
        return Clip(path, 24, 32, 32)

    async def stop(self):
        self.stopped = True


class FakeReactor:
    session_id = "our-session"

    def __init__(self):
        self.commands = []
        self.callbacks = {}
        self.released = False
        self.reject = None
        self.hold = None
        self.entered = asyncio.Event()

    def on(self, event, callback):
        self.callbacks[event] = callback

    def track(self, name):
        assert name == "main_video"
        return self

    def on_raw_frame(self, callback):
        self.frame = callback

    async def connect(self):
        self.callbacks["session_id_changed"](self.session_id)

    async def upload_file(self, path):
        assert Path(path).is_file()
        return {"upload_id": "seed-only"}

    async def send_command(self, name, data):
        self.commands.append((name, data))
        if name == self.hold:
            self.entered.set()
            await asyncio.sleep(60)
        if name == self.reject:
            self.callbacks["message"]({"type": "command_error"})
            return None
        kind = {
            "set_image": "image_accepted",
            "set_prompt": "prompt_accepted",
            "start": "generation_started",
            "pause": "generation_paused",
        }[name]
        self.callbacks["message"]({"type": kind})
        # Test asynchronous event acknowledgment independently of correlated replies.
        return None

    async def disconnect(self):
        pass

    def close(self):
        self.released = True


def adapter(tmp_path, states=None):
    reactor = FakeReactor()
    requests = []
    states = iter(states or ["CLOSED"])
    seed = tmp_path / "seed.png"
    Image.new("RGB", (32, 32), "green").save(seed)

    def http(request):
        requests.append(request)
        if request.url.path == "/tokens":
            return httpx.Response(200, json={"jwt": "private-token"})
        assert request.url.path == "/sessions/our-session"
        if request.method == "DELETE":
            return httpx.Response(204)
        return httpx.Response(200, json={"state": next(states)})

    def factory(**kwargs):
        assert kwargs == {"model_name": MODEL, "jwt": "private-token"}
        return reactor

    settings = LiveSettings(_env_file=None, reactor_api_key="rk_test", word_by_word_seed_image=seed)
    provider = LingBotProvider(
        settings,
        client_factory=lambda: httpx.AsyncClient(transport=httpx.MockTransport(http)),
        reactor_factory=factory,
        capture_factory=FakeCapture,
        evidence_path=tmp_path / "evidence.json",
        image_source="configured",
    )
    return provider, reactor, requests


@pytest.mark.parametrize("source", ["configured", "upload"])
async def test_one_session_four_prompt_updates_and_one_recording(tmp_path, source):
    provider, reactor, requests = adapter(tmp_path)
    provider.image_source = source
    provider.uploaded_image = tmp_path / "seed.png"
    updates = []

    async def update(index, timestamp):
        updates.append((index, timestamp))

    saved = await provider.run(list(FIXTURE_TEXT), tmp_path, update)
    assert saved.path.name == "story.mp4"
    assert await provider.close()
    commands = [name for name, _ in reactor.commands]
    assert commands == [
        "set_image",
        "set_prompt",
        "start",
        "set_prompt",
        "set_prompt",
        "set_prompt",
        "pause",
    ]
    prompts = [data["prompt"] for name, data in reactor.commands if name == "set_prompt"]
    assert prompts == [scene_prompt(list(FIXTURE_TEXT), i) for i in range(4)]
    assert [i for i, _ in updates] == [0, 1, 2, 3]
    for index, prompt in enumerate(prompts):
        assert all(text not in prompt for text in FIXTURE_TEXT[index + 1 :])
    authorization = json.loads(requests[0].content)["authorization_details"][0]
    assert authorization["resources"]["models"]["match"] == [MODEL]
    assert authorization["constraints"] == {"max_sessions": 1, "max_session_duration_seconds": 180}
    assert reactor.released
    evidence = (tmp_path / "evidence.json").read_text()
    assert "private-token" not in evidence and "rk_test" not in evidence
    assert FIXTURE_TEXT[0] not in evidence


async def test_rejected_prompt_stops_and_closes_without_restart(tmp_path):
    provider, reactor, _ = adapter(tmp_path, states=["ACTIVE", "CLOSED"])
    reactor.reject = "set_prompt"

    async def update(*_):
        pytest.fail("Rejected initial prompt must not reveal the scene")

    with pytest.raises(RuntimeError, match="provider_rejected_command"):
        await provider.run(list(FIXTURE_TEXT), tmp_path, update)
    assert await provider.close()
    assert "start" not in [name for name, _ in reactor.commands]


async def test_cancellation_and_unresolved_closure_keep_guard(tmp_path):
    provider, reactor, _ = adapter(tmp_path, states=["ACTIVE", "ACTIVE", "CLOSED"])
    reactor.hold = "set_image"

    async def update(*_):
        pass

    task = asyncio.create_task(provider.run(list(FIXTURE_TEXT), tmp_path, update))
    await reactor.entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not await provider.close()
    assert not reactor.released
    assert await provider.close()


async def test_starting_image_uses_only_place_and_does_not_retry(tmp_path):
    requests = []
    png = io.BytesIO()
    Image.new("RGB", (32, 32), "green").save(png, format="PNG")

    def http(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={"data": [{"b64_json": base64.b64encode(png.getvalue()).decode()}]},
        )

    provider = LingBotProvider(
        LiveSettings(
            _env_file=None, openai_api_key="secret", word_by_word_seed_image=tmp_path / "unused.png"
        ),
        client_factory=lambda: httpx.AsyncClient(transport=httpx.MockTransport(http)),
    )
    path = await provider.starting_image(FIXTURE_TEXT[0], tmp_path)
    assert path.exists() and len(requests) == 1
    payload = json.loads(requests[0].content)
    assert FIXTURE_TEXT[0] in payload["prompt"]
    assert all(text not in payload["prompt"] for text in FIXTURE_TEXT[1:])
    assert payload["n"] == 1
    assert await provider.close()  # No Reactor session was opened.


async def test_real_capture_publishes_hls_and_one_decodable_replay(tmp_path):
    capture = StreamCapture(tmp_path)
    capture.accept(bytes([10, 30, 90, 255]) * (32 * 32), 32, 32, 0, 0, b"")
    capture.start()
    async with asyncio.timeout(10):
        await capture.ready()
        await capture.wait_until(2)
        saved = await capture.finish()
    assert 2 <= saved.duration < 3
    assert saved.path.name == "story.mp4"
    assert "#EXT-X-ENDLIST" in (tmp_path / "index.m3u8").read_text()
    assert len(list(tmp_path.glob("*.mp4"))) == 1


def test_live_configuration_allows_upload_without_image_api_key(tmp_path):
    settings = LiveSettings(
        _env_file=None, word_by_word_live_enabled=True, reactor_api_key="rk_test"
    )
    assert settings.unavailable_reason() is None
    settings = LiveSettings(
        _env_file=None,
        word_by_word_live_enabled=True,
        reactor_api_key="rk_test",
        openai_api_key="configured",
    )
    assert settings.unavailable_reason() is None
