# WebRTC playback smoothing: controlled experiments

Run on 13 September 2026 to test the explanation for Word by Word's missing frames. This follows the [instrumented live investigation](decoded-frame-loss-2026-09-13.md).

## Finding to retain

**The native WebRTC build selected by Reactor SDK 1.5.1 enables playback smoothing by default. Its smoother can deliberately discard already-decoded frames when multiple buffered frames are due for display.**

The component experiment confirmed this behavior using the actual native library: missing frame IDs exactly matched WebRTC's own render-drop counter, and disabling smoothing preserved all 158 frames in every tested timing profile. The real local VP8 connection preserved all frames with both settings, including receiver stalls. Therefore smoothing is a demonstrated loss mechanism and a concrete capture-mode fix to evaluate; it remains an unproven attribution for the original live **57/158** failure.

The default is documented in [WebRTC's media configuration](https://webrtc.googlesource.com/src/+/a5ddff60/media/base/media_config.h). The native receive path selects the smoother before delivering frames to the sink. [Receive-stream implementation](https://webrtc.googlesource.com/src/+/a5ddff60/video/video_receive_stream2.cc).

## Experiment 1: isolate the decoded-frame boundary

Used Reactor's released, unmodified `libwebrtc.a`, selected by published `reactor-webrtc-sys` 0.16.0: `webrtc-7907-a5ddff60-p6`, full WebRTC commit `a5ddff6086d96fd2356ad6c521525ea2803f7988`. The release archive's SHA-256 matched its published manifest. The host was macOS 26.6.2, arm64. [Native release](https://github.com/reactor-team/reactor-webrtc/releases/tag/webrtc-7907-a5ddff60-p6), [published crate](https://crates.io/crates/reactor-webrtc-sys/0.16.0).

Injected 158 uniquely numbered, already-decoded frames into the real `IncomingVideoStream` at a nominal 24 fps. A manual clock and task scheduler controlled only render-task execution. Presentation timestamps were 100 ms ahead of nominal individual arrival times, with a 10 ms render delay. The comparison selected either the actual smoother or direct sink delivery, matching the native receive-stream routing. There was no encoder, decoder, network, Python or FFmpeg in this experiment.

| Timing profile | Delivered, smoothing on | Native render drops | Delivered, smoothing off |
| --- | ---: | ---: | ---: |
| Steady 24 fps | 158 | 0 | 158 |
| Three-frame batches | 158 | 0 | 158 |
| One 20 ms render-task pause | 158 | 0 | 158 |
| One 50 ms pause | 158 | 0 | 158 |
| One 100 ms pause | 156 | 2 | 158 |
| One 150 ms pause | 156 | 2 | 158 |
| One 250 ms pause | 156 | 2 | 158 |
| Repeated 150 ms pauses | 132 | 26 | 158 |
| Three-frame batches plus repeated pauses | 119 | 39 | 158 |

Each single pause started at 990 ms. Repeated pauses started at 240 ms, then every 500 ms through the input interval. After a 12-second simulated drain, no delivery tasks remained. All delivered IDs were ordered and unique. In every smoothing-on case, WebRTC's destructor log `WebRTC.Video.DroppedFrames.RenderQueue` exactly matched the number of missing IDs. Smoothing off bypasses that component, so its absent counter is recorded as `null`.

For the single 100 ms pause, IDs **23 and 24** disappeared. The actual render queue consumed the due frames and retained its newest candidate. Longer pauses in this particular setup lost the same two IDs; this reflects queue occupancy and timing, not a general drop limit. Similarly, the 20/50 ms results do not establish a universal safe stall duration.

Three-frame batches alone lost nothing. A batch size is therefore insufficient to diagnose frame loss. The relevant condition is which buffered frames are already due when the render task runs. The native policy is in [VideoRenderFrames::FrameToRender](https://webrtc.googlesource.com/src/+/a5ddff60/video/render/video_render_frames.cc); task delivery is in [IncomingVideoStream](https://webrtc.googlesource.com/src/+/a5ddff60/video/render/incoming_video_stream.cc).

## Experiment 2: real local WebRTC connection

Created two real peers using Reactor's published C++ adapter. They exchanged SDP and ICE in memory and transmitted 158 synthetic 1344×768 frames at 24 fps. Each frame encoded its identity in eight wide binary stripes, allowing the decoded output to be checked for missing, duplicated or reordered frames. No STUN/TURN server was configured.

The receiver either collected frames immediately or slept for 150 ms after every 24 delivered frames. The four-case matrix was run twice; the second run added an explicit count of native drop-log observations so an absent counter could not be mistaken for a measured zero.

| VP8 connection case | Sent | Decoded | Delivered | Missing IDs |
| --- | ---: | ---: | ---: | ---: |
| Smoothing on, immediate sink | 158 | 158 | 158 | 0 |
| Smoothing off, immediate sink | 158 | 158 | 158 | 0 |
| Smoothing on, 150 ms sink stalls | 158 | 158 | 158 | 0 |
| Smoothing off, 150 ms sink stalls | 158 | 158 | 158 | 0 |

Both matrices produced the counts above, with zero packet loss and zero decoder-path drops in all cases. Each stressed case applied six stalls. In the final matrix, each smoothing-on run emitted one native render-drop log with value zero; smoothing-off runs emitted none and record `null`. The first matrix's default-zero render-drop field lacked that presence check and should not independently be used as proof of an observed counter.

This connection experiment did **not** reproduce the missing-frame symptom. Unlike the component experiment, it did not control the timing of decoded frames relative to their presentation deadlines. A slow callback alone did not force the relevant queued-frame condition. Also, bypassing the smoother changes which native thread receives callback pressure; these sink stalls must not be equated with the manual render-task pauses in experiment 1.

The H.264 attempt could not produce a comparison: Apple's VideoToolbox encoder returned `-12902` before sending any video. An explicit 24 fps encoder limit did not resolve it. This is a limitation of this harness/host run, not evidence of a production receive-side H.264 failure. VP8 was selected explicitly for the successful connection matrix. An earlier build also required `-Wl,-ObjC` to retain Objective-C codec categories from the static archive; the reproducible runner includes it.

## What this means for Word by Word

The prior live diagnostics decoded 158 frames but delivered only 157 or 153 to Python, with zero reported packet loss and zero decoder-path drops. A render-stage discard can explain that pattern because the decode counter advances before the smoother. These experiments prove the mechanism under controlled conditions; they do not identify the scheduling event in those live runs or explain all 101 frames missing from the older 57/158 run.

The proposed native capture option remains:

```cpp
rtc_config.set_prerenderer_smoothing(false);
```

Apply it before creating a recording peer. This is a native WebRTC accessor, not an existing Python `Reactor` constructor argument. [Accessor documentation](https://webrtc.googlesource.com/src/+/a5ddff60/api/peer_connection_interface.h).

The complete capture path also needs an observable, bounded FIFO after the native sink. Reactor's separate Rust FFI callback queue has capacity one and drops older frames; bypassing smoothing can expose that queue to bursts. The local connection harness does not include that queue, Python or FFmpeg, so its 158/158 result is not full SDK capture validation. [Reactor queue construction](https://github.com/reactor-team/reactor-client-sdks/blob/9156ce9b09b3ebb8ed717d49d8ac69c5e44cec1d/crates/reactor-ffi/src/lib.rs#L893).

The next live validation must compare generated/sent, decoded, render/sink, native-enqueued/dropped, Python-dispatched and application-accepted counts, plus actual frame identity and clip boundaries. It should use the standard Word by Word scenarios and reject incomplete media. A longer timeout cannot recover frames already discarded.

## Evidence and reproduction

The raw JSON evidence below is kept locally and ignored by Git. The findings and reproducible harness remain part of the shared documentation; a fresh checkout can regenerate results using the linked commands.

- [Reproducible harness and commands](../../../scripts/experiments/webrtc_smoothing/README.md).
- [All 18 native component cases, including frame IDs](experiments/2026-09-13-smoothing/component-results.json).
- [First local VP8 matrix](experiments/2026-09-13-smoothing/loopback-VP8-first-matrix.json) and [final matrix with explicit counter observations](experiments/2026-09-13-smoothing/loopback-VP8-results.json).
- [H.264 failure evidence](experiments/2026-09-13-smoothing/h264-unusable.json).
- [Versions, hashes and host provenance](experiments/2026-09-13-smoothing/provenance.json).

These synthetic transport experiments have no `WW-CAT` category scenario or four-slot story mapping. They made **zero new Reactor service calls** and used no model generation. Application behavior and the installed SDK were not modified. H.264 end-to-end comparison and a live FastH3 test with the proposed native capture mode remain outstanding.
