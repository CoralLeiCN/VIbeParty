import asyncio
import json
import time
from collections import defaultdict
from types import SimpleNamespace

import httpx
import pytest
import reactor_sdk

from backend.games.prompt_royale import fast_h3
from backend.games.prompt_royale.config import RoyaleSettings
from backend.games.prompt_royale.fast_h3 import FastH3Video
from backend.games.prompt_royale.media import command, probe
from backend.games.prompt_royale.providers import ProviderFailure


@pytest.mark.parametrize(
    "scenario",
    [
        "success",
        "command_error",
        "clip_failed",
        "short_playback",
        "slow_delivery",
        "short_provider_clip",
        "sparse_playback",
        "two_frames",
        "single_frame",
        "no_frames",
        "unfinished",
    ],
)
async def test_fast_h3_threaded_frames_and_clip_lifecycle(tmp_path, monkeypatch, scenario):
    commands = []
    requests = []
    instances = []
    clock = time.monotonic()
    # Advance receiver time independently of test runtime. Real SDK callbacks
    # still run on a worker thread and write through the actual FFmpeg process.
    monkeypatch.setattr(fast_h3, "time", SimpleNamespace(monotonic=lambda: clock))
    produced = asyncio.Event()

    class FakeReactor:
        session_id = "test-fast-h3-session"

        def __init__(self, **kwargs):
            assert kwargs == {"model_name": "reactor/fast-h3", "jwt": "private-jwt"}
            self.callbacks = defaultdict(list)
            self.producer = None
            self.closed = False
            instances.append(self)

        def on(self, event, callback):
            self.callbacks[event].append(callback)

        def off(self, event, callback):
            self.callbacks[event].remove(callback)

        def fire(self, event, *args):
            for callback in list(self.callbacks[event]):
                callback(*args)

        def track(self, name):
            assert name == "main_video"
            return self

        def on_raw_frame(self, callback):
            self.on("frame", callback)

        def off_frame(self, callback):
            self.off("frame", callback)

        async def connect(self):
            self.fire("session_id_changed", self.session_id)
            self.fire("status_changed", "ready")

        async def send_command(self, command, data):
            commands.append((command, data))
            if command == "get_state":
                return {
                    "type": "state_update",
                    "data": {
                        "clip_seconds_min": 0.5 if scenario == "short_provider_clip" else 124 / 24,
                        "clip_seconds_max": 1 if scenario == "short_provider_clip" else 345 / 24,
                    },
                }
            if command == "set_autoplay":
                assert data == {"enabled": False}
                return {"type": "autoplay_accepted", "data": {"enabled": False}}
            clip = {"clip_id": "our-clip", "seconds": 158 / 24, "frames": 158, "ready": False}
            if scenario == "short_provider_clip":
                clip.update(seconds=1, frames=24)
            if command == "enqueue":
                assert data == {
                    "prompt": "private-prompt",
                    "seed": 42,
                    "seconds": 1 if scenario == "short_provider_clip" else 6,
                }
                # Idle frames, including another clip's event, cannot produce a successful capture.
                self.fire(
                    "message",
                    {
                        "type": "clip_started",
                        "data": {
                            "clip": {"clip_id": "unrelated-clip"},
                        },
                    },
                )
                for _ in range(130):
                    self.fire("frame", bytes(320 * 192 * 4), 320, 192, 0, 0, None)
                if scenario == "command_error":
                    self.fire(
                        "message",
                        {
                            "type": "command_error",
                            "data": {
                                "command": "enqueue",
                                "reason": "private-prompt private-key",
                            },
                        },
                    )
                    return None
                kind = "clip_failed" if scenario == "clip_failed" else "clip_generated"
                self.fire("message", {"type": kind, "data": {"clip": clip}})
                return {"type": "clip_queued", "data": {"clip": clip}}
            assert command == "play" and data == {"clip_id": "our-clip"}
            loop = asyncio.get_running_loop()
            self.fire("message", {"type": "clip_started", "data": {"clip": clip}})

            def produce():
                nonlocal clock
                # Match SDK 1.5.1: BGRA bytes delivered from a media thread, zero timestamps.
                count = {
                    "short_playback": 40,
                    "slow_delivery": 40,
                    "short_provider_clip": 24,
                    "single_frame": 1,
                    "no_frames": 0,
                }.get(scenario, 158)
                arrivals = [index / 24 for index in range(count)]
                if scenario == "sparse_playback":
                    arrivals = [0, 0.5, 2, 4]
                elif scenario == "slow_delivery":
                    arrivals = [index / 3 for index in range(count)]
                elif scenario in {"two_frames", "unfinished"}:
                    arrivals = [0, 4]
                base = clock
                colors = ([20, 20, 220, 255], [20, 220, 20, 255], [220, 20, 20, 255])
                for index, elapsed in enumerate(arrivals):
                    clock = base + elapsed
                    pixels = bytes(colors[index % 3]) * (320 * 192)
                    self.fire("frame", pixels, 320, 192, index, 0, None)
                    time.sleep(0.015)
                if scenario != "unfinished":
                    loop.call_soon_threadsafe(
                        self.fire,
                        "message",
                        {"type": "clip_finished", "data": {"clip": clip}},
                    )
                    # Frames outside the matching playback cannot rescue an empty clip.
                    loop.call_soon_threadsafe(
                        self.fire, "frame", bytes(320 * 192 * 4), 320, 192, 999, 0, None
                    )
                loop.call_soon_threadsafe(produced.set)

            self.producer = asyncio.create_task(asyncio.to_thread(produce))
            return None

        async def disconnect(self):
            if self.producer:
                await self.producer
            self.fire("status_changed", "disconnected")

        def close(self):
            self.closed = True

    def respond(request):
        requests.append(request)
        if request.url.path == "/tokens":
            body = json.loads(request.content)
            details = body["authorization_details"][0]
            assert details["resources"]["models"]["match"] == ["reactor/fast-h3"]
            assert details["constraints"] == {"max_sessions": 1, "max_session_duration_seconds": 60}
            return httpx.Response(200, json={"jwt": "private-jwt", "expires_at": time.time() + 300})
        assert request.method == "GET" and request.url.path == "/sessions/test-fast-h3-session"
        return httpx.Response(200, json={"state": "CLOSED"})

    monkeypatch.setattr(reactor_sdk, "Reactor", FakeReactor)
    settings = RoyaleSettings(_env_file=None, reactor_api_key="private-key")
    video = FastH3Video(
        settings, tmp_path / "unresolved-provider.json", httpx.MockTransport(respond)
    )
    target = tmp_path / "entry.mp4"

    async def status(value):
        pass

    expected_frames = {
        "success": 120,
        "short_playback": 40,
        "slow_delivery": 40,
        "short_provider_clip": 24,
        "sparse_playback": 4,
        "two_frames": 2,
    }
    if scenario in expected_frames:
        assert await video.generate("private-prompt", 42, target, 0, status) == target
        info = await probe(target, settings.prompt_royale_ffprobe)
        expected = expected_frames[scenario]
        assert float(info["format"]["duration"]) == pytest.approx(expected / 24, abs=0.001)
        assert len(info["streams"]) == 1
        assert info["streams"][0]["nb_frames"] == str(expected)
        assert video.last_evidence["capture_gate"] == "clip_finished_and_at_least_two_frames"
        assert video.last_evidence["capture_timing"] == "received_frames_at_24fps"
        assert video.last_evidence["output_frames"] == expected
        assert video.last_evidence["captured_frames"] == expected
        assert video.last_evidence["held_output_frames"] == 0
        if scenario == "slow_delivery":
            # Keep frames that arrive beyond five receiver seconds, up to the
            # frame cap; network delay must not discard the rest of the scene.
            assert video.last_evidence["capture_span_seconds"] > 12
        if scenario == "sparse_playback":
            # Decode the entire output: the four received colors must appear
            # once each, in order, without repeated or idle black frames.
            pixels = await command(
                settings.prompt_royale_ffmpeg,
                "-v",
                "error",
                "-i",
                str(target),
                "-vf",
                "scale=1:1",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "pipe:1",
            )
            colors = [220, 20, 20, 20, 220, 20, 20, 20, 220, 220, 20, 20]
            assert len(pixels) == len(colors)
            assert all(abs(actual - wanted) < 12 for actual, wanted in zip(pixels, colors))
        assert not target.with_suffix(".source.mp4").exists()
    elif scenario == "unfinished":
        task = asyncio.create_task(video.generate("private-prompt", 42, target, 0, status))
        await asyncio.wait_for(produced.wait(), 5)
        await asyncio.sleep(0.1)
        assert not task.done()  # Even usable frames need a matching completed playback.
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not target.exists()
        assert not target.with_suffix(".source.mp4").exists()
    else:
        with pytest.raises(ProviderFailure) as failure:
            await video.generate("private-prompt", 42, target, 0, status)
        assert failure.value.transient == (scenario in {"single_frame", "no_frames"})
        assert not target.exists()
        assert not target.with_suffix(".source.mp4").exists()
        assert video.last_evidence["outcome"] == "failed"
    assert instances[0].closed
    assert not instances[0].callbacks["frame"]
    assert video.last_evidence["confirmed_closed"] is True
    assert not video.journal.exists()
    assert sum(request.url.path == "/tokens" for request in requests) == 1
    assert [command for command, _ in commands][:3] == ["get_state", "set_autoplay", "enqueue"]
    (diagnostic,) = (tmp_path / "diagnostics").glob("*.json")
    for secret in ("private-key", "private-jwt", "private-prompt"):
        assert secret not in diagnostic.read_text()
