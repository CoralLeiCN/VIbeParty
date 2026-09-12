# Reverse Prompt handoff

Owner: session D. Branch `codex/reverse-prompt`. Backend 8013; frontend 5176.

## Current checkpoint

The backend, frontend, independent Helios adapter, pinned local scorer, scripted rehearsal, fixtures and operator scripts are implemented. The full three-player scripted flow has passed browser verification. Game availability is enabled for the labelled rehearsal. Live acceptance is blocked by operator account/session readiness and the exclusive trial allocation pending in session A. No paid call or real campaign initialization has run in this worktree.

The implementation starts from published foundation `eb831d80310ae548374143f236c90caf73a90c00` and includes shared integration through `35ecb7154540f8da37fa1add8f68d0e56cadcbfa`. Four-digit room codes are adopted from the accepted shared standard. All 61 Reverse Prompt and shared tests pass (40 Reverse Prompt), with Ruff, formatting, frontend build and lint. Browser checks cover the controlled leading-zero code `0042`, all admission paths and reset/close. Actual FFmpeg encoding/decoding/cancellation and the socket-disabled real MiniLM scorer remain verified.

## Milestone commits

| Commit | Reviewable result |
| --- | --- |
| `cecbf53` | Backend state/actions, role privacy and range authorization, guarded Helios adapter, persistent quota, pinned scorer, operator scripts and fixtures. Integrated by A at `62b0874`. |
| `65322cc` | Complete frontend, scripted relay/reveal/reset, browser recovery and retained inference ownership. Integrated by A at `faa6b16ac93ae558cd025b9dbd754fcda783a390`. |
| `d29501d` | Validate complete quota history, enforce fifteen-second source cap, finish fixture copies before cleanup, isolate test modules, and use the shared LAN HTTP clipboard fallback. |
| `74e1150` | Reject empty, whitespace-only and placeholder organizer configuration before admission. An explicitly empty override cannot fall back to the shared default. Valid Unicode overrides still work. |
| `a1dfbd6` | Capture the first120 decoded Helios frames directly into a private five-second MP4; optional recording service is no longer required. Bounded queue, metadata validation and owned encoder cancellation tested with real FFmpeg. |
| `67bb2b2` | Adopt shared four-digit string codes, atomic reservation and shared join input/validation. Malformed direct joins count toward the rate limit; leading-zero browser and lifecycle checks pass. |

## Implemented behavior

- Exactly three players. Host A writes P0 and remains unscored. B sees only V0 before P1; C sees only V1 before P2. Three fresh Helios sessions receive only their current prompt. Everyone sees V2; only B/C submit final guesses.
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

The selected route now uses `main_video.on_raw_frame` to encode the first120 decoded frames directly into five seconds at24fps, under the user's frame-assembly request. It needs no browser screenshots or optional recording API. The callback hands immutable BGRA bytes to a bounded16-frame queue; FFmpeg remains owned through cancellation. Invalid frames/timestamps or queue overflow fail unscored. SDK zero ID/timestamp means absent metadata and must not be counted as one repeated frame. Output is validated and remains private. The earlier bounded recording-download helper is retained but is not called in live generation.

Official SDK commit `9156ce9b09b3ebb8ed717d49d8ac69c5e44cec1d` logs and swallows termination HTTP failures, so successful `disconnect()` is insufficient. The adapter persists the session ID immediately and requires independent GET terminal CLOSED/INACTIVE or 404 before clearing the guard, with a bounded DELETE of that same session when needed. Provider tests prove that ACTIVE after successful SDK disconnect stays blocked. Session A and the other game owners have received this finding.

Actual Helios frame timing, visual quality, model/session cap and terminal confirmation remain unverified live. The adapter has no automatic session retry or fallback to fixtures. Optional recording availability is no longer a gate for the selected route.

## Dependencies and configuration

Resolved through session A: shared package pins/lock, FFmpeg/ffprobe, persistent model/quota settings, preservation of `Cache-Control: private, no-store`, explicit trusted browser aliases, and the local HTTP clipboard helper. No outstanding shared dependency change is requested.

Shared room-code helpers from `4b4164d` and portal/resolver changes from `35ecb71` are adopted. Reverse Prompt has no roster-clearing in-place party reset: round Reset retains its roster and code, while Close party releases the lookup before new admission. No temporary `activate(code)` or `update_code` compatibility API is used by the game. No integration conflict remains for this migration.

The admission review also moved the active-code/closing check before membership reuse. A current member submitting another valid code now receives404; supplying the correct code resumes without a duplicate player. All27 game/API tests and Ruff/formatting pass after this follow-up.

Private `.env` uses backend 8013/frontend 5176, matching API proxy/browser/public origins, fixture mode and `REVERSE_PROMPT_LIVE_ENABLED=false`. Current LAN public origin is `http://10.0.100.107:5176`. The configured quota path is `.local/vibeparty-persistent/reverse-prompt/quota.json`; it is deliberately absent until session A allocates the campaign. Session A may read the pinned model directory from this worktree.

## Remaining gates and next coordinated trials

1. Session A resolves the existing operator-readiness question: account balance/quota and previous sessions confirmed closed, then names the persistent campaign location and exclusive slot. Integration attempted a read-only dashboard check but it redirects to sign-in; the user has been asked for the missing facts. No verified account-balance/session-list API is available. Do not initialize another campaign to obtain more attempts.
2. Run one independent capture with `.venv/bin/python scripts/games/reverse-prompt/spike.py --slot <coordinator-reference>`. Enable live only for the allocated slot. Record duration, dimensions, bytes, frame count, remaining attempts and independently confirmed closure. This is the uncompleted initial live gate; implementation proceeded in fixture mode while it was blocked.
3. Coordinate a separate three-attempt full live relay and a one-attempt forced-failure trial (`--force-timeout`) with A. Validate private live media, real local scores, unscored failure and closure/cap behavior. A proposed allocation of 1+3+1 has been requested but not granted.
4. Run the three-person event-device rehearsal and physical-phone playback/replay. Three browser identities on one laptop are not physical-device evidence.

DEMO-02/07/08 cannot be marked fully passed before those trials. DEMO-01/03/04/05/06 have local browser, HTTP or offline evidence with live/event-device repeats recorded as pending. The unresolved-session guard must stay active whenever closure cannot be proved, including after process restart.
