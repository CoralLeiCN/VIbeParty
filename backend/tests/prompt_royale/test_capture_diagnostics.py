import asyncio
import json
import logging
import time
from types import SimpleNamespace

import httpx
import pytest
import reactor_sdk

from backend.games.prompt_royale.config import RoyaleSettings
from backend.games.prompt_royale.helios import HeliosVideo
from backend.games.prompt_royale.media import probe
from backend.games.prompt_royale.providers import FIXTURES, ProviderFailure
from backend.games.prompt_royale.reactor_video import error_details


def test_structured_sdk_error_retains_quota_details_without_payload():
    from reactor_sdk.errors import RateLimitedError

    error = RateLimitedError(
        "private-jwt private-prompt", status=429, retry_after_ms=6000, operation="connect"
    )
    assert error_details(error) == [
        {
            "type": "RateLimitedError",
            "code": "RATE_LIMITED",
            "http_status": 429,
            "retry_after_ms": 6000,
        }
    ]


@pytest.mark.parametrize(
    "timestamps,arrival_span,stage,underlying_error",
    [
        ([], 7, "wait_for_frames", "TimeoutError"),
        ([0] * 180, 0, "wait_for_frames", "TimeoutError"),
        ([0] * 180, 7, "request_recording", "RuntimeError"),
        ([1_000_000, 7_000_000], 0, "request_recording", "RuntimeError"),
    ],
)
async def test_capture_failure_retains_stage_and_all_frames_without_secrets(
    tmp_path, monkeypatch, caplog, timestamps, arrival_span, stage, underlying_error
):
    now = 0.0
    monkeypatch.setattr(
        "backend.games.prompt_royale.reactor_video.time",
        SimpleNamespace(time=time.time, monotonic=lambda: now),
    )

    class FakeReactor:
        session_id = "test-session"

        def __init__(self, **kwargs):
            self.callbacks = {}

        def on(self, event, callback):
            self.callbacks[event] = callback

        def track(self, name):
            return self

        def on_raw_frame(self, callback):
            self.frame = callback

        async def connect(self):
            self.callbacks["session_id_changed"](self.session_id)

        async def send_command(self, name, data):
            nonlocal now
            self.callbacks["message"]({"type": "command_accepted", "data": data})
            if name == "start":
                for index, stamp in enumerate(timestamps):
                    now = arrival_span * index / max(1, len(timestamps) - 1)
                    self.frame(b"pixels", 1280, 768, 0, stamp, None)

        async def request_recording(self):
            raise RuntimeError("private-prompt private-jwt private-key")

        async def disconnect(self):
            pass

        def close(self):
            pass

    requests = []

    def respond(request):
        requests.append(request)
        if request.url.path == "/tokens":
            return httpx.Response(200, json={"jwt": "private-jwt", "expires_at": time.time() + 300})
        assert request.method == "GET" and request.url.path == "/sessions/test-session"
        return httpx.Response(200, json={"state": "CLOSED"})

    real_timeout = asyncio.timeout
    monkeypatch.setattr(
        asyncio, "timeout", lambda seconds: real_timeout(0.03 if seconds == 60 else seconds)
    )
    monkeypatch.setattr(reactor_sdk, "Reactor", FakeReactor)
    video = HeliosVideo(
        RoyaleSettings(_env_file=None, reactor_api_key="private-key"),
        tmp_path / "unresolved-provider.json",
        httpx.MockTransport(respond),
    )

    async def status(value):
        pass

    with caplog.at_level(logging.WARNING), pytest.raises(ProviderFailure):
        await video.generate("private-prompt", 42, tmp_path / "entry.mp4", 0, status)

    (diagnostic,) = (tmp_path / "diagnostics").glob("*.json")
    contents = diagnostic.read_text()
    evidence = json.loads(contents)
    assert evidence["stage"] == stage
    assert evidence["received_frames"] == len(timestamps)
    assert evidence["zero_timestamp_frames"] == timestamps.count(0)
    assert evidence["timestamped_frames"] == len(timestamps) - timestamps.count(0)
    assert evidence["confirmed_closed"] is True
    assert evidence["outcome"] == "failed"
    assert underlying_error in {error["type"] for error in evidence["errors"]}
    assert evidence["model_events"]["command_accepted"] == 4
    assert diagnostic.stat().st_mode & 0o777 == 0o600
    assert not video.journal.exists()
    assert sum(request.url.path == "/tokens" for request in requests) == 1
    for secret in ("private-key", "private-jwt", "private-prompt"):
        assert secret not in contents + caplog.text


