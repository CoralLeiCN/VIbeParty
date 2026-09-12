# FastH3 laptop gate — 12 September 2026

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

No completed live trial yet. Continuity, capture boundaries, maximum cumulative Unicode prompt fit, actual duration, provider-enforced shutdown, and account spend are unverified. Required campaign: two forest/fox/dancing/confetti runs and one group-selected phrase/sentence variation, coordinated one at a time by integration. Fixture clips do not count toward this evidence.

## Guarded adapter and mock evidence

The game now has a direct `FastH3Provider`, wired behind explicit game-local operator gates. The spike reuses it. Fixture mode remains the default. Capture verification, cumulative prompt-limit verification, an allocated integration slot, confirmed previous-session closure, and a configured credential are all required before live admission. No verification flag has been enabled here.

SDK/native primary source inspected at `reactor-team/reactor-sdk` commit `9156ce9b09b3ebb8ed717d49d8ac69c5e44cec1d`: [coordinator session requests](https://github.com/reactor-team/reactor-sdk/blob/9156ce9b09b3ebb8ed717d49d8ac69c5e44cec1d/crates/reactor-core/src/coordinator.rs) and [terminal state definition](https://github.com/reactor-team/reactor-sdk/blob/9156ce9b09b3ebb8ed717d49d8ac69c5e44cec1d/crates/reactor-protocol/src/session.rs). Independently GET the owned session using its scoped JWT and API-version headers. Only HTTP 404 or `CLOSED`/`INACTIVE` confirms closure. Otherwise DELETE that same owned session and re-check. Authentication errors, active/suspended/unknown states, lost creation identity, and timeouts keep the game blocked. The SDK's local disconnected status does not clear this guard.

Fourteen new checks use mocked HTTP/SDK messages and synthetic BGRA frames only. They verify the one-session/180-second token request, four cumulative prompts and predecessor IDs, decodeable saved outputs after closure, ambiguous enqueue refusal without retry, startup acknowledgment requirements, bounded queue overflow, cancellation and late-frame rejection, provider failure, and independent closure success/failure/retry. They do **not** prove real FastH3 boundaries, throughput, continuity, token fit, cost, or account access.

The experimental capture arms on the matching `clip_started`, rejects queue overflow/dimension changes/non-monotonic IDs, and requires the advertised frame count plus matching `clip_finished`. Event/frame ordering remains a measured gate. The public FastH3 reference has detailed clip examples but some generated message tables say “No fields”; the actual wire envelope/frame timing must be checked during the coordinated spike. Never mark this adapter verified solely because its mocks pass.

Integration reports the official account dashboard currently redirects to sign-in, with no documented account-balance/session-list API suitable for readiness checks. Operator account readiness and an exclusive trial allocation remain required. **Actual live attempts in this worktree: 0.** No account spend or live closure result is claimed.
