"""Protocol/capture checks with synthetic frames and mocked HTTP only; no live evidence."""

import asyncio
import json
import time

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
        self.compact_generated = False
        self.queue_metadata_only = False
        self.zero_frame_metadata = False
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
            event_clip = {"clip_id": clip["clip_id"]} if self.compact_generated else clip
            self.emit("clip_generated", event_clip)  # Broadcast may precede command completion.
            ack = {"clip_id": clip["clip_id"]} if self.queue_metadata_only else clip
            return {"type": "clip_queued", "data": {"clip": ack}}
        if name == "get_queue":
            return {
                "type": "queue_update",
                "data": {"playout": [{"clip_id": "clip-1", "frames": 141.0}]},
            }
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
            frame_id, timestamp = (0, 0) if self.zero_frame_metadata else (i, i * 41667 + 1)
            self.frame(bytes([i % 256, 100, 200, 255]) * 32 * 32, 32, 32, frame_id, timestamp, b"")
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
    assert all(step["frame_id_gaps"] == 0 for step in report["steps"])
    assert all(step["finish_event_to_last_frame_seconds"] > 0 for step in report["steps"])
    assert [step["continued"] for step in report["steps"]] == [False, True, True, True]
    assert report["closure_checks"] == [{"http_status": 200, "state": "CLOSED"}]
    assert not list(tmp_path.glob("*.partial.mp4"))
    assert "scoped-test-token" not in json.dumps(report)
    assert "rk_test-only" not in json.dumps(report)
    assert FIXTURE_TEXT[0] not in json.dumps(report)
    assert len(list(tmp_path.glob("*.mp4"))) == 4  # Remains after independent closure.


@pytest.mark.asyncio
async def test_absent_optional_frame_metadata_is_reported_without_claiming_no_gaps(tmp_path):
    provider, reactor, _ = adapter(tmp_path)
    reactor.zero_frame_metadata = True
    await provider.open()
    async with asyncio.timeout(5):
        await provider.segment(list(FIXTURE_TEXT), 0, tmp_path / "0.mp4")
    assert await provider.close()
    report = provider.evidence["clips"][0]
    assert report["metadata_missing_frames"] == report["received_frames"] == 141
    assert report["first_frame_id"] is None and report["frame_id_gaps"] is None