async def test_preparation_error_is_retained_for_reused_source(tmp_path, monkeypatch):
    async def fail_preparation(*args):
        raise ValueError("private-source-detail")

    monkeypatch.setattr("backend.games.prompt_royale.reactor_video.prepare", fail_preparation)
    video = HeliosVideo(RoyaleSettings(_env_file=None), tmp_path / "unresolved-provider.json")

    async def status(value):
        pass

    with pytest.raises(ValueError):
        await video.generate(
            "private-prompt", 42, tmp_path / "entry.mp4", 0, status, tmp_path / "source.mp4"
        )

    (diagnostic,) = (tmp_path / "diagnostics").glob("*.json")
    evidence = json.loads(diagnostic.read_text())
    assert evidence["stage"] == "prepare_mp4"
    assert evidence["errors"] == [{"type": "ValueError"}]
    assert "private" not in diagnostic.read_text()


@pytest.mark.parametrize(
    "startup_timeout,startup_mode", [(None, "sdk"), (300, "sdk"), (300, "rest")]
)
async def test_zero_timestamps_can_complete_recording_download_and_real_mp4_preparation(
    tmp_path, monkeypatch, startup_timeout, startup_mode
):
    now = 0.0
    requests = []
    closed = False
    monkeypatch.setattr(
        "backend.games.prompt_royale.reactor_video.time",
        SimpleNamespace(time=time.time, monotonic=lambda: now),
    )

    class FakeReactor:
        session_id = "test-session"

        def __init__(self, **kwargs):
            self.callbacks = {}

        def on(self, event, callback):
            self.callbacks[event] = callback

        def track(self, name):
            return self

        def on_raw_frame(self, callback):
            self.frame = callback

        async def connect(self, *, session_id=None):
            nonlocal now
            assert session_id == (self.session_id if startup_mode == "rest" else None)
            now = 90 if startup_timeout else 0
            self.callbacks["session_id_changed"](self.session_id)
            self.callbacks["status_changed"]("ready")

        async def send_command(self, name, data):
            nonlocal now
            if name == "start":
                started = now
                for index in range(180):
                    now = started + index / 25
                    self.frame(b"pixels", 1280, 768, index, 0, None)

        async def request_recording(self):
            return SimpleNamespace(playlist_url="https://api.reactor.inc/recording.m3u8")

        async def disconnect(self):
            nonlocal closed
            closed = startup_mode == "sdk"  # SDK adoption leaves termination to our adapter.
            self.callbacks["status_changed"]("disconnected")

        def close(self):
            pass

    def respond(request):
        nonlocal closed
        requests.append(request)
        if request.url.path == "/tokens":
            payload = json.loads(request.content)
            cap = payload["authorization_details"][0]["constraints"]["max_session_duration_seconds"]
            assert cap == (startup_timeout or 0) + 60
            assert payload["expires_after"] >= cap + 20
            return httpx.Response(
                200,
                json={"jwt": "private-jwt", "expires_at": time.time() + payload["expires_after"]},
            )
        assert request.headers["Authorization"] == "Bearer private-jwt"
        if request.url.path == "/sessions":
            assert request.method == "POST"
            return httpx.Response(200, json={"session_id": "test-session", "state": "CREATED"})
        if request.url.path == "/recording.m3u8":
            return httpx.Response(200, text="#EXTM3U\n#EXTINF:5,\npart.mp4\n#EXT-X-ENDLIST\n")
        if request.url.path == "/part.mp4":
            return httpx.Response(200, content=(FIXTURES / "0.mp4").read_bytes())
        assert request.url.path == "/sessions/test-session"
        if request.method == "DELETE":
            closed = True
            return httpx.Response(200, json={})
        assert request.method == "GET"
        return httpx.Response(
            200,
            json={
                "state": "CLOSED" if closed else "ACTIVE",
                "capabilities": {"tracks": []},
                "selected_transport": {"protocol": "webrtc", "version": "1.0"},
            },
        )

    monkeypatch.setattr(reactor_sdk, "Reactor", FakeReactor)
    settings = RoyaleSettings(_env_file=None, reactor_api_key="private-key")
    observed = []
    video = HeliosVideo(
        settings,
        tmp_path / "unresolved-provider.json",
        httpx.MockTransport(respond),
        startup_timeout=startup_timeout,
        startup_mode=startup_mode,
        connection_observer=observed.append,
    )
    statuses = []

    async def status(value):
        statuses.append(value)

    target = tmp_path / "entry.mp4"
    assert await video.generate("private-prompt", 42, target, 0, status) == target
    info = await probe(target, settings.prompt_royale_ffprobe)
    assert 4.96 <= float(info["format"]["duration"]) <= 5.08
    assert info["streams"][0]["width"] == 1280
    assert info["streams"][0]["height"] == 768
    assert info["streams"][0]["codec_name"] == "h264"
    assert info["streams"][0]["r_frame_rate"] == "24/1"
    assert statuses == ["generating", "preparing"]
    assert video.last_evidence["capture_gate"] == "frame_arrival_time"
    assert video.last_evidence["received_frames"] == 180
    assert video.last_evidence["outcome"] == "ready"
    assert video.last_evidence["ready_seconds"] == (90 if startup_timeout else 0)
    assert video.last_evidence["confirmed_closed"] is True
    assert observed == ["ready", "disconnected"]
    assert sum(r.url.path == "/sessions" for r in requests) == (1 if startup_mode == "rest" else 0)
    assert sum(r.method == "DELETE" for r in requests) == (1 if startup_mode == "rest" else 0)
    assert not target.with_suffix(".source.mp4").exists()
    assert not video.journal.exists()


