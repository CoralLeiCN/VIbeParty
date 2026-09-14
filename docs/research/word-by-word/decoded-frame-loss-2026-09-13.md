# Word by Word: loss after decoding

Investigated 13 September 2026 after the user asked why frames were actually disappearing. This follows the [capture proposal](capture-fix-proposal-2026-09-13.md), whose native FIFO explanation was a possible mechanism rather than a measured diagnosis.

Follow-up: [native smoothing experiments](smoothing-experiment-2026-09-13.md) confirmed render-stage loss under controlled timing: the real native drop counter exactly matched missing frame IDs, and bypassing smoothing preserved all 158 frames. Real local VP8 connections preserved all frames with both settings. The experiments establish the mechanism, while attribution to the original live failure remains unproven.

## Finding

Two instrumented live runs locate a frame-count shortfall **after WebRTC decoding and before the application's Python recorder**. The strongest source-supported explanation is WebRTC's enabled playback smoother: it can discard already-decoded frames to keep rendering on time. That stage precedes Reactor's separate capacity-one callback queue.

The frame-count evidence establishes the boundary. It does not identify each discarded source frame, prove which native discard mechanism handled each one, or reconstruct the older 57/158 run, which had no decoder/delivery counters. The measured 157/158 and 153/158 failures must not be presented as reproducing the severity of 57/158.

## Live comparison

Both runs used Reactor SDK 1.5.1, the existing FastH3 provider, the exact `WW-CAT-01` inputs, and only its Place segment: `Enchanted forest`. This was a capture diagnosis, not a full story or multiplayer acceptance run. Each created one session, made one enqueue, and performed no paid retry.

| Measurement | Existing capture startup | FFmpeg started before play |
| --- | ---: | ---: |
| Advertised frames | 158 | 158 |
| WebRTC frames decoded | 158 | 158 |
| Reported packet loss / NACKs | 0 / 0 | 0 / 0 |
| Reported decoder-path dropped frames | 0 | 0 |
| Python application callbacks | 157 | 153 |
| Frames accepted by application | 157 | 153 |
| Application queue peak / limit | 7 / 32 | 2 / 32 |
| Longest application callback | 0.099 ms | 0.120 ms |
| Capture result | 30.009 s timeout | 30.010 s timeout |
| Independent closure check | HTTP 200, CLOSED | HTTP 200, CLOSED |

The second run additionally counted SDK `_fire_on_track` calls before application dispatch: all 153 belonged to `main_video`, and all 153 reached the application. It recorded no null-buffer or missing-track drop diagnostic. The missing frames were therefore absent before Python track dispatch, rather than rejected by `FrameCapture.accept()`.

The second run's maximum measured event-loop lag during playback was 1.571 ms. Its 112.884 ms maximum over the whole process occurred at 0.611 seconds, long before playback started at 11.996 seconds. This does not support blaming a long Python event-loop stall during capture. FFmpeg was spawned about 0.5 seconds before issuing play; moving that startup did not resolve the loss. Two different generated clips are not a controlled proof that prestarting can never help, but they reject it as a sufficient fix here.

Neither run emitted the scoped native FIFO drop log. Absence of that log is not an exact zero-drop counter, and the capacity-one queue should not be named as the confirmed culprit.

Local evidence:

- [Existing-startup measurements](../../../.local/test-runs/2026-09-13-frame-diagnostic/diagnostic.json) and [sanitized provider evidence](../../../.local/test-runs/2026-09-13-frame-diagnostic/sanitized-provider-evidence.json).
- [Prestarted-encoder measurements](../../../.local/test-runs/2026-09-13-frame-diagnostic/prewarmed/diagnostic.json) and [sanitized provider evidence](../../../.local/test-runs/2026-09-13-frame-diagnostic/prewarmed/sanitized-provider-evidence.json).

These two diagnostics bring Word by Word attempts in this task to three, including the original all-games test. No further live attempt was made. Both sessions were independently confirmed closed; actual charges were unavailable. The running application and its source were not changed.

## Why decoded frames can disappear

