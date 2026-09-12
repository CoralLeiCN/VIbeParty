# One FastH3 session per Reverse Prompt round

User-directed change,12 September2026: keep the session connected while players think, limiting B/C relay turns to30 seconds. This supersedes the earlier fresh-session-per-video and no-input-countdown decisions for Reverse Prompt. No additional live call was made for this change.

## Provider basis

The [FastH3 API](https://www.reactor.inc/models/fast-h3/api) documents multiple queued clips in one session. Clips are independent unless `continue_from_clip_id` explicitly supplies continuity; `starting_frame` is also optional. We omit both inputs and enqueue only the current player's text plus the fixed rendering instruction. A clip's identity determines playback and frame capture. The [billing documentation](https://docs.reactor.inc/resources/billing) says ready sessions remain billable while idle. The user accepted keeping the session open during bounded thinking turns to avoid reconnecting between clips.

## Implemented behavior

- Open one model-scoped creator session when A submits. Confirm autoplay off, landscape canvas and end flush once. Each accepted prompt consumes a separate persistent attempt before its enqueue; no automatic retries.
- Retain the session after V0 and V1 are captured and validated. B and C each have30 seconds to watch their private clue and explicitly submit their description. The deadline belongs to the server and survives refresh; the UI displays remaining seconds. No automatic draft submission occurs. Expiry stops unscored and closes the session.
- Capture and validate three separate five-second1344×768 MP4s. Stop each playback when the120-frame capture is complete. Retire its ID so late boundary/failure events cannot corrupt the next clip; idle frames are excluded. Fresh capture and correlation state are used for each enqueue, without reconnecting.
- Close and independently verify terminal state after V2 is saved, before guessing. A's original input and B/C's final guesses remain untimed; no GPU is held during final guesses, local scoring or replay. Error, reset, party closure and shutdown also own session cleanup.
- Keep90 seconds per generation. The retained session gets a360-second provider cap and a345-second application watchdog, covering three generation windows and two thinking turns with bounded cleanup before the provider cap.
- Preserve existing quota history without replenishment. An optional `session_attempt` groups up to three consecutive attempts under one session. All remain unresolved until terminal verification closes the whole group atomically. An unrelated/new process cannot consume another session while the group is open. Invalid group histories and changed session IDs fail closed. Diagnostic evidence stays private and excludes player inputs and credentials.

## Local evidence

The provider fake drives real FFmpeg through three independent clips in one token/session, using full, compact and queue-resolved metadata. Settings occur once. Each current-only prompt enqueues once; matching playback yields120 valid frames. Earlier clip events injected during a later enqueue are ignored. The session remains open between clips and the quota falls9→8→7→6, then all three attempt records close after the terminal GET. A later round opens a new session. A second-clip failure closes the same session and spends only two attempts.

HTTP tests retain exactly-three admission, host exclusion, snapshot/media/range privacy, immutable duplicate receipts, stale actions, ordered reveal, replay and reset. New checks cover timer refresh, late input before the timer callback, expiry and media revocation, reset during thinking, idle provider failure, final-video closure failure and the whole-round cap. Legacy and grouped quota records are checked across new `Quota` instances; partial closure is rejected.

Browser rehearsal on8013/5176 used A on localhost, B on the LAN origin and C on127.0.0.1. B's countdown showed25 seconds and21 after refresh, proving no reset. C's turn expired during one inspection, producing the unscored error. Confirmed reset preserved all three roles/code. A subsequent full timed rehearsal reached B's private clue, C's new30-second turn, untimed final guesses and ordered reveal with labelled88/46 sample scores. These are fixture flow checks, not new live generation evidence.

Final full backend run:166 passed after supplying the existing checksum-pinned Prompt Royale tokenizer through `PROMPT_ROYALE_TOKENIZER=/private/tmp/reverse-tests/umt5-tokenizer.json`. The initial22 failures were missing-tokenizer setup failures in that other game. Frontend build/lint and game Ruff checks pass. The final run includes second-clip failure, fresh next-round session ownership, and termination despite a session-identity storage failure. All63 Reverse Prompt tests pass; the remaining103 cover the shared application and other games.

## Remaining gates and configuration

The earlier successful Reverse001 video and failed Reverse002 trial used separate sessions. Live retained-session performance and real provider stop/late-event ordering remain unverified, as does physical-phone acceptance. Further live-trial coordination remains stopped.

The canonical campaign file was under `/Users/coral/.codex/worktrees/5a4f/VIbeParty/.local/vibeparty-persistent/reverse-prompt/quota.json`. That integration worktree has now been removed; the file is no longer present. Last verified state was seven remaining, two closed attempts, no unresolved session. No replacement ledger was initialized. Live admission remains disabled and cannot proceed with a missing campaign; restore the original record to a durable location before enabling it. MiniLM and the saved Reverse001 video remain in this worktree's persistent local directory.

No package, shared code or environment schema change is needed. During the user-requested main landing, shared `docs/games/reverse-prompt/{game-spec,tech-stack}.md`, the parallel plan and checklist were synchronized with this user-directed change. The game-owned API contract and this record describe the same implemented behavior.