@pytest.mark.asyncio
async def test_native_frame_burst_during_encoder_startup_saves_every_frame(tmp_path, monkeypatch):
    width, height, frame_count = 1344, 768, 158
    capture = FrameCapture(tmp_path / "burst.mp4", frame_count)
    capture.accepting = True
    encoder_starting = asyncio.Event()
    release_encoder = asyncio.Event()
    create_process = asyncio.create_subprocess_exec

    async def delayed_encoder(*args, **kwargs):
        encoder_starting.set()
        await release_encoder.wait()
        return await create_process(*args, **kwargs)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", delayed_encoder)

    def frame_color(index):
        return (32 + index % 6 * 40, 32 + index // 6 % 6 * 40, 32 + index // 36 * 40)

    def send_frame(index):
        red, green, blue = frame_color(index)
        pixels = bytes([blue, green, red, 255]) * width * height
        capture.accept(pixels, width, height, 0, 0, b"")

    def startup_burst():
        # Native delivery cannot inspect the app queue or wait for FFmpeg startup.
        for index in range(1, 25):
            send_frame(index)

    def remaining_frames():
        for index in range(25, frame_count):
            time.sleep(1 / 24)
            send_frame(index)

    capture.task = asyncio.create_task(capture.write())
    try:
        async with asyncio.timeout(20):
            send_frame(0)
            await encoder_starting.wait()
            await asyncio.to_thread(startup_burst)
            assert capture.error is None
            release_encoder.set()
            # A sender finish event may arrive before all buffered frames.
            capture.finished.set()
            await asyncio.to_thread(remaining_frames)
            saved = await capture.task
            assert (saved.width, saved.height) == (width, height)
            assert saved.duration == pytest.approx(frame_count / 24, abs=0.001)
            assert capture.received == frame_count and capture.queue_peak >= 24
            decoder = await create_process(
                "ffmpeg",
                "-v",
                "error",
                "-i",
                str(saved.path),
                "-vf",
                "scale=1:1",
                "-pix_fmt",
                "rgb24",
                "-f",
                "rawvideo",
                "pipe:1",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            pixels, errors = await decoder.communicate()
            assert decoder.returncode == 0, errors
            assert len(pixels) == frame_count * 3
            # Unique, well-separated colors detect dropped, duplicated or reordered frames.
            for index in range(frame_count):
                actual = pixels[index * 3 : (index + 1) * 3]
                assert all(abs(a - e) <= 4 for a, e in zip(actual, frame_color(index), strict=True))
    finally:
        release_encoder.set()
        await capture.abort()
    assert not list(tmp_path.glob("*.partial.mp4"))


def test_duplicate_meaningful_frame_metadata_still_invalidates_capture(tmp_path):
    capture = FrameCapture(tmp_path / "0.mp4", 141)
    capture.accepting = True
    capture.accept(bytes(16), 2, 2, 0, 1, b"")
    capture.accept(bytes(16), 2, 2, 0, 41668, b"")
    assert capture.error == "non_monotonic_frame_ids" and capture.received == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("queue_only", [False, True])
async def test_compact_generated_event_preserves_or_reads_frame_metadata(tmp_path, queue_only):
    provider, reactor, _ = adapter(tmp_path)
    reactor.compact_generated = True
    reactor.queue_metadata_only = queue_only
    await provider.open()
    async with asyncio.timeout(5):
        clip = await provider.segment(list(FIXTURE_TEXT), 0, tmp_path / "0.mp4")
    assert clip.duration == pytest.approx(141 / 24)
    assert sum(name == "enqueue" for name, _ in reactor.commands) == 1
    assert sum(name == "get_queue" for name, _ in reactor.commands) == int(queue_only)
    assert await provider.close()


@pytest.mark.asyncio
async def test_ambiguous_enqueue_is_never_retried(tmp_path):
    provider, reactor, requests = adapter(tmp_path)
    await provider.open()
    reactor.ambiguous = True
    with pytest.raises(CaptureError, match="ambiguous_enqueue"):
        await provider.segment(list(FIXTURE_TEXT), 0, tmp_path / "0.mp4")
    assert sum(n == "enqueue" for n, _ in reactor.commands) == 1
    assert not provider.next_index and not list(tmp_path.glob("*.mp4"))
    assert provider.evidence["phase"] == "enqueue"
    assert len(provider.evidence["steps"]) == 1
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
    evidence = json.loads((tmp_path / "evidence.json").read_text())
    assert evidence["closed"] is False
    assert [check["state"] for check in evidence["closure_checks"]] == ["ACTIVE", "SUSPENDED"]
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
@pytest.mark.parametrize("width,height,capacity", [(2, 2, 32), (1920, 1080, 16)])
async def test_capture_overflow_invalidates_output(tmp_path, width, height, capacity):
    capture = FrameCapture(tmp_path / "0.mp4", 141)
    capture.accepting = True
    frame = bytes(width * height * 4)
    for i in range(capacity + 1):
        capture.accept(frame, width, height, i, i + 1, b"")
    assert capture.frames.qsize() == capacity and capture.error == "frame_queue_overflow"
    assert capture.received == capacity
    assert capture.evidence()["queue_peak_bytes"] <= 128 * 1024 * 1024
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


def test_live_gate_requires_presenter_opt_in_and_credential():
    settings = LiveSettings(_env_file=None)
    assert settings.unavailable_reason()
    settings.word_by_word_live_enabled = True
    assert settings.unavailable_reason()
    from pydantic import SecretStr

    settings.reactor_api_key = SecretStr("rk_test-only")
    assert settings.unavailable_reason() is None
