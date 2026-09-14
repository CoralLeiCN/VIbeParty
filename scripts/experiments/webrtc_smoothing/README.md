# WebRTC smoothing experiment

This harness compares frame delivery with the playback smoother enabled and disabled. It links the unmodified WebRTC library selected by Reactor SDK 1.5.1 and uses published `reactor-webrtc-sys` 0.16.0 glue for its local peer connection experiment. It does not import the application's Python SDK or change its installed library.

See the [recorded findings](../../../docs/research/word-by-word/smoothing-experiment-2026-09-13.md) for results, failed attempts, and limits.

## Run on macOS arm64

Requirements: Python 3.12 or later, Xcode command-line tools (`clang++`, Apple SDK frameworks), and `zstd`. Downloads use GitHub releases and crates.io. Both archives have pinned SHA-256 checksums in `run.py`. No API key, Reactor server, model, camera, microphone, or paid generation is used. Local WebRTC sockets must be allowed for the connection test. STUN and TURN servers are not configured.

From the repository root:

```sh
.venv/bin/python scripts/experiments/webrtc_smoothing/run.py prepare
.venv/bin/python scripts/experiments/webrtc_smoothing/run.py build
.venv/bin/python scripts/experiments/webrtc_smoothing/run.py component
.venv/bin/python scripts/experiments/webrtc_smoothing/run.py loopback --codec VP8
```

H.264 is available as an explicit experiment:

```sh
.venv/bin/python scripts/experiments/webrtc_smoothing/run.py loopback --codec H264
```

On the recorded host, VideoToolbox encoding returned `-12902` before sending video, so H.264 produced no usable smoothing comparison. The runner fails a case with no decoded or delivered frames. It never silently substitutes another codec.

Outputs, downloads, build commands and binaries go to ignored `.local/experiments/webrtc-smoothing/`. Use `--work-dir /absolute/path` for a separate run. Results are JSON containing delivered and missing frame IDs. Each local connection process has a 40-second limit; builds have a 180-second limit. A loopback run writes partial results after each completed case, and each run replaces results with the same filename. Copy results before repeating if both runs matter.

## Two distinct experiments

`smoothing_experiment.cc` injects 158 already-decoded synthetic frames into the actual native `IncomingVideoStream`, with its actual `VideoRenderFrames` policy. A manual clock and scheduler impose specific render-task pauses. Presentation times are 100 ms ahead of nominal individual arrival times; the render delay is 10 ms. Smoothing off selects direct sink delivery, matching `VideoReceiveStream2`. This isolates the render stage; it does not encode, decode or transmit video. Native destructor drop counts must exactly match missing frame IDs, and the queue must drain completely. Eighteen deterministic cases cover nine timing profiles with smoothing on and off.

`loopback_experiment.cc` creates two real peers using Reactor's C++ adapter, exchanges SDP and ICE in memory, and sends synthetic 1344×768 video at 24 fps. Eight wide binary stripes encode IDs 1–158 through the codec. The receiver counts decoded frames, delivered IDs, packet loss and native render-drop logs. A 150 ms sleep after every 24 delivered frames applies pressure in the native sink. The same callback pressure is applied in both arms, though bypassing the smoother changes which native thread receives it. This experiment uses real media transport and codecs but omits Reactor's Rust FFI queue, Python, FFmpeg and the hosted model.

`native_render_drops: null` means no native render-drop log was observed. It must not be interpreted as a measured zero; `render_drop_log_entries` makes this distinction explicit in loopback results. Missing, duplicated, invalid or reordered markers cannot count as preserved delivery. Source count, sent count, decoded count and delivered count must be compared separately.

To diagnose a harness failure, set `SMOOTHING_TRACE=1` for native logging. Such logs can include local network addresses, so review them before sharing. Raw results contain synthetic IDs and aggregate counters only.

## Scope

These are transport experiments, not Word by Word model evaluations; `WW-CAT` scenario IDs and the four story slots are not applicable. A live fix still needs the standard Word by Word scenarios, actual H.264 delivery, native FFI counters and verified clip boundaries. The original 57/158 failure cannot be reconstructed from these synthetic inputs.
