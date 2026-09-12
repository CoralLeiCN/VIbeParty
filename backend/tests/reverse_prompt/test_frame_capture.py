import asyncio

import pytest

from backend.games.reverse_prompt.frame_capture import FRAME_COUNT, QUEUE_LIMIT, FrameCapture
from backend.games.reverse_prompt.media import command, probe, validate


def pixels(index=0):
    return bytes((index * 2, 0, 255 - index * 2, 255)) * (640 * 384)


async def until(predicate):
    async with asyncio.timeout(5):
        while not predicate():
            await asyncio.sleep(0.001)


async def test_actual_ffmpeg_encodes_first_120_frames_with_absent_metadata(tmp_path):
    capture = FrameCapture()
    output = tmp_path / "capture.mp4"
    task = asyncio.create_task(capture.record(output))
    capture.start()
    try:
        for index in range(FRAME_COUNT):
            capture.on_frame(pixels(index), 640, 384, 0, 0, b"")
            await until(lambda: capture.encoded > index or task.done())
            if task.done():
                task.result()
        assert await task == output
    finally:
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    metadata = await validate(output)
    info = await probe(output)
    assert metadata["duration"] == 5
    assert info["streams"][0]["nb_frames"] == "120"
    assert info["streams"][0]["r_frame_rate"] == "24/1"
    assert len(info["streams"]) == 1
    # Decode the first/last frame to confirm temporal order survives encoding.
    colors = await command(
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(output),
        "-vf",
        r"select=eq(n\,0)+eq(n\,119),scale=1:1",
        "-fps_mode",
        "passthrough",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "pipe:1",
    )
    assert len(colors) == 6
    assert colors[0] > 240 and colors[2] < 15  # First frame red.
    assert colors[3] < 30 and colors[5] > 220  # Last frame blue.
    assert capture.evidence()["encoded_frames"] == 120
    capture.on_frame(pixels(), 640, 384, 999, 0, b"")
    assert capture.received == 120


async def test_duplicate_metadata_is_ignored_and_capture_backpressure_fails_closed():
    capture = FrameCapture()
    capture.start()
    data = pixels()
    capture.on_frame(data, 640, 384, 1, 1, b"")
    capture.on_frame(data, 640, 384, 1, 1, b"")
    assert capture.received == 1
    for frame_id in range(2, QUEUE_LIMIT + 2):
        capture.on_frame(data, 640, 384, frame_id, frame_id * 41667, b"")
    with pytest.raises(ValueError, match="keep up"):
        await capture.next_frame()
    assert len(capture.queue) == QUEUE_LIMIT
    capture.stop()
    assert not capture.queue


@pytest.mark.parametrize("timestamp", [1, 15_100_001])
async def test_invalid_source_timestamp_order_or_span_fails(timestamp):
    capture = FrameCapture()
    capture.start()
    capture.on_frame(pixels(), 640, 384, 1, 100_000, b"")
    capture.on_frame(pixels(), 640, 384, 2, timestamp, b"")
    with pytest.raises(ValueError):
        await capture.next_frame()


async def test_cancelled_capture_awaits_encoder_exit_and_ignores_late_frames(tmp_path):
    capture = FrameCapture()
    task = asyncio.create_task(capture.record(tmp_path / "partial.mp4"))
    capture.start()
    capture.on_frame(pixels(), 640, 384, 0, 0, b"")
    await until(lambda: capture.encoded == 1 or task.done())
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert capture.process.returncode is not None
    capture.on_frame(pixels(), 640, 384, 0, 0, b"")
    assert capture.received == 1 and not capture.queue


async def test_playback_end_rejects_short_video_and_ignores_idle_padding():
    capture = FrameCapture()
    capture.start()
    capture.on_frame(pixels(), 640, 384, 0, 0, b"")
    capture.finish()
    for _ in range(120):
        capture.on_frame(pixels(), 640, 384, 0, 0, b"")
    with pytest.raises(ValueError, match="Playback ended"):
        await capture.next_frame()
    assert capture.received == 1


async def test_provider_canvas_is_checked_before_encoding():
    capture = FrameCapture(expected_dimensions=(1344, 768))
    capture.start()
    capture.on_frame(pixels(), 640, 384, 0, 0, b"")
    with pytest.raises(ValueError, match="Unexpected provider video dimensions"):
        await capture.next_frame()
    assert capture.received == 0
