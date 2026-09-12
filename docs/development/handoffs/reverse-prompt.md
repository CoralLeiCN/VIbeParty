# Reverse Prompt handoff

Owner: session D. Branch `codex/reverse-prompt`. Backend 8013; frontend 5176.

## Current checkpoint — one session per round

Implementation milestone: `11a9010`, with evidence recorded in `b55685e`. This handoff accompanies the user-requested squash landing of `codex/reverse-prompt` onto local `main`, preserving the existing `25c60bf` integration baseline.

The latest user instruction replaces separate provider sessions and unlimited relay thinking with **one FastH3 session retained through both30-second B/C turns**. Each clip still receives only its own prompt and the fixed instruction, with no continuation or image input. The server enforces the relay deadline, and refresh preserves the remaining time. A's original input and final guesses remain untimed. Expiry stops unscored and closes the session.

One session opens when A submits and closes after V2 is validated, before guessing. Failure, reset, party closure and shutdown own the same cleanup. The per-generation deadline remains90 seconds; the provider cap is360 seconds with a345-second application watchdog. Quota accounting still consumes one attempt per accepted prompt. The backward-compatible `session_attempt` group holds up to three attempts unresolved until a terminal GET closes them atomically. Retired clip events and idle frames cannot become another player's capture. The detailed [session-reuse record](../../research/reverse-prompt/session-reuse.md) and [current API contract](../contracts/reverse-prompt/README.md) describe the implementation.

Final validation:166 backend tests pass (63 Reverse Prompt), game Ruff/format checks pass, and frontend build/lint pass. The complete suite used the existing pinned Prompt Royale tokenizer in a temporary cache; no shared files or package pins changed. Browser checks on8013/5176 passed both timed private turns, refresh preserving B's countdown, expiry ending unscored, same-roster reset, untimed final guesses, ordered88/46 rehearsal reveal and portal party closure. Provider fakes use real FFmpeg to verify three clips in one token/session, unchanged current-only inputs, separate captures, delayed old events, grouped quota closure and a second-clip failure without a third attempt. No new paid call was made. Live reuse and physical-phone acceptance remain unverified.

**Current setup blocker:** the archived integration worktree5a4f has been removed, including the configured canonical quota file. Its last independently verified state was7 remaining,2 closed attempts and no unresolved session. The current record cannot be read; no replacement or replenished ledger was created. Restore that original campaign record to durable storage before live operation. Live mode remains false. The pinned local MiniLM and saved successful001 video remain available in this worktree.

No dependency or shared configuration schema change is required. The shared game specification, technical plan, parallel plan and checklist now describe the retained session, relay deadlines and missing campaign record. Further live-trial coordination remains stopped.

## Prior checkpoint — separate sessions (historical)

The backend, frontend, independent MiniMax FastH3 adapter through Reactor, pinned local scorer, scripted rehearsal, fixtures and operator scripts are implemented. The user selected FastH3 in place of Helios on12 September2026. The full three-player scripted flow has passed browser verification. Game availability is enabled for the labelled rehearsal. The first independent real FastH3 capture passed in allocated slot `2026-09-12-reverse-001`: one attempt, five-second1344×768 video,16.49s total, independently confirmed terminal closure. The subsequent full-relay slot `2026-09-12-reverse-002` failed on its first generation and stopped unscored. Both consumed attempts are independently closed;7 remain with no unresolved session. The two unused allocations were cancelled, and the user stopped further live-trial coordination. Full live-round and physical-phone acceptance remain incomplete.

The implementation starts from published foundation `eb831d80310ae548374143f236c90caf73a90c00` and includes shared integration baseline `4d973a8ecf68a3144b5f1888e064e21596f68ab0`, plus FastH3 shared-reference alignment `30f4512` absorbed by normal merge `767cabf`. Four-digit room codes are adopted from the accepted shared standard. The switch milestone passed71 Reverse Prompt/shared tests (50 game tests); the compact-completion follow-up passes all14 provider tests, with Ruff, formatting, frontend build and lint. Browser checks cover the controlled leading-zero code `0042`, all admission paths and reset/close. Actual FFmpeg encoding/decoding/cancellation and the socket-disabled real MiniLM scorer remain verified.

## Milestone commits

