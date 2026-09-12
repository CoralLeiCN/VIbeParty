import asyncio
import json
import sys
from types import SimpleNamespace

import httpx
import pytest

from backend.games.reverse_prompt.quota import Quota
from backend.games.reverse_prompt.reactor_video import HeliosProvider, download_recording


@pytest.mark.asyncio
async def test_disconnect_success_is_not_closure_proof(tmp_path):
    quota = Quota(tmp_path / "quota.json")
    quota.initialize()
    attempt = quota.consume()
    quota.session(attempt, "session")
    provider = HeliosProvider("unused", quota)

    class SDK:
        async def disconnect(self):
            pass  # Native SDK may swallow a failed DELETE.

    requests = []

    def handler(request):
        requests.append(request.method)
        return httpx.Response(200, json={"state": "ACTIVE"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(Exception):
            await provider._close(SDK(), client, "test-token", "session", attempt)
    assert requests == ["GET", "DELETE", "GET"]
    assert quota.read()["unresolved"]
    assert quota.read()["remaining"] == 8


@pytest.mark.asyncio
async def test_recording_manifest_order_and_credentials_stay_at_coordinator(tmp_path):
    observed = []

    def handler(request):
        observed.append((str(request.url), request.headers.get("authorization")))
        if request.url.path == "/playlist":
            return httpx.Response(
                200, text='#EXTM3U\n#EXT-X-MAP:URI="init.mp4"\nhttps://cdn.example/segment.m4s\n'
            )
        return httpx.Response(200, content=b"init" if request.url.path == "/init.mp4" else b"frame")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await download_recording(
            client,
            SimpleNamespace(playlist_url="https://api.reactor.inc/playlist"),
            "test-token",
            tmp_path / "video",
        )
    assert (tmp_path / "video").read_bytes() == b"initframe"
    assert observed[0][1] == "Bearer test-token" and observed[1][1] == "Bearer test-token"
    assert observed[2][1] is None


@pytest.fixture
def decoded_provider(tmp_path, monkeypatch):
    quota = Quota(tmp_path / "quota.json")
    quota.initialize()
    sessions, token_bodies = [], []
    start_received = asyncio.Event()

    class SDK:
        silent = False

        def __init__(self, model_name, jwt):
            assert model_name == "reactor/helios"
            self.session_id = f"session-{len(sessions)}"
            self.commands = []
            self.handlers = {}
            self.feeder = None
            self.closed = False
            sessions.append(self)

        def on(self, event, callback):
            self.handlers[event] = callback

        def track(self, name):
            assert name == "main_video"
            return self

        def on_raw_frame(self, callback):
            self.frame = callback

        async def connect(self):
            self.handlers["session_id_changed"](self.session_id)

        async def send_command(self, command, data):
            self.commands.append((command, data))
            if command == "start":
                start_received.set()
                if not self.silent:
                    self.feeder = asyncio.create_task(self.feed())

        async def feed(self):
            for _ in range(120):
                self.frame(bytes((0, 0, 255, 255)) * (640 * 384), 640, 384, 0, 0, b"")
                await asyncio.sleep(0.003)

        async def request_recording(self):
            raise AssertionError("Direct capture must not require provider recording")

        async def disconnect(self):
            if self.feeder:
                self.feeder.cancel()
                await asyncio.gather(self.feeder, return_exceptions=True)
            self.closed = True

        def close(self):
            assert self.closed

    def handler(request):
        if request.url.path == "/tokens":
            assert request.headers["Reactor-API-Key"] == "fake-key"
            token_bodies.append(json.loads(request.content))
            return httpx.Response(200, json={"jwt": "fake-token"})
        if request.method == "GET" and request.url.path.startswith("/sessions/"):
            sid = request.url.path.rsplit("/", 1)[1]
            session = next(s for s in sessions if s.session_id == sid)
            return httpx.Response(200, json={"state": "CLOSED" if session.closed else "ACTIVE"})
        raise AssertionError("Unexpected provider request")

    original_client = httpx.AsyncClient
    monkeypatch.setitem(sys.modules, "reactor_sdk", SimpleNamespace(Reactor=SDK))
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    return HeliosProvider("fake-key", quota), SDK, sessions, token_bodies, start_received


async def test_direct_capture_uses_fresh_sessions_and_current_prompt_only(
    decoded_provider, tmp_path
):
    provider, _, sessions, tokens, _ = decoded_provider
    for step, prompt in enumerate(("A red balloon.", "A blue train.")):
        path = await provider.generate(prompt, tmp_path / str(step), step)
        assert path.is_file()
        assert provider.last_evidence["capture_method"] == "decoded_frames"
        assert provider.last_evidence["frames"] == 120
        assert provider.last_evidence["duration"] == 5
        assert provider.last_evidence["closed"]
        assert [name for name, _ in sessions[step].commands] == [
            "set_sr_scale",
            "set_prompt",
            "start",
        ]
        assert sessions[step].commands[1][1]["prompt"].startswith(prompt + "\n\n")
    assert "balloon" not in sessions[1].commands[1][1]["prompt"]
    assert len(sessions) == len(tokens) == 2
    assert provider.quota.read()["remaining"] == 7
    assert not provider.quota.read()["unresolved"]
    for token in tokens:
        detail = token["authorization_details"][0]
        assert detail["resources"]["models"]["match"] == ["reactor/helios"]
        assert detail["constraints"] == {"max_sessions": 1, "max_session_duration_seconds": 90}


async def test_cancelled_frame_wait_closes_the_session_without_refunding(
    decoded_provider, tmp_path
):
    provider, sdk, sessions, _, started = decoded_provider
    sdk.silent = True
    task = asyncio.create_task(provider.generate("A red balloon.", tmp_path / "cancel", 0))
    await asyncio.wait_for(started.wait(), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert sessions[0].closed
    assert provider.quota.read()["remaining"] == 8
    assert not provider.quota.read()["unresolved"]
    assert provider.last_evidence["encoded_frames"] == 0
