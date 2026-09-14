# Word by Word: capture fix proposal

Researched 13 September 2026. This is a proposal, not an implemented or live-validated fix. Reviewed the saved 57/158-frame failure, application code, installed Reactor SDK 1.5.1, current public SDK source, and Reactor's reference clients. This research made no new generation requests.

Subsequent investigation: [two instrumented live runs](decoded-frame-loss-2026-09-13.md) located loss after decoding and before Python. They identify WebRTC's enabled playback smoother as an earlier frame-dropping stage to investigate, ahead of the native callback queue. That follow-up revises the first native experiment to bypass smoothing and use an observable FIFO together; changing the FIFO alone is insufficient if the smoother already discarded frames.

Experiment results are now recorded in the [smoothing study](smoothing-experiment-2026-09-13.md). Controlled tests using the actual native smoother reproduced missing frames and matched its internal drop counter. Local VP8 connections did not reproduce loss; a complete SDK/FastH3 capture-mode comparison is still required.

## Recommendation

Fix the capture lifecycle and add measurements first. Then select a recording path that can preserve the clip: preferably a provider-produced artifact with verified FastH3 support and clip boundaries; otherwise an instrumented capture path with an explicit native buffering policy. Keep rejecting substantially incomplete video.

These solve different problems. A bounded finish/drain state fixes the unnecessary wait and misleading timeout. It does not recover the 101 frames absent from this run. Preserving those frames requires establishing where delivery lost them and changing that part of the path. Neither a larger application queue nor a longer timeout establishes a complete recording.

## What the failure establishes

The private evidence is `.local/test-runs/2026-09-13-live/word-evidence.json`:

| Observation | Result | Implication |
| --- | ---: | --- |
| Generation acknowledged complete | 158 frames in 4.401 s | Generation completed before capture failed. |
| Frames accepted by the application | 57/158, about 36% | Most of the expected video never entered the capture queue. |
| Application queue peak | 1 of 32 frames | This run did not exhaust the application buffer. |
| Matching sender finish | 6.482 s after start | The sender reported playback complete. |
| Last accepted frame | 0.236 s after finish | Stopping immediately on the control event would truncate late delivery. |
| Step completion | Timeout at 30.007 s | The writer continued waiting after delivery stopped. |
| Frame identifiers/timestamps | Missing on all 57 frames | Exact lost positions and media boundaries cannot be reconstructed. |

At 24 fps, 158 frames represent 6.583 seconds. Writing 57 frames at that rate produces only 2.375 seconds. Repeating them until the output contains 158 frames would manufacture a duration without restoring the missing action.

`FrameCapture.write()` in `backend/games/word_by_word/live.py` waits for the advertised count before checking its finish event. The segment deadline in `backend/games/word_by_word/service.py` covers generation, capture, encoding, and validation, but reports them all as a generation timeout. The earlier [timeout investigation](timeout-investigation-2026-09-12.md) reproduced the same waiting condition with 156 and 157 frames using real FFmpeg.

The saved run cannot distinguish SDK queue loss, transport/decode loss, callbacks rejected before start, or an emitted-count mismatch. The SDK mechanism below is verified; attributing all 101 missing frames to it would exceed the evidence.

## What Reactor actually provides and recommends

### Live callbacks prioritize freshness

The native SDK constructs its video delivery thread with capacity **one** and a drop-oldest policy. This queue sits between WebRTC decoding and the Python callback. Its comments explain that host callbacks can stall acquiring Python's GIL; media threads must remain free to decode and receive. The drop counter is internal and is logged at debug level on powers of two. It is not an application queue counter. [Native queue construction](https://github.com/reactor-team/reactor-client-sdks/blob/9156ce9b09b3ebb8ed717d49d8ac69c5e44cec1d/crates/reactor-ffi/src/lib.rs#L893), [callback and overflow implementation](https://github.com/reactor-team/reactor-client-sdks/blob/9156ce9b09b3ebb8ed717d49d8ac69c5e44cec1d/crates/reactor-ffi/src/callbacks.rs).

