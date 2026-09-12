# FastH3 laptop gate — 12 September 2026

The later [live enablement change](live-enablement.md) replaces the app's historical
verification and trial-slot flags with the presenter's live setting. The measured
capture failures below remain unresolved.

## Local compatibility evidence

- Runtime: Darwin arm64, Python 3.13.3, Node 24.3.0/npm 11.6.2.
- `reactor-sdk==1.5.1` installed and imported in an isolated temporary environment. No session was opened by installation or import.
- Installed source inspected: `fetch_jwt` accepts `models`, `max_sessions`, `max_session_duration_seconds`, `expires_after`. The token request includes the duration and count constraints. Constructing `Reactor(..., jwt=token)` avoids a second unconstrained token exchange.
- `Reactor.track('main_video').on_raw_frame` supplies decoded BGRA, dimensions, frame ID, sender timestamp, and optional metadata. Delivery occurs on an FFI thread. The SDK keeps the newest frame if the callback blocks; the capture must use a bounded queue and fail if it loses data.
- `disconnect()` requests nonrecoverable termination for sessions created by this client. Integration reports native shutdown can swallow errors: a returned call or disconnected local status is insufficient proof; independent provider closure remains required. It has no `recoverable` argument. An adopted session is not owned and cannot satisfy our cleanup contract; the game never adopts sessions.
- FFmpeg/ffprobe missing from the initial PATH; integration installed 7.1.1 at `/opt/homebrew/bin`. Four scripted fixture clips rendered successfully.

## Executable spike

The staged spike enforces one session, a 180-second provider limit, 120 seconds total, and 30 seconds per step, with no enqueue retry. It uses one predecessor chain and captures each clip before enqueuing the next. It drains to the advertised frame count after `clip_finished`, encodes H.264/yuv420p with fast start and no audio, probes and decodes each output, then requests nonrecoverable shutdown. It records timings and frame counts without tokens or raw model messages. This is an experimental gate, not a validated production adapter.

Frame count is insufficient to establish correct capture boundaries if idle/held frames are mixed in. Inspect first and last frames against clip events and inspect actual playback before considering the gate passed. A finish message indicates sender completion; it does not establish that the client's buffered frames arrived.

## Sources checked

