import asyncio
import json
import sys
from types import SimpleNamespace

import httpx
import pytest

from backend.games.reverse_prompt.quota import GuardError, Quota
from backend.games.reverse_prompt.reactor_video import FastH3Provider, GenerationError


@pytest.mark.asyncio
async def test_disconnect_success_is_not_closure_proof(tmp_path):
    quota = Quota(tmp_path / "quota.json")
    quota.initialize()
    attempt = quota.consume()
    quota.session(attempt, "session")
    provider = FastH3Provider("unused", quota)

    class SDK:
        async def disconnect(self):
            pass  # Native SDK may swallow a failed DELETE.

    requests = []

    def handler(request):
        requests.append(request.method)
        return httpx.Response(200, json={"state": "ACTIVE"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(GenerationError):
            await provider._close(SDK(), client, "test-token", "session", attempt)
    assert requests == ["GET", "DELETE", "GET"]
    assert quota.read()["unresolved"]
    assert quota.read()["remaining"] == 8


@pytest.fixture
def decoded_provider(tmp_path, monkeypatch):
    quota = Quota(tmp_path / "quota.json")
    quota.initialize()
    sessions, token_bodies = [], []
    enqueued, played = asyncio.Event(), asyncio.Event()

    class SDK:
        behavior = "normal"

        def __init__(self, model_name, jwt):
            assert model_name == "reactor/fast-h3"
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

        def emit(self, kind, **data):
            # The pinned Python SDK carries the payload inside data.
            self.handlers["message"]({"type": kind, "data": data})

        async def connect(self):
            self.handlers["session_id_changed"](self.session_id)
            self.frame(bytes((0, 0, 0, 255)) * (1344 * 768), 1344, 768, 0, 0, b"")

        async def send_command(self, command, data):
            self.commands.append((command, data))
            if command == "enqueue":
                enqueued.set()
                if hasattr(self, "clip"):
                    # Delayed events from the previous clip must not poison the new capture.
                    for event in ("clip_started", "clip_finished", "clip_failed"):
                        self.emit(event, clip=self.clip)
                count = sum(name == "enqueue" for name, _ in self.commands)
                self.clip = {"clip_id": f"{self.session_id}-clip-{count}", "frames": 124, **data}
                if self.behavior == "ambiguous_enqueue":
                    return None
                if self.behavior == "rejected":
                    self.emit("clip_failed", clip=self.clip)
                    await asyncio.Event().wait()  # No ack; rejection must wake the caller.
                if self.behavior == "invalid_length":
                    self.clip["frames"] = 345
                if self.behavior in {
                    "compact_generated",
                    "queue_only",
                    "missing_queue_clip",
                    "invalid_queue_frames",
                }:
                    self.emit("clip_generated", clip_id=self.clip["clip_id"])
                elif self.behavior == "wrong_generated":
                    self.emit("clip_generated", clip={**self.clip, "clip_id": "other-clip"})
                elif self.behavior != "silent_generation":
                    # Completion can be delivered before the enqueue acknowledgment.
                    self.emit("clip_generated", clip=self.clip)
                if self.behavior in {"queue_only", "missing_queue_clip", "invalid_queue_frames"}:
                    return {"type": "clip_queued", "data": {"clip_id": self.clip["clip_id"]}}
                return {"type": "clip_queued", "data": {"clip": self.clip}}
            if command == "get_queue":
                item = {"clip_id": self.clip["clip_id"], "frames": 124.0}
                if self.behavior == "missing_queue_clip":
                    item["clip_id"] = "other-clip"
                if self.behavior == "invalid_queue_frames":
                    item["frames"] = 124.5
                return {"type": "queue_update", "data": {"playout": [item]}}
            if command == "play":
                played.set()
                assert data == {"clip_id": self.clip["clip_id"]}
                # Idle frames between command and matching start must be excluded.
                self.frame(bytes((0, 0, 0, 255)) * (1344 * 768), 1344, 768, 0, 0, b"")
                clip = self.clip
                if self.behavior == "wrong_started":
                    clip = {**clip, "clip_id": "other-clip"}
                if self.behavior == "queue_only":
                    self.emit("clip_started", clip_id=clip["clip_id"])
                else:
                    self.emit("clip_started", clip=clip)
                self.emit("clip_started", clip=clip)  # Harmless duplicate boundary.
                if self.behavior not in {"silent_playback", "wrong_started"}:
                    self.feeder = asyncio.create_task(self.feed())
                return None
            if command == "stop":
                if self.feeder:
                    self.feeder.cancel()
                    await asyncio.gather(self.feeder, return_exceptions=True)
                self.emit("clip_stopped", clip=self.clip)
                return None
            acknowledgments = {
                "set_autoplay": "autoplay_accepted",
                "set_canvas": "canvas_accepted",
                "set_flush_on_clip_end": "flush_accepted",
            }
            if self.behavior == "unconfirmed_settings":
                return None
            return {"type": acknowledgments[command], "data": data}

        async def feed(self):
            count = 3 if self.behavior == "short_playback" else 124
            for index in range(count):
                self.frame(bytes((0, 0, 255, 255)) * (1344 * 768), 1344, 768, 0, 0, b"")
                await asyncio.sleep(1 / 24)
                if index == 119:
                    self.emit("clip_started", clip=self.clip)  # Must not re-arm capture.
            self.emit("clip_finished", clip=self.clip)
            for _ in range(10):
                self.frame(bytes((0, 0, 0, 255)) * (1344 * 768), 1344, 768, 0, 0, b"")

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
            # The guard and attempt consumption precede all provider traffic.
            assert quota.read()["unresolved"]
            token_bodies.append(json.loads(request.content))
            return httpx.Response(200, json={"jwt": "fake-token"})
        if request.method == "GET" and request.url.path.startswith("/sessions/"):
            sid = request.url.path.rsplit("/", 1)[1]
            session = next(s for s in sessions if s.session_id == sid)
            state = "ACTIVE" if session.behavior == "unresolved" else "CLOSED"
            return httpx.Response(200, json={"state": state if session.closed else "ACTIVE"})
        if request.method == "DELETE":
            return httpx.Response(200, json={})
        raise AssertionError("Unexpected provider request")

    original_client = httpx.AsyncClient
    monkeypatch.setitem(sys.modules, "reactor_sdk", SimpleNamespace(Reactor=SDK))
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    return FastH3Provider("fake-key", quota), SDK, sessions, token_bodies, enqueued, played


async def test_three_independent_clips_reuse_one_session_and_exclude_stale_playback(
    decoded_provider, tmp_path
):
    from backend.games.reverse_prompt.media import command

    provider, sdk, sessions, tokens, _, _ = decoded_provider
    prompts = ("A red balloon.", "A blue train.", "A green frog.")
    for step, prompt in enumerate(prompts):
        sdk.behavior = ("normal", "compact_generated", "queue_only")[step]
        path = await provider.generate(prompt, tmp_path / str(step), step)
        evidence = provider.last_evidence
        assert evidence["model"] == "reactor/fast-h3"
        assert evidence["capture_method"] == "decoded_frames"
        assert evidence["frames"] == evidence["encoded_frames"] == 120
        assert evidence["source_frames"] == 124
        assert evidence["frame_metadata_source"] == ("generated", "enqueue", "queue")[step]
        assert evidence["duration"] == 5
        assert (evidence["width"], evidence["height"]) == (1344, 768)
        assert not evidence["closed"] and evidence["playback_started"]
        assert not sessions[0].closed and provider.quota.read()["unresolved"]
        assert provider.quota.read()["remaining"] == 8 - step
        assert evidence["session_reused"] is (step > 0)
        saved_evidence = provider.quota.read()["attempts"][-1]["evidence"]
        assert saved_evidence["outcome"] == saved_evidence["phase"] == "saved"
        assert saved_evidence["encoded_frames"] == 120
        assert "attempt" not in saved_evidence
        request = [data for name, data in sessions[0].commands if name == "enqueue"][-1]
        assert set(request) == {"prompt", "seconds", "metadata"}
        assert request["prompt"].startswith(prompt + "\n\n")
        assert request["seconds"] == 5.167
        assert all(other not in request["prompt"] for other in prompts if other != prompt)
        # Decode the opening to prove the black idle frames were not captured.
        color = await command(
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-vf",
            "scale=1:1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "pipe:1",
        )
        assert color[0] > 240 and color[1] < 15 and color[2] < 15
    assert len(sessions) == len(tokens) == 1
    assert [name for name, _ in sessions[0].commands] == [
        "set_autoplay",
        "set_canvas",
        "set_flush_on_clip_end",
        "enqueue",
        "play",
        "stop",
        "enqueue",
        "play",
        "stop",
        "enqueue",
        "get_queue",
        "play",
        "stop",
    ]
    await provider.close()
    await provider.close()  # Duplicate cleanup must not reopen or rebill.
    assert provider.quota.read()["remaining"] == 6
    assert not provider.quota.read()["unresolved"]
    assert all(a["closed"] and a["evidence"]["closed"] for a in provider.quota.read()["attempts"])
    ledger_text = json.dumps(provider.quota.read())
    assert not any(text in ledger_text for text in (*prompts, "fake-key", "fake-token"))
    for token in tokens:
        detail = token["authorization_details"][0]
        assert detail["resources"]["models"]["match"] == ["reactor/fast-h3"]
        assert detail["constraints"] == {"max_sessions": 1, "max_session_duration_seconds": 360}
    sdk.behavior = "rejected"
    with pytest.raises(GenerationError):
        await provider.generate("A new round.", tmp_path / "next-round", 0)
    assert len(sessions) == len(tokens) == 2
    assert provider.quota.read()["remaining"] == 5
    assert not provider.quota.read()["unresolved"]


@pytest.mark.parametrize(
    "behavior",
    [
        "ambiguous_enqueue",
        "rejected",
        "invalid_length",
        "wrong_started",
        "unconfirmed_settings",
        "short_playback",
        "missing_queue_clip",
        "invalid_queue_frames",
    ],
)
async def test_provider_failures_never_publish_or_retry(decoded_provider, tmp_path, behavior):
    provider, sdk, sessions, tokens, _, _ = decoded_provider
    sdk.behavior = behavior
    with pytest.raises((GenerationError, ValueError)):
        async with asyncio.timeout(3):
            await provider.generate("A red balloon.", tmp_path / "failed", 0)
    assert not (tmp_path / "failed" / "video.mp4").exists()
    assert sessions[0].closed and len(tokens) == 1
    assert sum(name == "enqueue" for name, _ in sessions[0].commands) <= 1
    assert provider.quota.read()["remaining"] == 8
    assert not provider.quota.read()["unresolved"]
    assert provider.quota.read()["attempts"][-1]["evidence"]["outcome"] == "failed"


@pytest.mark.parametrize("behavior", ["silent_generation", "silent_playback", "wrong_generated"])
async def test_cancelled_wait_closes_without_refunding(decoded_provider, tmp_path, behavior):
    provider, sdk, sessions, _, enqueued, played = decoded_provider
    sdk.behavior = behavior
    task = asyncio.create_task(provider.generate("A red balloon.", tmp_path / "cancel", 0))
    gate = played if behavior == "silent_playback" else enqueued
    await asyncio.wait_for(gate.wait(), timeout=2)
    await asyncio.sleep(0.02)
    if behavior != "silent_playback":
        assert not played.is_set()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert sessions[0].closed
    assert provider.quota.read()["remaining"] == 8
    assert not provider.quota.read()["unresolved"]
    assert provider.last_evidence["encoded_frames"] == 0
    assert provider.quota.read()["attempts"][-1]["evidence"]["outcome"] == "cancelled"
    assert not (tmp_path / "cancel" / "video.mp4").exists()


async def test_unconfirmed_round_closure_preserves_the_persistent_block(decoded_provider, tmp_path):
    provider, sdk, _, _, _, _ = decoded_provider
    sdk.behavior = "unresolved"
    await provider.generate("A red balloon.", tmp_path / "uncertain", 0)
    with pytest.raises(GenerationError, match="closure"):
        await provider.close()
    restarted = Quota(provider.quota.path)
    assert restarted.read()["unresolved"] and restarted.read()["remaining"] == 8
    evidence = restarted.read()["attempts"][-1]["evidence"]
    assert evidence["outcome"] == "saved"
    assert not evidence["closed"]
    with pytest.raises(GuardError, match="closure"):
        restarted.consume()


async def test_diagnostics_exclude_sdk_exception_text(decoded_provider, tmp_path, monkeypatch):
    provider, sdk, _, _, _, _ = decoded_provider

    async def failed_command(self, command, data):
        raise RuntimeError("private player prompt and fake-token")

    monkeypatch.setattr(sdk, "send_command", failed_command)
    with pytest.raises(RuntimeError):
        await provider.generate("private player prompt", tmp_path / "failed", 0)
    ledger = Quota(provider.quota.path).read()
    evidence = ledger["attempts"][-1]["evidence"]
    assert evidence["failure_category"] == "RuntimeError"
    assert evidence["phase"] == "set_autoplay" and evidence["closed"]
    assert "private player prompt" not in json.dumps(ledger)
    assert "fake-token" not in json.dumps(ledger)


async def test_diagnostic_storage_failure_preserves_generation_error(
    decoded_provider, tmp_path, monkeypatch
):
    provider, sdk, sessions, _, _, _ = decoded_provider
    sdk.behavior = "rejected"

    def unavailable(*_args):
        raise GuardError("Diagnostic storage unavailable")

    monkeypatch.setattr(provider.quota, "record_outcome", unavailable)
    with pytest.raises(GenerationError, match="Provider rejected generation"):
        await provider.generate("A red balloon.", tmp_path / "failed", 0)
    assert sessions[0].closed and not provider.quota.read()["unresolved"]
    assert provider.quota.read()["remaining"] == 8
    assert provider.last_evidence["diagnostics_unavailable"]
    assert not (tmp_path / "failed" / "video.mp4").exists()


async def test_second_clip_failure_closes_the_shared_session_without_a_third_attempt(
    decoded_provider, tmp_path
):
    provider, sdk, sessions, tokens, _, _ = decoded_provider
    await provider.generate("A red balloon.", tmp_path / "first", 0)
    sdk.behavior = "rejected"
    with pytest.raises(GenerationError):
        await provider.generate("A blue tower.", tmp_path / "second", 1)
    ledger = Quota(provider.quota.path).read()
    assert len(sessions) == len(tokens) == 1 and sessions[0].closed
    assert ledger["remaining"] == 7 and not ledger["unresolved"]
    assert all(a["closed"] for a in ledger["attempts"])
    assert [a["evidence"]["outcome"] for a in ledger["attempts"]] == ["saved", "failed"]
    assert not (tmp_path / "second" / "video.mp4").exists()


async def test_session_identity_storage_failure_still_terminates_provider(
    decoded_provider, tmp_path, monkeypatch
):
    provider, _, sessions, _, _, _ = decoded_provider

    def storage_failure(*_args):
        raise GuardError("Session identity storage unavailable")

    monkeypatch.setattr(provider.quota, "session", storage_failure)
    with pytest.raises(GuardError):
        await provider.generate("A red balloon.", tmp_path / "failed", 0)
    assert sessions[0].closed
    assert provider.quota.read()["remaining"] == 8
    assert not provider.quota.read()["unresolved"]
    assert not (tmp_path / "failed" / "video.mp4").exists()
