# Exclusive live-provider trial slots

Coordinator: Session A, codex/app-integration. Credentials remain in private .env; do not put values here.

## Active allocation

17 September 2026: the user's request to run an online test and then publish/merge on success authorizes `2026-09-17-host-recovery-001`: one LingBot World 2 session for PORTAL-001 with WW-CAT-01 inputs and the existing Place-only forest seed. No generation retry. Test host recovery during streaming, completion/replay, and close/switch to Prompt Royale. Confirm this session's terminal provider state before release. Earlier completed LingBot runs are recorded in [the 16 September verification](../research/word-by-word/2026-09-16-lingbot-continuous-flow.md). This allocation supersedes the historical stop below for this single test only. Status: complete and released. One session consumed; generation completed with all four steps, host access recovered during STREAMING, one 25.125-second replay saved, and provider closure independently confirmed at 20:00:58 UTC. Close/switch and Prompt Royale creation passed. No generation retry; actual spend was not measured. [Verification record](../research/word-by-word/2026-09-17-host-recovery.md#online-verification).

### Historical allocations (12 September)

Live-trial coordination and monitoring of other tasks are stopped at the user's instruction. No further paid sessions are authorized. Reverse slot 002 consumed only its first attempted generation, which failed in the browser; the remaining two allocations are cancelled. The canonical quota records two closed Reverse attempts, seven remaining and no unresolved session. A detailed owner report for slot 002 is not integrated in this checkpoint; this task is no longer waiting for it. All Word slots and Reverse slots 001/002 are closed.

All three Word slots are closed and released; that batch is exhausted at 3/3 attempts. The user directed use of the existing API key and real verification without dashboard prechecks. The key worked in all three Word attempts; account balance and account-wide prior-session status remain unverified. Each trial's own session was independently confirmed closed.

The coordinator initialized Reverse's single nine-attempt campaign at `/Users/coral/.codex/worktrees/5a4f/VIbeParty/.local/vibeparty-persistent/reverse-prompt/quota.json`. It began with nine remaining and no unresolved session; after its second trial it has seven remaining, two closed attempts and no unresolved session. Every Reverse worktree/trial must use that exact file through `REVERSE_PROMPT_QUOTA_FILE`; never initialize a second file or replenish it. Two of the nine attempts are consumed. The remaining seven are preserved and unallocated; initialization or restart cannot replenish the campaign.

- Allowance for each completed Word slot: exactly one FastH3 session creation attempt, with no paid retry.
- Word limits: 180-second provider lifetime, 120-second overall application deadline, 30 seconds per step; four sequential additive clips.
- Record actual attempt count, timing, saved clips or failed gate, and spend if available. Do not represent unavailable billing data as zero cost.
- Independently confirm terminal state/404 for the session this trial creates. Disconnect alone is insufficient. Hold this slot, and block every other worktree, until closure is confirmed; an elapsed deadline does not transfer the slot automatically.
- Completed: three Word session attempts today, all independently closed; zero valid saved clips. Reverse's completed allocations and the user stop are recorded above.

## Completed allocations

`2026-09-12-word-001`: granted at 14:25 UTC; run started at 14:26:52 UTC. Consumed 1/1 attempt. Token request returned HTTP 200; startup took 8.407 seconds, first enqueue acknowledgment 0.212 seconds and first generation 4.522 seconds. Local capture failed with `missing_clip_frame_count` before playback; zero clips saved. Total elapsed 14.066 seconds, including 1.137 seconds of cleanup. Independent session GET returned HTTP 200 with state `CLOSED`; coordinator reviewed the private evidence JSON. Slot released at 14:29 UTC. Actual spend is unmeasured. The next slot follows a committed metadata correction and focused regression checks; the first slot made no automatic retry.

`2026-09-12-word-002`: granted at 14:29 UTC after the metadata correction and 40 passing Word tests. Consumed 1/1 attempt. Startup took 5.985 seconds; first enqueue acknowledgment 0.018 seconds and generation 5.958 seconds. Parsed 158 source frames, but capture rejected the SDK's repeated zero frame IDs as `non_monotonic_frame_ids` after receiving one frame; zero clips saved. Total elapsed 12.728 seconds, including 0.519 seconds of cleanup. Independent GET returned HTTP 200 with state `CLOSED`; coordinator reviewed the private evidence JSON and released the slot. Actual spend is unmeasured. The game owner is correcting the treatment of zero IDs/timestamps as absent metadata, a behavior already established in Reverse Prompt's SDK checks.

`2026-09-12-word-003`: granted at 14:33 UTC after correction `853fe02` and 42 passing Word tests. Consumed 1/1 attempt, the final allocation in this batch. Startup took 7.549 seconds; enqueue acknowledgment 0.186 seconds and generation 4.387 seconds. The provider advertised 158 frames; capture received 156, all without optional frame metadata. Queue peak was two, with no overflow. The matching finish event arrived 6.504 seconds after start, and the final received frame arrived 0.109 seconds after that event. The incomplete capture reached the 30.004-second step deadline; no valid MP4 was saved. Total elapsed 38.415 seconds, including 0.862 seconds of cleanup. Independent GET returned HTTP 200 with state `CLOSED`; coordinator reviewed the private evidence JSON and released the slot. Actual spend is unmeasured. Word live mode remains disabled pending a verified capture/export approach; no fourth attempt is allocated.

`2026-09-12-reverse-001`: granted at 14:38 UTC with one attempt, a 90-second provider cap and 90-second application deadline. Successful real capture: 124 declared source frames, first 120 matching playback frames encoded as a five-second, 24 fps, silent H.264 MP4 at 1344×768; 1,953,399 bytes. Startup took 7.051 seconds, generation ready at 10.460 seconds, total 16.490 seconds. Optional frame IDs/timestamps were absent. The game independently confirmed terminal state by GET; coordinator reviewed sanitized evidence and the canonical quota record: latest attempt closed, unresolved false, eight remaining. Slot released; no retry or second attempt. Actual spend is unmeasured. This passes one independent capture, not the full relay/device acceptance.

| Owner | Requested first allocation | State | Transfer requirement |
| --- | --- | --- | --- |
| Word by Word | Three separately allocated FastH3 attempts | Batch complete; capture gate failed; no active slot | New capture evidence and separately allocated future work |
| Prompt Royale | 1 Helios session, <=60s lifetime, >=6s source / 5s output | Queued; no allocation | attempt count + saved playable source + terminal provider state |
| Reverse Prompt | Nine-attempt campaign; two consumed, seven remain | Coordination stopped; no live allocation | persistent ledger preserved + terminal provider state; uncertainty blocks every worktree |

SDK 1.5.1 native import verified by all owners on Darwin arm64/Python3.13. SDK disconnect can swallow termination errors: disconnect alone is not proof; verify coordinator session terminal state/404. No transfer until closure confirmed. Fixture work can proceed with explicit failed live gate if external readiness blocks the spike. Game owners report attempts, closure, evidence, dependency changes and committed SHAs in their handoffs.

FFmpeg/ffprobe 7.1.1 installed and verified by A.

Historical readiness attempt, before this allocation on 12 September: billing documentation and the available signed-out dashboard did not establish account balance or account-wide session state. No paid slot or persistent campaign allocation had been issued. The user's subsequent direction supersedes that precheck for `2026-09-12-word-001`; closure verification for the trial's own session remains required.
