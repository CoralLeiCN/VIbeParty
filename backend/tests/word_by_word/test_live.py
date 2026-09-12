"""Protocol/capture checks with synthetic frames and mocked HTTP only; no live evidence."""

import asyncio
import json

import httpx
import pytest

from backend.games.word_by_word.domain import FIXTURE_TEXT
from backend.games.word_by_word.live import CaptureError, FastH3Provider, FrameCapture, LiveSettings
from backend.games.word_by_word.providers import scene_prompt


class FakeReactor:
    def __init__(self):
        self.callbacks = {}
        self.commands = []
        self.session_id = "our-session"
        self.released = False
        self.ambiguous = False
        self.setting_ack = True
        self.fail_connect = False
        self.fail_play = False
        self.streams = []
        self.provider = None

    def on(self, event, callback):
        self.callbacks[event] = callback

    def track(self, name):
        assert name == "main_video"
        return self

    def on_raw_frame(self, callback):
        self.frame = callback

    async def connect(self):
        if self.fail_connect:
            raise RuntimeError("lost creation acknowledgment")
        self.callbacks["session_id_changed"](self.session_id)

    def emit(self, kind, clip):
        self.callbacks["message"]({"type": kind, "data": {"clip": clip}})

    async def send_command(self, name, data):
        self.commands.append((name, data))
        if name.startswith("set_"):
            reply = {
                "set_autoplay": "autoplay_accepted",
                "set_canvas": "canvas_accepted",
                "set_flush_on_clip_end": "flush_accepted",
            }[name]
            return {"type": reply, "data": {}} if self.setting_ack else None
        if name == "enqueue":
            if self.ambiguous:
                return None
            count = sum(n == "enqueue" for n, _ in self.commands)
            clip = {"clip_id": f"clip-{count}", "frames": 141}
            self.emit("clip_generated", clip)  # Broadcast may precede command completion.
            return {"type": "clip_queued", "data": {"clip": clip}}
        if name == "play":
            if self.fail_play:
                self.callbacks["error"]("synthetic failure")
                return None
            self.streams.append(asyncio.create_task(self.stream(data["clip_id"])))
        return None

    async def stream(self, clip_id):
        capture = self.provider.capture
        self.frame(bytes(32 * 32 * 4), 32, 32, -1, -1, b"")  # Idle frame before start.
        self.emit("clip_started", {"clip_id": "unrelated"})
        self.frame(bytes(32 * 32 * 4), 32, 32, -1, -1, b"")
        self.emit("clip_started", {"clip_id": clip_id})
        # Finish at the sender can precede the delivery of buffered frames.
        self.emit("clip_finished", {"clip_id": clip_id})
        for i in range(141):
            while capture.frames.qsize() >= 2:
                await asyncio.sleep(0.001)
            self.frame(bytes([i % 256, 100, 200, 255]) * 32 * 32, 32, 32, i, i * 41667, b"")
            await asyncio.sleep(0.001)

    async def disconnect(self):
        for task in self.streams:
            if not task.done():
                task.cancel()
        await asyncio.gather(*self.streams, return_exceptions=True)

    def close(self):
        self.released = True


def adapter(tmp_path, *, states=None):
    requests = []
    states = iter(states or [(200, {"state": "CLOSED"})])
    reactor = FakeReactor()

    def http(request):
        requests.append(request)
        if request.url.path == "/tokens":
            return httpx.Response(200, json={"jwt": "scoped-test-token"})
        assert request.url.path == "/sessions/our-session"
        assert request.headers["Authorization"] == "Bearer scoped-test-token"
        assert request.headers["Reactor-API-Version"] == "1"
        if request.method == "DELETE":
            return httpx.Response(204)
        code, payload = next(states)
        return httpx.Response(code, json=payload)

    def factory(**kwargs):
        assert kwargs == {"model_name": "reactor/fast-h3", "jwt": "scoped-test-token"}
        return reactor

    provider = FastH3Provider(
        "rk_test-only",
        client_factory=lambda: httpx.AsyncClient(transport=httpx.MockTransport(http)),
        reactor_factory=factory,
        evidence_path=tmp_path / "evidence.json",
    )
    reactor.provider = provider
    return provider, reactor, requests