| Commit | Reviewable result |
| --- | --- |
| `426c5e4` | Persistent sanitized generation diagnostics, private-exception and unavailable-storage regressions; all54 game tests pass. No additional live call. |
| `1a3221a` | Failed first step of real relay002, terminal closure, persistent allowance, browser reset/close and user stop recorded separately from the diagnostics follow-up. |
| `e7b9ac6` | First successful real FastH3 capture and sanitized evidence; one five-second clip,16.49s total, independent terminal closure. |
| `9e71dbb8798e42696b0bfef6feaa3723342acc21` | Preserve compact FastH3 completion metadata; read the existing matching queue item once when needed;14 provider tests pass, including actual encoding for all three metadata shapes. Integrated by A at `9e6d2ba`. |
| `cfc422cc9ac92ce6effb19d647a1f5e1696f9e00` | Switch to MiniMax FastH3 through Reactor: independent queued clips, correlated playback capture,1344×768 output, fail-unscored cleanup and focused tests. Frontend model copy and research/runbook updated;71 Reverse/shared tests and browser admission checks pass. |
| `cecbf53` | Backend state/actions, role privacy and range authorization, guarded Helios adapter, persistent quota, pinned scorer, operator scripts and fixtures. Integrated by A at `62b0874`. |
| `65322cc` | Complete frontend, scripted relay/reveal/reset, browser recovery and retained inference ownership. Integrated by A at `faa6b16ac93ae558cd025b9dbd754fcda783a390`. |
| `d29501d` | Validate complete quota history, enforce fifteen-second source cap, finish fixture copies before cleanup, isolate test modules, and use the shared LAN HTTP clipboard fallback. |
| `74e1150` | Reject empty, whitespace-only and placeholder organizer configuration before admission. An explicitly empty override cannot fall back to the shared default. Valid Unicode overrides still work. |
| `a1dfbd6` | Capture the first120 decoded Helios frames directly into a private five-second MP4; optional recording service is no longer required. Bounded queue, metadata validation and owned encoder cancellation tested with real FFmpeg. |
| `67bb2b2` | Adopt shared four-digit string codes, atomic reservation and shared join input/validation. Malformed direct joins count toward the rate limit; leading-zero browser and lifecycle checks pass. |

## Implemented behavior

- Exactly three players. Host A writes P0 and remains unscored. B sees only V0 before P1; C sees only V1 before P2. Three fresh FastH3 sessions receive only their current prompt and the fixed rendering instruction; no continuation or image inputs are sent. Everyone sees V2; only B/C submit final guesses.
- Server projections and media GET/HEAD/range requests enforce the same role and phase restrictions. Ordered reveal shows the complete chain, both guesses and local scores. Replay uses saved five-second silent H.264 MP4s. Reset preserves the roster, revokes old media and returns to a new lobby ID.
- Inputs have no countdowns. Normalized immutable submissions use UUID receipts; duplicate retries succeed, conflicting/stale replacements fail. Private input and provider failures do not leak through error messages.
- Failed generation ends unscored. Failed or timed-out scoring reveals the chain without scores/ranking. A retained inference worker prevents overlap or late publication after timeout.
- Attempt consumption is atomic and persistent before any provider request. Nine attempts are allocated explicitly once; reset/restart never refunds them. Unknown closure retains a shared blocker across reset, party close and game switching. Invalid ledger history also blocks live work.

The implemented HTTP contract is in [the game contract](../contracts/reverse-prompt/README.md). Operator commands and private environment settings are in [the runbook](../../../scripts/games/reverse-prompt/README.md).

## Verified on the demo laptop

12 September 2026, macOS Darwin arm64, CPython 3.13.3. Reactor SDK 1.5.1 native library loads; FFmpeg/ffprobe 7.1.1 are installed. Shared dependency lock includes Sentence Transformers 6.0.1, torch 2.14.0, transformers 5.17.0, huggingface-hub 1.31.0, numpy 2.5.3 and HTTPX 0.28.1.

