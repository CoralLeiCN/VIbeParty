"""FastH3 queue/play capture without Reactor's optional server recorder."""

import asyncio
import contextlib
import math
import queue
import threading
import time

from backend.games.prompt_royale.providers import ProviderFailure
from backend.games.prompt_royale.reactor_video import ReactorVideo


class FastH3Video(ReactorVideo):
    model_name = "reactor/fast-h3"
    preset = {"requested_seconds": 6, "max_output_seconds": 5, "fps": 24}

    async def _capture(self, reactor, client, session, path, prompt, seed, evidence, started):
        loop = asyncio.get_running_loop()
        changed = asyncio.Event()
        playing = threading.Event()
        # Raw callbacks run on the SDK's media thread. Bound both queued memory
        # (~48 MiB at 1344x768 BGRA) and the frames passed to the encoder.
        frames = queue.Queue(maxsize=12)
        events = {}
        failures = []
        clip_id = None
        first_arrival = None
        frame_limit = self.preset["max_output_seconds"] * self.preset["fps"]
        queued_frames = 0
        writer = None

        def message(value):
            if not isinstance(value, dict) or not isinstance(value.get("data"), dict):
                return
            kind, data = value.get("type"), value["data"]
            if kind == "command_error":
                command = data.get("command")
                if command in {"get_state", "set_autoplay", "enqueue", "play"}:
                    evidence["rejected_command"] = command
                failures.append("FastH3 rejected a command")
            elif kind == "clip_failed":
                failures.append("FastH3 could not build the clip")
            elif kind in {"state_update", "clip_generated", "clip_started", "clip_finished"}:
                event_id = data.get("clip", {}).get("clip_id")
                if len(events) < 32:
                    events[kind, event_id] = data
                if event_id == clip_id and kind == "clip_started":
                    playing.set()
                    evidence["play_started_seconds"] = round(time.monotonic() - started, 3)
                elif event_id == clip_id and kind == "clip_finished":
                    playing.clear()
                    evidence["play_finished_seconds"] = round(time.monotonic() - started, 3)
            changed.set()

        def frame(pixels, width, height, _id, timestamp_us, _metadata):
            nonlocal first_arrival, queued_frames
            self.record_frame(evidence, timestamp_us, started)
            if not playing.is_set() or queued_frames >= frame_limit:
                return
            if (
                not 1 <= width <= 1920
                or not 1 <= height <= 1080
                or len(pixels) != width * height * 4
            ):
                loop.call_soon_threadsafe(failures.append, "Invalid FastH3 video frame")
            else:
                arrival = time.monotonic()
                if first_arrival is None:
                    first_arrival = arrival
                elapsed = arrival - first_arrival
                try:
                    frames.put_nowait((pixels, width, height, elapsed))
                    queued_frames += 1
                except queue.Full:
                    evidence["dropped_frames"] = evidence.get("dropped_frames", 0) + 1
            loop.call_soon_threadsafe(changed.set)

        def check():
            if failures:
                raise ProviderFailure(failures[0])

        async def send(command, data):
            evidence["stage"] = command
            reply = await reactor.send_command(command, data)
            if isinstance(reply, dict) and "type" in reply:
                message(reply)
            check()
            return reply.get("data", reply) if isinstance(reply, dict) else None

        async def wait_for(kind, event_id=None):
            while True:
                changed.clear()
                check()
                if (kind, event_id) in events:
                    return events[kind, event_id]
                await changed.wait()

        async def encode():
            process = None
            geometry = None
            captured = 0
            completed = False

            try:
                while True:
                    changed.clear()
                    check()
                    try:
                        pixels, width, height, elapsed = frames.get_nowait()
                    except queue.Empty:
                        if ("clip_finished", clip_id) in events:
                            break
                        await changed.wait()
                        continue
                    if process is None:
                        geometry = (width, height)
                        evidence["source_width"], evidence["source_height"] = geometry
                        process = await asyncio.create_subprocess_exec(
                            self.settings.prompt_royale_ffmpeg,
                            "-y",
                            "-v",
                            "error",
                            "-f",
                            "rawvideo",
                            "-pix_fmt",
                            "bgra",
                            "-s",
                            f"{width}x{height}",
                            "-r",
                            str(self.preset["fps"]),
                            "-i",
                            "pipe:0",
                            "-an",
                            "-c:v",
                            "libx264",
                            "-preset",
                            "ultrafast",
                            "-pix_fmt",
                            "yuv420p",
                            "-movflags",
                            "+faststart",
                            str(path),
                            stdin=asyncio.subprocess.PIPE,
                            stdout=asyncio.subprocess.DEVNULL,
                            stderr=asyncio.subprocess.DEVNULL,
                        )
                    if geometry != (width, height):
                        raise ProviderFailure("FastH3 changed frame size during playback")
                    # Encode each received frame once at the model's frame rate.
                    # Missing frames shorten the clip; do not pad or interpolate.
                    process.stdin.write(pixels)
                    await process.stdin.drain()
                    captured += 1
                    evidence["captured_frames"] = captured
                    evidence["capture_span_seconds"] = round(elapsed, 3)
                if captured < 2:
                    raise ProviderFailure(
                        "FastH3 playback ended without enough video frames", transient=True
                    )
                evidence.update(
                    output_frames=captured,
                    output_source_frames=captured,
                    held_output_frames=0,
                    output_duration_seconds=captured / self.preset["fps"],
                    capture_timing="received_frames_at_24fps",
                )
                process.stdin.close()
                await process.stdin.wait_closed()
                await asyncio.wait_for(process.wait(), 10)
                if process.returncode:
                    raise ProviderFailure("FastH3 frame encoding failed")
                evidence["source_bytes"] = path.stat().st_size
                completed = True
            finally:
                if process and process.returncode is None:
                    process.kill()
                    await process.wait()
                if not completed:
                    path.unlink(missing_ok=True)

        reactor.on("message", message)
        reactor.track("main_video").on_raw_frame(frame)
        try:
            state = await send("get_state", {}) or await wait_for("state_update")
            minimum, maximum = state.get("clip_seconds_min"), state.get("clip_seconds_max")
            if (
                not all(
                    isinstance(value, (int, float)) and math.isfinite(value)
                    for value in (minimum, maximum)
                )
                or not 0 < minimum <= maximum <= 60
            ):
                raise ProviderFailure("FastH3 did not publish valid clip duration limits")
            evidence.update(clip_seconds_min=minimum, clip_seconds_max=maximum)
            seconds = min(maximum, max(minimum, self.preset["requested_seconds"]))
            await send("set_autoplay", {"enabled": False})
            data = await send("enqueue", {"prompt": prompt, "seed": seed, "seconds": seconds})
            clip = data.get("clip", {}) if data else {}
            clip_id = clip.get("clip_id")
            if not isinstance(clip_id, str) or not clip_id:
                raise ProviderFailure("FastH3 did not acknowledge the queued clip")
            duration = clip.get("seconds")
            if not isinstance(duration, (int, float)) or not 0 < duration <= 60:
                raise ProviderFailure("FastH3 accepted an unusable clip duration")
            evidence.update(clip_id=clip_id, generated_seconds=duration)
            evidence["stage"] = "wait_for_clip_generated"
            if not clip.get("ready"):
                await wait_for("clip_generated", clip_id)
            evidence["clip_generated_seconds"] = round(time.monotonic() - started, 3)
            writer = asyncio.create_task(encode())
            await send("play", {"clip_id": clip_id})
            evidence["stage"] = "capture_playback"
            await writer
            await wait_for("clip_finished", clip_id)
            evidence["capture_gate"] = "clip_finished_and_at_least_two_frames"
        finally:
            playing.clear()
            reactor.off("message", message)
            reactor.track("main_video").off_frame(frame)
            if writer and not writer.done():
                writer.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await writer
        return None