@pytest.mark.asyncio
async def test_scoped_additive_protocol_and_saved_capture(tmp_path):
    provider, reactor, requests = adapter(tmp_path)
    async with asyncio.timeout(10):
        await provider.open()
        for index in range(4):
            saved = await provider.segment(list(FIXTURE_TEXT), index, tmp_path / f"{index}.mp4")
            assert saved.duration == pytest.approx(141 / 24)
            assert (saved.width, saved.height) == (32, 32)
        assert await provider.close()
    token = json.loads(requests[0].content)
    assert token == {
        "expires_after": 900,
        "authorization_details": [
            {
                "type": "session",
                "resources": {"models": {"match": ["reactor/fast-h3"]}},
                "constraints": {"max_sessions": 1, "max_session_duration_seconds": 180},
            }
        ],
    }
    enqueue = [data for name, data in reactor.commands if name == "enqueue"]
    for i, data in enumerate(enqueue):
        assert data["prompt"] == scene_prompt(list(FIXTURE_TEXT), i)
        assert data["continue_from_clip_id"] == (f"clip-{i}" if i else "")
    assert reactor.released and len(enqueue) == 4
    report = json.loads((tmp_path / "evidence.json").read_text())
    assert report["closed"] and len(report["clips"]) == 4
    assert all(c["first_frame_id"] == 0 and c["received_frames"] == 141 for c in report["clips"])
    assert not list(tmp_path.glob("*.partial.mp4"))
    assert "scoped-test-token" not in json.dumps(report)
    assert "rk_test-only" not in json.dumps(report)
    assert FIXTURE_TEXT[0] not in json.dumps(report)
    assert len(list(tmp_path.glob("*.mp4"))) == 4  # Remains after independent closure.


@pytest.mark.asyncio
async def test_ambiguous_enqueue_is_never_retried(tmp_path):
    provider, reactor, requests = adapter(tmp_path)
    await provider.open()
    reactor.ambiguous = True
    with pytest.raises(CaptureError, match="ambiguous_enqueue"):
        await provider.segment(list(FIXTURE_TEXT), 0, tmp_path / "0.mp4")
    assert sum(n == "enqueue" for n, _ in reactor.commands) == 1
    assert not provider.next_index and not list(tmp_path.glob("*.mp4"))
    assert await provider.close()
    assert sum(r.method == "POST" for r in requests) == 1


@pytest.mark.asyncio
async def test_unconfirmed_settings_stop_before_enqueue(tmp_path):
    provider, reactor, _ = adapter(tmp_path)
    reactor.setting_ack = False
    with pytest.raises(CaptureError, match="unconfirmed_session_settings"):
        await provider.open()
    assert all(n != "enqueue" for n, _ in reactor.commands)
    assert await provider.close()


@pytest.mark.parametrize(
    "status,payload", [(200, {"state": "CLOSED"}), (200, {"state": "INACTIVE"}), (404, {})]
)
@pytest.mark.asyncio
async def test_only_independent_terminal_state_confirms_close(tmp_path, status, payload):
    provider, reactor, requests = adapter(tmp_path, states=[(status, payload)])
    await provider.open()
    assert await provider.close()
    assert reactor.released
    assert [r.method for r in requests] == ["POST", "GET"]
    assert await provider.close()  # Duplicate cleanup performs no second network operation.
    assert len(requests) == 2