MiniLM revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` is installed with a runtime-checked file checksum manifest at `.local/vibeparty-persistent/models/all-MiniLM-L6-v2`, outside disposable media. The offline check blocks sockets before model import/load/warm-up: exact 100, paraphrase 82, exact ties and token overflow rejection pass. CPU batch shape 3×384, actual limit 256 tokens, warm encoding approximately 9–12 ms, peak process RSS approximately 480 MB during the spike.

Three CUA identities on localhost/127.0.0.1/LAN completed admission, author input, both private relay clues, both final guesses, ordered reveal, saved playback/replay, portal return/Continue and same-roster reset. Desktop and 390×844 layouts were inspected. Backend restart produced the expired-party recovery UI. Copy join link reports success from LAN HTTP with the shared fallback.

Three original geometric fixture clips are bundled: each five seconds, 640×384, H.264/yuv420p, silent and under 24 KiB. Scripted inputs and sample scores 88/46 are enforced only in explicit rehearsal mode. These clips do not count as live generation evidence.

Detailed DEMO-01–08 evidence and remaining gates: [laptop verification](../../research/reverse-prompt/laptop-verification.md).

## Provider findings

The live model is fixed to `reactor/fast-h3`; no model-selector environment variable or new dependency is needed. The adapter confirms autoplay off,1344×768 canvas and end flush on, enqueues one5.167-second prompt, requires matching queued/generated clip identity and124 source frames (preserving compact completion metadata or reading the matching queue item once), then explicitly plays it. Capture begins only on that clip's matching start event and encodes120 frames into five seconds of silent H.264. Idle frames and duplicate starts are ignored; short playback, wrong identities, failed/ambiguous commands and invalid frames fail unscored. A bounded16-frame queue and owned FFmpeg preserve cancellation/backpressure. The unused recording downloader is removed. Detailed contract, evidence and live boundary risks are in [the FastH3 switch record](../../research/reverse-prompt/fasth3-switch.md).

Official SDK commit `9156ce9b09b3ebb8ed717d49d8ac69c5e44cec1d` logs and swallows termination HTTP failures, so successful `disconnect()` is insufficient. The adapter persists the session ID immediately and requires independent GET terminal CLOSED/INACTIVE or 404 before clearing the guard, with a bounded DELETE of that same session when needed. Provider tests prove that ACTIVE after successful SDK disconnect stays blocked. Session A and the other game owners have received this finding.

The first actual FastH3 trial verified one124-frame source to120-frame capture, expected visual content, scoped90-second token configuration and independent terminal closure. Source IDs/timestamps were absent, so the trial does not establish per-frame transport ordering or physical-phone playback. Full live-round and forced-failure evidence remain pending. The adapter has no automatic session retry or fallback to fixtures. Optional recording availability is no longer a gate for the selected route.

## Dependencies and configuration

Resolved through session A: shared package pins/lock, FFmpeg/ffprobe, persistent model/quota settings, preservation of `Cache-Control: private, no-store`, explicit trusted browser aliases, and the local HTTP clipboard helper. No shared dependency change is requested. Session A aligned shared technical/environment/example.env references in `30f4512`, now absorbed. It integrated the complete replacement `9e71dbb` at `9e6d2ba`; the full integrated backend suite passes155 tests, plus Ruff/format and frontend build/lint. This worktree absorbed that integration at `da4977d`. No dependency/configuration request remains open.

Final integration status: A subsequently landed its current tree on local `main` at `25c60bf` and archived its task. The latest Reverse002 evidence (`1a3221a`) and diagnostics (`426c5e4`) are committed here but are not included in that landing. The evidence handoff was delivered; delivery of the diagnostics follow-up was rejected because A's task was archived. No task was reopened and no shared/main files were modified. This was the prior handoff state; the current user-requested landing includes these commits along with session reuse. The FastH3 model switch itself was already integrated.

Shared room-code helpers from `4b4164d` and portal/resolver changes from `35ecb71` are adopted. Reverse Prompt has no roster-clearing in-place party reset: round Reset retains its roster and code, while Close party releases the lookup before new admission. No temporary `activate(code)` or `update_code` compatibility API is used by the game. No integration conflict remains for this migration.

The admission review also moved the active-code/closing check before membership reuse. A current member submitting another valid code now receives404; supplying the correct code resumes without a duplicate player. All27 game/API tests and Ruff/formatting pass after this follow-up.

Private `.env` uses backend 8013/frontend 5176, matching API proxy/browser/public origins, fixture mode and `REVERSE_PROMPT_LIVE_ENABLED=false`. Current LAN public origin is `http://10.0.100.107:5176`. The canonical quota is `/Users/coral/.codex/worktrees/5a4f/VIbeParty/.local/vibeparty-persistent/reverse-prompt/quota.json`, initialized once by A and set as the absolute path in this worktree’s private `.env`. Do not initialize a second file. Reverse001 and002 each consumed one attempt;7 remain, both closed, unresolved=false. Session A may read the pinned model directory from this worktree.

## FastH3 verification checkpoint

The provider fake drives actual FFmpeg through three independent124-frame FastH3 jobs; all three saved outputs are five-second1344×768 MP4s. Decoded opening pixels prove idle black frames were excluded. Queue completion before acknowledgment, duplicate start messages, wrong IDs, ambiguous enqueue, generation rejection, unconfirmed settings, short playback and cancellation pass. Failed output is removed, no retry occurs, and uncertainty after encoding retains the persistent guard. The switch milestone passed71 game/shared tests, Ruff/format, frontend build and ESLint. All14 provider tests pass after the compact-completion follow-up, including its two new metadata-rejection cases.

