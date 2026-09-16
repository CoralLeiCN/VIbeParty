"""Legacy Helios streaming capture, retained for diagnostic comparisons."""

import asyncio

import httpx

from backend.games.prompt_royale.providers import ProviderFailure
from backend.games.prompt_royale.reactor_video import (
    ReactorVideo,
    SavedRecording,
    download_recording,
)


class HeliosVideo(ReactorVideo):
    model_name = "reactor/helios"
    preset = {"sr_scale": "2x"}

    async def _capture(self, reactor, client, session, path, prompt, seed, evidence, started):
        received = asyncio.Event()
        loop = asyncio.get_running_loop()
        stamps = []

        def frame(_pixels, _width, _height, _id, timestamp_us, _metadata):
            elapsed = self.record_frame(evidence, timestamp_us, started)
            if timestamp_us:
                stamps.append(timestamp_us)
                evidence["media_seconds"] = (stamps[-1] - stamps[0]) / 1_000_000
                if stamps[-1] - stamps[0] >= 6_000_000:
                    evidence["capture_gate"] = "sender_timestamps"
                    loop.call_soon_threadsafe(received.set)
            if evidence["zero_timestamp_frames"] and elapsed - evidence["first_frame_seconds"] >= 6:
                evidence["capture_gate"] = "frame_arrival_time"
                loop.call_soon_threadsafe(received.set)

        reactor.track("main_video").on_raw_frame(frame)
        for command, data in (
            ("set_sr_scale", {"sr_scale": "2x"}),
            ("set_seed", {"seed": seed}),
            ("set_prompt", {"prompt": prompt}),
            ("start", {}),
        ):
            evidence["stage"] = command
            await reactor.send_command(command, data)
        evidence["stage"] = "wait_for_frames"
        await received.wait()
        evidence["stage"] = "request_recording"
        clip = await reactor.request_recording()
        recording = SavedRecording(clip.playlist_url, session.jwt)
        evidence["stage"] = "download_recording"
        try:
            evidence["source_bytes"] = await download_recording(client, recording, path)
        except (httpx.TransportError, TimeoutError) as error:
            raise ProviderFailure(
                "Recording download failed", transient=True, source=recording
            ) from error
        except httpx.HTTPStatusError as error:
            raise ProviderFailure(
                "Recording download failed",
                transient=error.response.status_code in {429, 500, 502, 503, 504},
                source=recording,
            ) from error
        return recording