@pytest.mark.asyncio
async def test_disconnect_ack_and_delete_ack_do_not_clear_active_guard(tmp_path):
    provider, reactor, requests = adapter(
        tmp_path,
        states=[
            (200, {"state": "ACTIVE"}),
            (200, {"state": "SUSPENDED"}),
            (200, {"state": "CLOSED"}),
        ],
    )
    await provider.open()
    assert not await provider.close()
    assert not provider.closed and not reactor.released
    assert json.loads((tmp_path / "evidence.json").read_text())["closed"] is False
    assert await provider.close()
    assert [r.method for r in requests] == ["POST", "GET", "DELETE", "GET", "GET"]


@pytest.mark.asyncio
async def test_unavailable_closure_endpoint_preserves_guard(tmp_path):
    provider, reactor, _ = adapter(tmp_path, states=[(403, {}), (200, {"state": "CLOSED"})])
    await provider.open()
    with pytest.raises(httpx.HTTPStatusError):
        await provider.close()
    assert not provider.closed and not reactor.released
    assert await provider.close()


@pytest.mark.asyncio
async def test_lost_session_identity_never_implies_closed(tmp_path):
    provider, reactor, requests = adapter(tmp_path)
    reactor.fail_connect = True
    with pytest.raises(RuntimeError):
        await provider.open()
    assert not await provider.close()
    assert len(requests) == 1 and not reactor.released
    with pytest.raises(CaptureError, match="already_attempted"):
        await provider.open()


@pytest.mark.asyncio
async def test_provider_failure_aborts_pending_capture(tmp_path):
    provider, reactor, _ = adapter(tmp_path)
    await provider.open()
    reactor.fail_play = True
    with pytest.raises(CaptureError, match="provider_session_failed"):
        await asyncio.wait_for(provider.segment(list(FIXTURE_TEXT), 0, tmp_path / "0.mp4"), 1)
    assert provider.capture is None and not list(tmp_path.glob("*.mp4"))
    assert await provider.close()


@pytest.mark.asyncio
async def test_capture_overflow_invalidates_output(tmp_path):
    capture = FrameCapture(tmp_path / "0.mp4", 141)
    capture.accepting = True
    for i in range(9):
        capture.accept(bytes(16), 2, 2, i, i, b"")
    assert capture.frames.qsize() == 8 and capture.error == "frame_queue_overflow"
    with pytest.raises(CaptureError, match="overflow"):
        await capture.write()
    assert not list(tmp_path.glob("*.mp4"))


@pytest.mark.asyncio
async def test_capture_cancel_removes_partial_and_ignores_late_frames(tmp_path):
    capture = FrameCapture(tmp_path / "0.mp4", 141)
    capture.accepting = True
    capture.task = asyncio.create_task(capture.write())
    capture.accept(bytes(32 * 32 * 4), 32, 32, 0, 0, b"")
    while capture.process is None:
        await asyncio.sleep(0.001)
    await capture.abort()
    capture.accept(bytes(32 * 32 * 4), 32, 32, 1, 1, b"")
    assert capture.received == 1 and capture.process.returncode is not None
    assert not list(tmp_path.glob("*.mp4"))


@pytest.mark.asyncio
async def test_cleanup_cancellation_is_bounded_and_keeps_guard(tmp_path):
    provider, reactor, _ = adapter(tmp_path)
    await provider.open()

    async def hang():
        await asyncio.Event().wait()

    reactor.disconnect = hang
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(provider.close(), 0.01)
    assert not provider.closed and not reactor.released


def test_live_gate_requires_capture_prompt_slot_and_previous_closure():
    settings = LiveSettings(_env_file=None)
    assert settings.unavailable_reason()
    settings.word_by_word_live_enabled = True
    settings.word_by_word_capture_verified = True
    assert settings.unavailable_reason()
    settings.word_by_word_prompt_limit_verified = True
    assert settings.unavailable_reason()
    settings.word_by_word_live_slot = "allocated-test-slot"
    settings.word_by_word_previous_session_closed = True
    assert settings.unavailable_reason()
    from pydantic import SecretStr

    settings.reactor_api_key = SecretStr("rk_test-only")
    assert settings.unavailable_reason() is None