Browser check on8013/5176 shows MiniMax FastH3 in the host mode selector and lobby explanation. Live admission correctly refuses while disabled; explicit rehearsal opens and closes through the portal. The temporary room was closed. This run adds UI confirmation for the model change; it does not replace the existing three-player rehearsal or physical-phone/live gates.

## First real FastH3 capture

Slot `2026-09-12-reverse-001`, one allowed attempt, completed successfully. Prompt: “A red balloon floats past a blue tower.” Token/session startup7.051s, generated-ready10.460s, total16.490s. Source124 frames; saved120,24fps,5.0s,1344×768, silent H.264/yuv420p,1,953,399 bytes. The adapter independently confirmed terminal state by GET before clearing the guard and returning the file. At the end of slot001 the shared campaign had8 remaining and unresolved=false. Slot002 subsequently consumed one more attempt, as recorded below. A reviewed the canonical ledger and released slot001. Actual spend is unmeasured. Slot001 authorized only that one attempt. Live mode is disabled again after the separate slot002 cleanup.

Safe machine-readable evidence: [Reverse001](../../research/reverse-prompt/evidence/2026-09-12-reverse-001.json). Private preserved video: `.local/reverse-live/2026-09-12-reverse-001/video.mp4`, outside disposable round media. Five sampled frames show a red balloon rising past a blue tower, without a black opening; ffprobe/full decode pass. The model switch now has one real capture result. Physical-phone playback and a full three-prompt live round remain separate checks.

## Live relay failure and cleanup

Slot `2026-09-12-reverse-002` allocated three sequential attempts for a complete live round, with no retries. Host A submitted once; the first generation failed before B received a clue. All three browser identities saw the generic unscored failure. No second or third generation, guess, score or reveal occurred. The canonical ledger independently confirms terminal provider GET closure for both campaign attempts:7 remaining, unresolved=false. The exact failure cause and capture counts are unknown because the running adapter did not persist diagnostics; the private SDK log contained startup information only. No valid002 output was retained.

Host reset returned to the same three-player lobby/code, then Close party retired guest access. The live-enabled process stopped, and normal8013 service restarted with live generation disabled. The first successful001 video remains in private persistent storage. A released002 and cancelled its two unused allocations. Further live-trial coordination is stopped at the user's request; remaining quota is not authorization for another call.

[Sanitized Reverse002 evidence](../../research/reverse-prompt/evidence/2026-09-12-reverse-002.json) records the observed failure and cleanup without session IDs or credentials. This is a naturally failed generation, not a deliberately forced-timeout test.

The diagnostics follow-up persists each attempt's outcome, last phase, available frame/timing evidence and closure state in the existing quota ledger. It retains fixed local failure reasons and exception categories, never SDK/HTTP bodies, prompts or credentials. Existing counters and the unresolved guard are preserved; a diagnostic storage error does not replace the generation error. Provider tests cover success, cancellation, rejection, unknown closure, private SDK exception text and unavailable diagnostic storage. All54 Reverse Prompt tests pass after the follow-up, with Ruff and formatting checks. No paid call exercised this follow-up;002's exact cause cannot be reconstructed.

## Remaining acceptance gates

- A complete live three-video relay through final guesses, local scoring and ordered reveal remains unverified. The first real single clip succeeded; the full-round trial did not.
- Deliberate timeout/provider-cap evidence remains incomplete. Existing automated failure/cancellation/unknown-closure checks pass.
- Physical-phone playback/replay and the three-person event-device rehearsal remain unverified. Three browser identities on one laptop are separate evidence.

DEMO-02/07/08 are not fully passed. DEMO-01/03/04/05/06 retain local browser, HTTP or offline evidence; full-live/device repeats remain incomplete. Do not run further live trials or coordinate new slots while the user's stop remains in force.

FastH3 compact-event follow-up: Word trial001 confirmed generation and terminal closure but exposed absent completion frame counts. Reverse preserves enqueue metadata, accepts whole-number124.0 and reads the existing matching queue item once if needed, with no re-enqueue. Nested/direct clip identities are supported; invalid counts or wrong queue IDs fail. Offline MiniLM was rerun with sockets disabled: `[100,82]`,256 tokens,10.6ms warm batch.