The public SDK lockfile selects `reactor-webrtc` 0.16.0. The corresponding published `reactor-webrtc-sys` crate selects native build `webrtc-7907-a5ddff60-p6`. Its C++ glue constructs the default WebRTC peer configuration and does not disable playback smoothing. The inspected source at that WebRTC revision enables `enable_prerenderer_smoothing` by default and explicitly describes buffering and potentially dropping decoded frames for smooth rendering. [SDK dependency lock](https://github.com/reactor-team/reactor-client-sdks/blob/9156ce9b09b3ebb8ed717d49d8ac69c5e44cec1d/Cargo.lock), [published native dependency](https://crates.io/crates/reactor-webrtc-sys/0.16.0), [WebRTC configuration](https://webrtc.googlesource.com/src/+/a5ddff60/media/base/media_config.h).

The relevant path is:

```text
decode → increment frames_decoded → playback smoother
       → Reactor video sink → native callback queue → Python → app queue → FFmpeg
```

`VideoStreamDecoder::OnFrameToRender()` updates the decoder statistics before passing the frame onward. With smoothing enabled, `VideoReceiveStream2` inserts `IncomingVideoStream` before the downstream renderer. [Decode-counter ordering](https://webrtc.googlesource.com/src/+/a5ddff60/video/video_stream_decoder2.cc), [smoother selection](https://webrtc.googlesource.com/src/+/a5ddff60/video/video_receive_stream2.cc).

Inside `VideoRenderFrames::FrameToRender()`, a loop consumes every queued frame whose display time is due. Each newer due frame replaces the previous candidate. Only the final candidate is returned to the renderer; the overwritten candidates are counted internally as render-queue drops. The code also rejects some stale, future-dated, or out-of-order frames. That internal counter is separate from the decoder-path drop counter returned in our SDK statistics. [Exact render-queue implementation](https://webrtc.googlesource.com/src/+/a5ddff60/video/render/video_render_frames.cc), [delivery to the sink](https://webrtc.googlesource.com/src/+/a5ddff60/video/render/incoming_video_stream.cc).

For example, if three frames are already due when the render task runs, it emits the newest and discards the other two. This can happen with arrival/timing variation even if every packet arrives and every frame decodes. A saved recording then loses motion because it receives only frames selected for display. The specific scheduling event responsible for each measured missing frame was not traced.

FastH3's reference model emits three-frame batches, but Reactor's runtime splits them and paces individual frames. The batch size alone is therefore not evidence that the client receives every three frames simultaneously. [Runtime pacer](https://github.com/reactor-team/reactor-runtime/blob/4d001fd84b1af8591a0fb8e3cbeae227c7edf904/src/reactor_runtime/transport/webrtc/pacer.py).

## Revised fix to test

The first native experiment should bypass display smoothing for the recording connection using WebRTC's actual accessor:

```cpp
rtc_config.set_prerenderer_smoothing(false);
```

This belongs in an explicit capture mode in Reactor's native adapter before creating the peer connection. It is not an existing argument to the Python `Reactor` constructor. WebRTC documents that this passes decoded frames onward promptly; it cannot prevent earlier transport or decoder loss. [Native accessor](https://webrtc.googlesource.com/src/+/a5ddff60/api/peer_connection_interface.h).

The capture mode also needs a bounded, observable FIFO rather than Reactor's capacity-one drop-oldest callback queue, because bypassing smoothing can expose decoding bursts to that next stage. Merely increasing that FIFO while leaving the earlier smoother enabled cannot recover frames the smoother already discarded.

Validate the native change by comparing decoded, render/sink, native-enqueued, native-dropped, Python-dispatched, and application-accepted counts with real clip boundaries. Add an explicit render-drop counter or trace to prove or falsify the smoothing diagnosis. Continue rejecting incomplete media and bound the application's post-finish drain. A verified provider-side artifact remains an alternative, but hosted FastH3 recording/export support is still unverified.

The precise diagnosis to give Reactor is: **SDK 1.5.1 on macOS arm64 reports 158 decoded frames with zero packet loss, yet delivers 157 or 153 frames to the Python recorder; prestarting FFmpeg does not resolve it. The native configuration appears to retain WebRTC's frame-dropping playback smoother, followed by a drop-oldest callback queue. Please expose a recording path that bypasses both policies, with counters to verify preservation.** No message was sent to Reactor.
