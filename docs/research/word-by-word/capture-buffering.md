# Capture startup burst, 12 September 2026

The reported "No usable video was saved" failure reached the first FastH3 clip's
capture phase. The saved diagnostic record reports successful token creation,
generation in 4.404 seconds, 158 advertised frames, only nine accepted frames,
an eight-frame queue peak, and `frame_queue_overflow`. No clip was saved. The
provider session was independently confirmed `CLOSED` during cleanup.

FFmpeg starts after the first frame supplies its dimensions. The native stream
continues delivering frames while the encoder starts. The previous eight-frame
queue could overflow during that interval; the existing provider fake avoided
this condition by waiting whenever the app queued two frames.

The queue now holds up to 32 frames, with a separate 128 MiB raw-data limit. At
1344×768 this permits 32 queued BGRA frames (126 MiB); at 1920×1080 the byte
limit permits 16. One frame being written, encoder/pipe buffers, and provider
memory are additional to the queue budget. Evidence includes queue peak bytes
and both limits. Exceeding either limit still rejects the incomplete capture;
frames are never silently dropped to publish a video.

The regression uses native-thread synthetic frames and actual FFmpeg encoding.
It holds encoder startup, delivers 24 additional full-resolution frames without
consulting queue occupancy, then delivers the remaining frames at 24 fps. An
early sender finish event does not truncate delivery. The old code fails with
`frame_queue_overflow`; the updated code saves all 158 frames at 1344×768, and
decoding verifies unique color markers in order. Separate cases exercise the frame
and byte limits and confirm that overflow leaves no playable partial file.

Validation: all 70 Word by Word/shared backend tests pass; scoped Ruff lint,
formatting and diff whitespace checks pass. The shared HTTP route test initially
failed because the new checkout had no frontend build. Copying the existing,
unchanged frontend build into this checkout resolved that setup requirement.

This is a capture regression, not a category/model rehearsal; no WW-CAT scenario
or paid generation was run. The earlier 156-of-158 end-of-stream failure remains
a separate unverified live case. The running app and primary checkout were not
restarted or changed by this isolated branch.