async def test_long_startup_rejects_token_that_cannot_cover_session_cap(tmp_path):
    def respond(request):
        assert request.url.path == "/tokens"
        return httpx.Response(200, json={"jwt": "private-jwt", "expires_at": time.time() + 300})

    video = HeliosVideo(
        RoyaleSettings(_env_file=None, reactor_api_key="private-key"),
        tmp_path / "unresolved-provider.json",
        httpx.MockTransport(respond),
        startup_timeout=300,
        startup_mode="rest",
    )

    async def status(value):
        pass

    with pytest.raises(ProviderFailure, match="Token expires"):
        await video.generate("private-prompt", 42, tmp_path / "entry.mp4", 0, status)
    assert not video.sessions
    assert not video.journal.exists()


@pytest.mark.parametrize("creation_status", [200, 429, 500])
async def test_rest_startup_timeout_and_rejection_preserve_session_ownership(
    tmp_path, monkeypatch, creation_status
):
    class UnconnectedReactor:
        def __init__(self, **kwargs):
            pass

        def on(self, *args):
            pass

        def track(self, name):
            return self

        def on_raw_frame(self, callback):
            pass

        async def connect(self, **kwargs):
            pytest.fail("SDK must not connect before the runtime is ready")

        async def disconnect(self):
            pass

        def close(self):
            pass

    requests = []
    deleted = False

    def respond(request):
        nonlocal deleted
        requests.append(request)
        if request.url.path == "/tokens":
            return httpx.Response(200, json={"jwt": "private-jwt", "expires_at": time.time() + 600})
        if request.url.path == "/sessions":
            return httpx.Response(creation_status, json={"session_id": "test-session"})
        assert request.url.path == "/sessions/test-session"
        if request.method == "DELETE":
            deleted = True
            return httpx.Response(200, json={})
        return httpx.Response(200, json={"state": "CLOSED" if deleted else "CREATED"})

    real_timeout = asyncio.timeout
    monkeypatch.setattr(
        asyncio, "timeout", lambda seconds: real_timeout(0.03 if seconds == 300 else seconds)
    )
    monkeypatch.setattr(reactor_sdk, "Reactor", UnconnectedReactor)
    video = HeliosVideo(
        RoyaleSettings(_env_file=None, reactor_api_key="private-key"),
        tmp_path / "unresolved-provider.json",
        httpx.MockTransport(respond),
        startup_timeout=300,
        startup_mode="rest",
    )

    async def status(value):
        pass

    with pytest.raises(ProviderFailure) as failure:
        await video.generate("private-prompt", 42, tmp_path / "entry.mp4", 0, status)
    assert sum(r.url.path == "/sessions" for r in requests) == 1
    assert deleted is (creation_status == 200)
    assert video.last_evidence["confirmed_closed"] is (creation_status != 500)
    assert video.journal.exists() is (creation_status == 500)
    assert failure.value.uncertain is (creation_status == 500)


async def test_legacy_download_failure_retains_recording_for_retry(tmp_path):
    class Capture:
        def track(self, name):
            return self

        def on_raw_frame(self, callback):
            self.frame = callback

        async def send_command(self, name, data):
            if name == "start":
                for stamp in (1_000_000, 7_000_000):
                    self.frame(b"pixels", 1280, 768, 0, stamp, None)

        async def request_recording(self):
            return SimpleNamespace(playlist_url="https://api.reactor.inc/recording.m3u8")

    def respond(request):
        return httpx.Response(503)

    video = HeliosVideo(RoyaleSettings(_env_file=None), tmp_path / "journal.json")
    evidence = {"received_frames": 0, "timestamped_frames": 0, "zero_timestamp_frames": 0}
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(ProviderFailure) as failure:
            await video._capture(
                Capture(),
                client,
                SimpleNamespace(jwt="private-jwt"),
                tmp_path / "source.mp4",
                "private-prompt",
                42,
                evidence,
                time.monotonic(),
            )
    assert failure.value.transient
    assert failure.value.source.playlist == "https://api.reactor.inc/recording.m3u8"