- [FastH3 command reference](https://www.reactor.inc/models/fast-h3/api): predecessor IDs, explicit playback, consumed queues, advertised clip frames/duration, six-second input snapping, 4,000-character/1,024-token prompt bounds.
- [Reactor Python SDK](https://docs.reactor.inc/sdk-reference/python/reactor) and [Track API](https://docs.reactor.inc/sdk-reference/python/track): capture callbacks and shutdown.
- [Authentication](https://docs.reactor.inc/authentication): model scopes, one-session allowance, provider lifetime cap.
- [Billing](https://docs.reactor.inc/resources/billing): idle GPU time is billable; actual spend requires the account dashboard. The billing page's Python recoverable example conflicts with the installed SDK and current session reference; use the installed nonrecoverable signature.

## Live acceptance evidence

Three real trials are complete, with failed capture gates and independently confirmed closure (details below). This batch's three-attempt allocation is exhausted. Continuity, complete capture boundaries, maximum cumulative Unicode token fit, saved duration/replay, provider-enforced lifetime expiry, and account spend remain unverified. The actual 30-second step timeout and explicit cleanup were exercised. Required successful campaign: two forest/fox/dancing/confetti runs and one group-selected phrase/sentence variation, coordinated one at a time by integration. Fixture clips do not count toward this evidence.

## Guarded adapter and mock evidence

The game now has a direct `FastH3Provider`, wired behind explicit game-local operator gates. The spike reuses it. Fixture mode remains the default. Capture verification, cumulative prompt-limit verification, an allocated integration slot, confirmed previous-session closure, and a configured credential are all required before live admission. No verification flag has been enabled here.

SDK/native primary source inspected at `reactor-team/reactor-sdk` commit `9156ce9b09b3ebb8ed717d49d8ac69c5e44cec1d`: [coordinator session requests](https://github.com/reactor-team/reactor-sdk/blob/9156ce9b09b3ebb8ed717d49d8ac69c5e44cec1d/crates/reactor-core/src/coordinator.rs) and [terminal state definition](https://github.com/reactor-team/reactor-sdk/blob/9156ce9b09b3ebb8ed717d49d8ac69c5e44cec1d/crates/reactor-protocol/src/session.rs). Independently GET the owned session using its scoped JWT and API-version headers. Only HTTP 404 or `CLOSED`/`INACTIVE` confirms closure. Otherwise DELETE that same owned session and re-check. Authentication errors, active/suspended/unknown states, lost creation identity, and timeouts keep the game blocked. The SDK's local disconnected status does not clear this guard.

Fourteen new checks use mocked HTTP/SDK messages and synthetic BGRA frames only. They verify the one-session/180-second token request, four cumulative prompts and predecessor IDs, decodeable saved outputs after closure, ambiguous enqueue refusal without retry, startup acknowledgment requirements, bounded queue overflow, cancellation and late-frame rejection, provider failure, and independent closure success/failure/retry. They do **not** prove real FastH3 boundaries, throughput, continuity, token fit, cost, or account access.

The experimental capture arms on the matching `clip_started`, rejects queue overflow/dimension changes/non-monotonic IDs, and requires the advertised frame count plus matching `clip_finished`. Event/frame ordering remains a measured gate. The public FastH3 reference has detailed clip examples but some generated message tables say “No fields”; the actual wire envelope/frame timing must be checked during the coordinated spike. Never mark this adapter verified solely because its mocks pass.

At the initial readiness checkpoint, integration reported the account dashboard redirected to sign-in and no documented account-balance/session-list API suitable for readiness checks was established. **Actual attempts at that checkpoint: 0.** The user's subsequent direction to use the key waived this dashboard precheck; the three actual trials and their closure evidence below supersede that blocked status.

## Requested live campaign: readiness recheck

After the operator explicitly requested the real generation trials, this session requested the first exclusive allocation again: one FastH3 session, four additive clips, 180-second provider lifetime, 120 seconds overall and 30 seconds per segment. Integration confirmed that this allocation remains ungranted until account credits and prior-session closure are established. A fresh browser visit to the documented dashboard redirected to `https://www.reactor.inc/auth?next=%2Fdashboard`; the sign-in tab was handed to the operator. Credential presence/prefix and both capture executables were checked locally without exposing credentials. No provider session or token exchange was attempted.

The spike now retains the stage reached, per-step prompt code-point counts, enqueue/generation timings, incomplete capture metrics, frame-ID gaps, event/frame receipt intervals, bounded queue peak, cleanup duration, and allowlisted independent closure status. Private evidence contains no accepted text, token, raw provider body or queue payload. These diagnostics will support the first real trial; they are not live acceptance evidence. All 14 focused mock/capture checks pass, including evidence privacy and buffered frames arriving after the sender's finish event. Ruff and formatting pass.

## Actual trial 2026-09-12-word-001

The user directed use of the existing API key without dashboard validation. Integration granted one exclusive session attempt; account prechecks were recorded as waived, not passed. The 14:26:52 UTC trial used the fixed forest/fox/dancing/confetti contributions on this Darwin arm64 laptop. [Sanitized actual evidence](evidence/2026-09-12-word-001.json); owned session identity and private source remain in `.local/word-live/2026-09-12-word-001/evidence.json`.

| Observation | Actual result |
| --- | --- |
| Authentication | Token HTTP 200; existing key worked |
| Session startup/settings | 8.407 seconds; all required settings acknowledged |
| First enqueue | Acknowledged in 0.212 seconds; 233-code-point prompt |
| First generation completion | Reported 4.522 seconds after enqueue began |
| Capture | Stopped before playback: `missing_clip_frame_count`; no saved clips |
| Total/cleanup | 14.066 seconds total; cleanup 1.137 seconds |
| Independent closure | Owned-session GET HTTP 200, `CLOSED` |
| Attempts/spend | One real session attempt; account spend unmeasured |

This establishes key access, first generation completion and explicit shutdown/independent closure. It does not establish playable capture or continuity. No paid request was retried. The absent/non-integer frame count was not retained in the original diagnostic, so its exact wire representation is unknown. Code review found absent completion metadata could overwrite valid enqueue metadata, and whole-number JSON floats were refused. Commit `2fbd4a9` preserves acknowledged values, accepts exact integral numeric frame counts, and can read the existing playout queue for missing metadata without another enqueue. Forty Word tests pass, including two focused compact-event regression cases; Ruff and formatting pass. A second trial has been requested but must be allocated before running.

The newer [FastH3 schema](https://docs.reactor.inc/model-api-reference/fast-h3/schema) publishes an 800-character prompt bound, whereas the marketing API page still states 4,000 characters/1,024 tokens. The implementation now enforces the stricter 800-character limit. All four maximum-length accepted contributions plus exact fixed instructions total 732 Unicode code points. Character fit is established; cumulative Unicode token fit is not yet established and live admission remains gated.

## Actual trial 2026-09-12-word-002

Integration allocated one further attempt after reviewing the first session's closure. The 14:30:33 UTC run used correction `2fbd4a9` and the same fixed chain. [Sanitized actual evidence](evidence/2026-09-12-word-002.json).

| Observation | Actual result |
| --- | --- |
| Authentication/startup | Token HTTP 200; startup 5.985 seconds |
| First generation | Enqueue acknowledged in 0.018 seconds; generated in 5.958 seconds |
| Clip metadata | Enqueue and completion both parsed as 158 frames |
| Capture | First decoded frame received; stopped on repeated zero frame ID; no saved clip |
| Failure | `non_monotonic_frame_ids`; first ID and timestamp both zero |
| Total/cleanup | 12.728 seconds total; cleanup 0.519 seconds |
| Independent closure | Owned-session GET HTTP 200, `CLOSED` |
| Attempts/spend | Two cumulative real attempts today; account spend unmeasured |

The locked SDK's native [frame callback](https://github.com/reactor-team/reactor-sdk/blob/9156ce9b09b3ebb8ed717d49d8ac69c5e44cec1d/crates/reactor-ffi/src/peer.rs#L517) substitutes `(0, 0, empty)` when optional frame metadata is absent. The installed `track.py` documents the zero timestamp. Reverse Prompt had independently recorded this SDK behavior; its owned files were read without modification. Commit `853fe02` handles absent metadata using callback delivery order and explicitly records missing-metadata counts and an unavailable gap measurement. Genuine non-monotonic supplied identifiers still fail. Bounded buffering, advertised-frame count, matching finish event, full decode and duration checks remain. These checks cannot establish network frame completeness without identifiers; visual boundary review remains required. Forty-two Word tests pass, including complete synthetic capture with absent metadata and rejection of meaningful duplicate IDs; Ruff and formatting pass. A third separately coordinated trial is requested; no fourth attempt is authorized.

## Actual trial 2026-09-12-word-003 — capture gate failed

Integration allocated the third and final attempt of this batch. The 14:33:24 UTC run used correction `853fe02` and the same fixed chain. [Sanitized actual evidence](evidence/2026-09-12-word-003.json).

| Observation | Actual result |
| --- | --- |
| Authentication/startup | Token HTTP 200; startup 7.549 seconds |
| First generation | Enqueue acknowledged in 0.186 seconds; generated in 4.387 seconds |
| Advertised/delivered frames | 158 expected; 156 captured, all without optional identifiers/timestamps |
| Local queue | Peak 2 of 8, no overflow or capture error |
| Event timing | First frame 0.207 seconds after start event; finish event at 6.504 seconds; last frame 0.109 seconds after finish |
| Frame delivery span | 6.405 seconds; source frame completeness cannot be established |
| Application deadline | Step timed out at 30.004 seconds while awaiting remaining frames |
| Media result | Zero valid saved clips; incomplete temporary MP4 removed |
| Total/cleanup | 38.415 seconds total; cleanup 0.862 seconds |
| Independent closure | Owned-session GET HTTP 200, `CLOSED` |
| Attempts/spend | Three cumulative real attempts; account spend unmeasured |

No fourth attempt was made or requested. All three owned sessions are independently closed and integration was notified. The existing API key works; it is not the blocker. The measured blocker is complete frame capture: the client obtained two fewer frames than advertised without overflowing its local queue. The evidence does not identify whether loss occurred in event ordering, decoding, SDK delivery, transport, or the provider's declared length. Do not lower the frame requirement merely to turn this failure into a pass.

Before allocating another batch, investigate capture boundaries and a reliable provider export path; add bounded pre-start/post-finish frame counters and private diagnostic retention if needed to locate the shortfall. Any diagnostic partial video must remain separate from valid game media. Re-run complete capture and inspect first/last frames and replay before attempting continuity or maximum Unicode token claims. Live remains disabled; fixture behavior and its separate evidence remain available. No dependency/configuration change has been requested yet.