Reactor documents `on_raw_frame` for forwarding decoded bytes without the additional NumPy conversion. It does not expose encoded packets or promise every generated frame. Our application already uses that API and a short synchronous callback, so switching callback APIs is not a new fix. [Python track API](https://github.com/reactor-team/reactor-client-sdks/blob/9156ce9b09b3ebb8ed717d49d8ac69c5e44cec1d/sdks/python/reactor_sdk/track.py#L432).

The installed version is the latest published package, **1.5.1**, uploaded 11 September 2026. Its `client.py` and `track.py` are byte-identical to the files at public SDK commit `9156ce9b09b3ebb8ed717d49d8ac69c5e44cec1d`. There is no newer published SDK upgrade to recommend from this inspection. [Published package](https://pypi.org/project/reactor-sdk/1.5.1/).

### Reference clients accept stream semantics

Reactor's FastH3 sample creates a capture at `clip_started`, stops assigning frames at `clip_finished`/`clip_stopped`, and encodes the frames it actually received at 24 fps. It does not wait for the advertised count. This demonstrates a reference capture pattern, not a guarantee of complete recordings. Copying its immediate stop would discard late frames in our measured run. [FastH3 reference client](https://github.com/reactor-team/infinite-livestream/blob/c2326e49ca29149d67fe3b97fb9908d31bb6716f/fast-h3/client/client.py).

The continuous streaming client uses a paced output, repeating frames on underflow and dropping old frames on overflow. It also keeps blocking FFmpeg pipe writes off the event loop with bounded worker queues. That is appropriate for a continuous broadcast. Applying it to Word by Word would require an explicit policy for tolerated missing motion; it cannot establish complete source capture. [Streaming client guidance](https://github.com/reactor-team/infinite-livestream/blob/c2326e49ca29149d67fe3b97fb9908d31bb6716f/streaming-client/README.md).

### Recording downloads are conditional

The generic SDK offers `request_clip(seconds)`, `request_recording()`, and download helpers. The documentation requires recording to be enabled for the model. These refer to time windows in a session recording, not an export by FastH3 generation clip ID. [Recording guide](https://docs.reactor.inc/concepts/recordings).

The public FastH3 reference README explicitly leaves recording disabled. It also describes independent clips without continuation, whereas the hosted FastH3 API documents continuation and configurable hold/flush behavior. Therefore the reference is evidence about that implementation, not proof that the current hosted deployment has recording disabled. Hosted recording support remains unverified. [Reference model limitations](https://github.com/reactor-team/infinite-livestream/blob/c2326e49ca29149d67fe3b97fb9908d31bb6716f/fast-h3/README.md#clip-boundaries-are-hard-cuts), [current hosted API](https://www.reactor.inc/models/fast-h3/api).

The Python recording example defaults to Helios, waits for media, requests a window, and waits for the recorder to complete its chunk. Readiness advances with recorded media rather than merely elapsed wall time. The download contains fragmented MP4, and mid-session timestamps need normalization for standalone clips. Our implementation would need bounded download and cleanup behavior rather than copying the example's indefinite wait. [SDK recording example](https://github.com/reactor-team/reactor-client-sdks/blob/9156ce9b09b3ebb8ed717d49d8ac69c5e44cec1d/sdks/python/examples/06_record_clip.py), [Python recording guidance](https://github.com/reactor-team/reactor-client-sdks/blob/9156ce9b09b3ebb8ed717d49d8ac69c5e44cec1d/sdks/python/README.md#recordings).

## Proposed implementation

### 1. Make capture completion bounded and diagnosable

Change `FrameCapture` to track waiting-for-start, receiving, draining, and finalizing explicitly. A matching finish event starts a bounded drain even when the count is short. An initial **one-second maximum after finish** is a proposed diagnostic setting, to validate against measured network tails; it is not a Reactor guarantee. Keep the existing overall step and session limits. Stop admitting further playback until this capture has finalized.

If frames remain missing when that window expires, cancel the encoder, remove the partial output, and report `capture_incomplete` with expected/received counts. Preserve separate errors for generation timeout, no first frame, playback interruption, queue overflow, and encoding failure. The host should see “The video stream ended before capture completed” for this case. Keep internal counts in diagnostics.

Continue requiring valid silent H.264, dimensions, size, duration, and full decoding before publication. An equal callback count alone does not prove boundary correctness: held frames or callbacks from the wrong interval can satisfy a count. Retain the visual boundary gate, and record absent source metadata explicitly.

### 2. Measure loss at each boundary

Add bounded, allowlisted counters and timing summaries:

- All raw callbacks, including callbacks before start, after finish, with no active capture, and rejected for each reason. Record callback time and capture phase; do not enqueue unbounded diagnostic work.
- Application callback duration, maximum interarrival gap, event-loop lag, queue occupancy, and FFmpeg write/drain time.
- `get_stats()` snapshots before play and after the drain, plus low-rate samples during playback where available: inbound video frames decoded/dropped, packets received/lost, NACKs, decode time, RTT, jitter, and connection type. Use deltas and preserve unavailable values as null.
- The native queue's drop diagnostics, scoped to `reactor_ffi::callbacks` rather than enabling broad SDK logs. Its existing messages report sampled cumulative counts; an exact structured counter would require an SDK addition.

Reactor exposes transport/decode counters through `get_stats()` and advises sampling bitrates at least 200 ms apart, usually every few seconds. These counters can narrow the diagnosis but are not per-clip source-frame acknowledgements. [SDK statistics guidance](https://github.com/reactor-team/reactor-client-sdks/blob/9156ce9b09b3ebb8ed717d49d8ac69c5e44cec1d/sdks/python/README.md#connection-statistics).

### 3. Choose the frame-preserving path from the evidence

| Finding | Proposed change | Limitation to verify |
| --- | --- | --- |
| Hosted FastH3 provides a complete recording/export with usable boundaries | Download privately, cut by verified media boundaries, normalize timestamps, remove audio, validate, then publish | Confirm recording support, final-chunk readiness while idle, completeness, and mapping to all four generation IDs before adopting it. |
| Native delivery drops frames while decode counters remain healthy | Isolate capture from other Python work if timing shows contention; evaluate an opt-in bounded FIFO in the native SDK | The one-frame depth is hard-coded. A FIFO needs a pinned native build/vendor release, frame and byte caps, observable overflow, and safe shutdown. It cannot repair loss before decode. |
| Many callbacks precede the start event | Correct synchronization using sender frame markers or another verified media boundary | Blindly arming at `play` or retaining a pre-roll can include black or the preceding clip's held frame. Without markers, this remains a boundary experiment. |
| Transport/decode already loses frames | Diagnose the measured connection and seek a provider-side artifact | Increasing either local queue cannot recover those frames. |

For a native FIFO experiment, start with a bounded capacity and byte budget comparable to the app's existing 32-frame/128 MiB limit, account for both queues in total memory, and reject recording on overflow. Do not block WebRTC's media thread and do not silently change the default live-display policy for other games. This is our proposed SDK extension, not a configuration Reactor currently exposes.

The preferred durable solution for saved replay is a verified provider-produced clip artifact. Until that support is established, the practical first increment is the bounded lifecycle plus measurements above. It improves failure handling immediately and supplies the evidence needed to choose an effective delivery change.

### 4. Do not silently relax the recording requirement

A separate product option is to tolerate a very small shortfall after boundary review. For example, 156/158 received frames represent 98.7% of the count and 6.5 seconds at 24 fps. That could yield an acceptable clip, but count coverage does not establish which action or boundary was lost. Any threshold would be our product decision and would revise the current requirement to reject incomplete captures.

This proposal does **not** recommend enabling that fallback by default. It must never make the 57/158 case pass by padding, slowing playback, or deleting the completeness check.

## Validation and questions for Reactor

Before another live comparison, use native-thread delivery and real FFmpeg to exercise complete delivery, 156/157-frame shortfalls, 57-frame severe loss, late frames after finish, callbacks preceding start, no finish, overflow, cancellation, and adjacent clips with distinct visual markers. Verify bounded completion, no published partial file, and no cross-clip contamination. A synthetic callback test does not by itself test Reactor's native one-frame queue; any SDK buffering experiment also needs a test through that queue.

Then use the [standard scenarios](../../games/word-by-word/test-scenarios.md): `WW-CAT-01` twice and `WW-CAT-02` once, preserving the current four-slot mapping and existing spending/session limits. Record transport/capture results separately from visual story results. Review all four additions and boundaries, private collection, manual reveal, and replay after independent session-closure confirmation. No scenario was rerun during this research.

Concrete questions to take to Reactor, with sanitized evidence:

1. Does hosted `reactor/fast-h3` support runtime recording today, and is there an artifact/export API keyed by its generation `clip_id`?
2. If only session recording is available, how can a client obtain exact clip boundaries and finalize the last chunk while the model holds between plays?
3. Is an opt-in bounded FIFO or native recording sink available instead of the current capacity-one video callback queue? Can native drop counters be exposed through SDK statistics?
4. Why are source frame IDs and timestamps absent in this deployment, and can each frame carry a clip ID and frame index for reliable boundary validation?

These questions have not been sent to Reactor. No application behavior, dependency pin, or running service was changed by this research.
