# Word by Word capture timeout investigation

Investigated 12 September 2026 against commit `0149761`, Reactor SDK 1.5.1,
and the saved local live evidence. The latest two recorded runs completed model
generation in about 4.4 seconds, then timed out while collecting the first clip's
decoded video frames. The 30-second application step deadline fired with one or
two frames still missing. No valid clip was saved.

## Latest recorded runs

Times below are evidence-file modification times in UTC, not recorded session
start times. The private source files are under
`.local/vibeparty/word-by-word/live-evidence/`. No session identifiers, credentials,
or player contributions are reproduced here.

| Evidence recorded | Startup | Generation from enqueue | Captured / expected frames | Queue peak / limit | Step duration | Result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 16:46:19 | 9.445 s | 4.404 s | 9 / 158 | 8 / 8 | 5.073 s | `frame_queue_overflow` |
| 17:06:29 | 8.033 s | 4.374 s | 157 / 158 | 5 / 32 | 30.013 s | Waiting for remaining frame |
| 17:12:39 | 6.113 s | 4.426 s | 156 / 158 | 2 / 32 | 30.011 s | Waiting for remaining frames |

All three records show token HTTP 200, acknowledged generation, and independent
HTTP 200 / `CLOSED` confirmation during cleanup. The latest two report no local
capture error or queue overflow. The earlier startup overflow was addressed by
the [capture buffer change](capture-buffering.md); enlarging that queue did not
resolve the subsequent frame shortfall.

For the latest run, the matching finish event arrived 6.502 seconds after the
start event. The last accepted frame arrived 0.144 seconds after finish. The
capture remained pending until the step deadline. All 156 accepted frames lacked
optional source identifiers and timestamps, so their precise source positions
cannot be recovered from this evidence.

## Why the app says generation timed out

In `backend/games/word_by_word/live.py`, `FrameCapture.write()` loops until it has
written exactly the provider's advertised frame count. An empty queue causes a
5 ms sleep followed by another check. The writer checks `clip_finished` only
after reaching that count. Consequently, receiving finish with 156 or 157 of 158
frames leaves the writer waiting for additional frames until cancellation.

`FastH3Provider.segment()` waits for that writer. In
`backend/games/word_by_word/service.py`, the 30-second timeout wraps the whole
segment: enqueue, generation, playback, encoding, and validation. Any timeout in
those phases becomes the same public message, "Generation timed out." The
120-second round deadline and 180-second session cap were not reached in these
runs.

The provider documents `clip_generated` as a completed build and `clip_finished`
as completion of sending the clip. Neither says the receiver has captured every
frame. See the [FastH3 command reference](https://www.reactor.inc/models/fast-h3/api).

## What remains uncertain

The immediate cause is established: capture waits for frames that have not
arrived. The saved counters do not locate the original loss. Candidates are:

- Event ordering: the app ignores callbacks before the matching `clip_started`;
  it currently does not count those discarded frames.
- SDK delivery: installed `reactor_sdk/client.py` documents that the native
  delivery layer retains only the newest frame while a callback is busy. This
  allows loss before the app's queue, even when that queue never fills.
- Transport, decoding, or a difference between the advertised count and emitted
  video. Existing evidence has no transport/decode statistics to distinguish them.

These are possible mechanisms, not a determination that a particular layer
dropped the missing frames. The zero identifier/timestamp fallback was confirmed
in the locally available Reactor SDK native source at commit
`9156ce9b09b3ebb8ed717d49d8ac69c5e44cec1d`.

## Local reproduction

Ran the current `FrameCapture` with synthetic 32×32 BGRA frames, absent optional
metadata, real FFmpeg encoding, an expected count of 158, and a finish event after
delivery. No provider was constructed or called. Queue peak stayed at two frames.

| Delivered | After finish | Capture error | Saved output |
| ---: | --- | --- | --- |
| 156 | Still waiting after a 0.5 s observation window | None | None |
| 157 | Still waiting after a 0.5 s observation window | None | None |
| 158 | Writer completed within the observation window | None | MP4 |

The incomplete cases were cancelled and temporary files removed. This confirms
the waiting condition; it does not reproduce the upstream loss. This was a
capture-only diagnostic, with no category/model rehearsal or WW-CAT scenario.
Scenario IDs for the existing private runs were not recorded and are unknown.

## Recommended follow-up

1. Record callback counts before start, during capture, and after finish, plus
   allowlisted SDK `get_stats()` video counters. Distinguish capture timeouts from
   generation timeouts in diagnostics and the player-facing message.
2. Verify FastH3 support for Reactor's recording/download path as an alternative
   to collecting every decoded live frame. The [recording documentation](https://docs.reactor.inc/concepts/recordings)
   requires model recording support and requests while the session is ready;
   support and accurate per-clip boundaries have not been established here.
3. Validate the chosen capture path with an authorized live run using the
   [standard scenarios](../../games/word-by-word/test-scenarios.md), then inspect
   saved boundaries and replay. Increasing the timeout alone cannot recover
   discarded frames; weakening the count check would not establish completeness.

This investigation changed documentation only. It made no new paid generation
requests and did not restart the application or alter timeout settings.
