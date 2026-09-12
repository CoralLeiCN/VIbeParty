# Laptop verification — 12 September 2026

This record separates working local behavior from unverified live acceptance. The first allocated real FastH3 capture passed in slot `2026-09-12-reverse-001`: one attempt,5s1344×768 MP4,16.49s total and independently confirmed terminal closure. A initialized the one shared nine-attempt campaign;8 remain. See the [current switch evidence](fasth3-switch.md#first-real-capture). Historical no-trial statements below describe prior checkpoints.

## Current provider: MiniMax FastH3

The user selected FastH3 through Reactor. The [switch record](fasth3-switch.md) documents the new queue/playback adapter, tests, browser checks and open live gates. Historical Helios and recording findings below describe earlier milestones. Current capture uses1344×768 and a matching FastH3 playback event; the unused recording downloader has been removed.

## Four-digit room-code acceptance

Commit `67bb2b2` adopts shared helpers from `4b4164d` and portal/resolver `35ecb71`. All61 Reverse Prompt/shared tests pass (40 Reverse Prompt), Ruff/formatting pass, and frontend build/ESLint pass. New HTTP regressions cover strings versus numbers/null/missing values, ASCII-only validation, the exact format/unavailable messages, leading-zero reservation/lookup/admission, same-roster reset, retired lookup/session, and malformed requests counting against the20/minute admission limit.

CUA browser acceptance used a temporary fixture-only server on8013 with the shared generator controlled to return `0042`; normal random generation was restored afterward. A/Ada used localhost, B/Ben the LAN origin, and C/Cam127.0.0.1, all on frontend5176. Verified host creation/display, Copy link success and its `?code=0042` destination, prefilled game join requiring explicit submission, portal manual code resolution preserving the query, `42` and fullwidth digits retaining editable text with the exact format message, unknown `0043` with the exact unavailable message, whitespace-padded ` 0042 ` admission, three-player roster, host refresh, Start, confirmed round Reset preserving code/roster, portal return/Continue availability, host Close party, expired guest identity and rejected old-code rejoin. Input DOM confirms `type=text`, `inputmode=numeric`, `pattern=[0-9]{4}`, and no max-length truncation. Existing private media/action checks also pass in the focused suite.

## Direct frame capture selected for the real demo

After the user requested genuine generated videos and suggested assembling screenshots, commit `a1dfbd6` changed the live route to encode the SDK's decoded frames directly. Reactor's [Track documentation](https://docs.reactor.inc/sdk-reference/python/track#on-raw-frame) exposes `on_raw_frame(bgra, width, height, frame_id, timestamp_us, user_data)`. Installed SDK1.5.1 `client.py` copies native pixels into immutable bytes on its delivery thread; `track.py` and `_ffi.py` identify zero frame ID/timestamp as absent metadata. Treating every zero ID as a duplicate would incorrectly stall capture.

The adapter accepts the first120 frames after starting the current prompt. A bounded16-frame queue feeds an owned FFmpeg subprocess, producing five seconds of24fps silent H.264/yuv420p MP4. Maximum frame dimensions by pixel count are1280×768; source aspect ratio is preserved. Known duplicate IDs are ignored; absent IDs are accepted; available timestamp reordering/span beyond15s, invalid dimensions/payloads and queue overflow fail unscored. Cancellation stops collection and kills/awaits the subprocess. Provider closure is still independently checked before local validation/publication. Optional provider recording is no longer a prerequisite. The legacy bounded recording-download helper remains isolated from the selected live route.

Actual FFmpeg tests on the laptop pass:120 frames,5s,24fps, one video stream, H.264/yuv420p, decoded first/last colors in the expected order, ignored late frames and process exit after cancellation. Provider-fake tests prove two fresh sessions receive only their current prompt and never request recordings; token constraints, attempt decrement, cancellation and closure guards remain enforced. All37 Reverse Prompt/shared tests pass (30 Reverse Prompt), plus Ruff/formatting. Synthetic test frames verify the encoder only; they are not Helios output or proof of live quality.

Integration checked the official dashboard on12 September: it redirected to sign-in, so account readiness could not be verified. [Official billing documentation](https://docs.reactor.inc/resources/billing) says programmatic usage/billing APIs are still in development and directs balance checks to the dashboard. There is no verified account-wide session-list endpoint in the reviewed SDK. The user has been asked for balance and previous-session closure confirmation; no campaign or slot is allocated yet.

## Runtime and scoring

Apple Silicon macOS; Python3.13.3; FFmpeg/ffprobe7.1.1; reactor-sdk1.5.1 native dylib loads. Shared lock pins Sentence Transformers6.0.1, CPU torch2.14.0, transformers5.17.0, huggingface-hub1.31.0, numpy2.5.3. MiniLM revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, checksum manifest required at runtime. Model directory is outside disposable media.

`offline_check.py` forbids socket connections before importing/loading/warming the model. Exact match100, paraphrase82, exact tie100/100 and over-token rejection pass. Warm batch ~9–12ms, shape3×384; max sequence256 including special tokens; process peakRSS ~480MB during the spike. Timed-out inference remains owned until completion; no overlapping model invocation is permitted. Invalid vectors or any inference failure produce a full unscored reveal with no ranking.

## Provider source findings

The [official SDK coordinator source](https://github.com/reactor-team/reactor-client-sdks/blob/9156ce9b09b3ebb8ed717d49d8ac69c5e44cec1d/crates/reactor-core/src/coordinator.rs) defines GET/DELETE `/sessions/{id}` and authentication headers. [Session states](https://github.com/reactor-team/reactor-client-sdks/blob/9156ce9b09b3ebb8ed717d49d8ac69c5e44cec1d/crates/reactor-protocol/src/session.rs) identify CLOSED/INACTIVE as terminal. The native [teardown code](https://github.com/reactor-team/reactor-client-sdks/blob/9156ce9b09b3ebb8ed717d49d8ac69c5e44cec1d/crates/reactor-core/src/reactor.rs) logs rather than propagates failed termination. Our guard consequently requires independent terminal GET/404, using a bounded DELETE of that same session if necessary. Tests prove a successful SDK disconnect with ACTIVE state cannot clear the guard.

The installed1.5.1 recording downloader assembles fragmented MP4 and performs blocking urllib I/O in a thread. The game uses cancellable HTTPX requests, bounded manifest/segment sizes, ordered init+fragments, and coordinator-only bearer credentials. FFmpeg probes actual source bytes; no assumed TS extension. Account recording availability, captured frame/manifest timing and provider closure/cap are still live gates. Public [recording documentation](https://docs.reactor.inc/concepts/recordings) currently differs from installed source on the container description.

## Browser rehearsal

CUA in-app browser over HTTP on frontend5176/backend8013. Trusted aliases localhost (A/Ada),127.0.0.1 (B/Ben),10.0.100.107 (C/Cam) isolate cookies on the same computer; these are three browser identities, not three physical phones.

Completed: create/join all three, host refresh preserving roster, author submission, B private clue, B interpretation, C private clue, C interpretation, final clip visible to A without a guess input, separate B/C guesses, accepted status, ordered three-card reveal, sample scores88/46, saved video playback/replay, portal return/Continue restoring reveal, host reset with same roster and guest refresh to lobby. All three reveal video elements report duration5s and640×384 without media errors. B’s clue played to currentTime5/ended=true; a reveal clip played to end and replayed from0. Desktop and390×844 lobby layouts were visually inspected; labels/readable counters/tap targets are present.

An accessibility native-control click crashed B’s first in-app tab after video decoded. Reopening the same URL in a fresh tab restored B’s session and clue; a coordinate click on the visible Play control then played successfully. Do not count this as physical-phone playback evidence. Native phone playback remains an event-device gate.

Backend restart was exercised before the full rehearsal: the UI displayed “This party has ended” and offered admission again. The live quota/unresolved persistence case is tested with a temporary allocated ledger, never the real campaign.

After absorbing integration `13ebbac`, clicking Copy join link on the LAN HTTP origin shows Copied through the shared clipboard fallback. A failed copy gives explicit select/copy guidance beside the visible address.

## Final local checks

`UV_CACHE_DIR=/private/tmp/vibeparty-reverse-uv bash scripts/check.sh` passes Ruff, formatting, frontend ESLint, production build and all 41 integrated backend tests. Twelve tests belong to Reverse Prompt. Its test directory is a package so identically named tests from different games collect independently. The only warnings are the shared Starlette test client's HTTPX/AnyIO deprecations.

The final quota regression rejects malformed history that falsely clears the unresolved marker or omits an attempt's session identity field. Storage errors become a blocking guard error. Source duration is capped strictly at fifteen seconds. Rehearsal fixture copies complete before cancellation can release cleanup. The socket-disabled real-model check still returns scores `[100,82]`, token limit256 and a10.7ms warm batch.

Organizer-admission follow-up `74e1150`: 30 Reverse Prompt/shared tests pass (23 Reverse Prompt), plus Ruff and formatting. HTTP regressions cover empty/whitespace/placeholder values from both shared settings and the game override, reject matching empty submissions and default-code fallback without creating a room or cookie, and accept a correctly configured Unicode override. This backend-only change follows integration's full41-test/build/lint validation at `2bc48cc`.

## Acceptance status

| ID | Evidence | Remaining |
| --- | --- | --- |
| DEMO-01 | Three CUA identities complete party; HTTP tests reject fourth and nonhost start/reset | Physical group rehearsal |
| DEMO-02 | Provider fake receives exactly three current-only prompts; real adapter creates a fresh client/token each call | Three real independent MiniMax FastH3 videos |
| DEMO-03 | HTTP tests cover private snapshots, full GET, HEAD, range and expired-turn media; CUA private clue flow | Live media repeat |
| DEMO-04 | Real pinned scorer offline; exact/paraphrase/token/tie tests; author exclusion; failed/timeout unscored behavior | Full live round using local scorer |
| DEMO-05 | Same receipt on duplicate; conflicting/stale bodies rejected; reset cancels retained provider work | Live duplicate/failure rehearsal |
| DEMO-06 | Browser refresh and real backend restart; persistent quota and startup blocker tests | Operator crash reconciliation on actual live campaign |
| DEMO-07 | Browser five-second H.264 decode/play/replay; three cards in order | Actual demo phone playback |
| DEMO-08 | Forced provider-fake timeout initiates cleanup and ends unscored; native disconnect failure test | Real forced generation failure, account cap/quota verification |
