# Word by Word handoff

Owner: Session B, branch `codex/word-by-word`, worktree `/Users/coral/.codex/worktrees/651c/VIbeParty`.
Foundation: `eb831d80310ae548374143f236c90caf73a90c00`.
Development: API 8011, frontend 5174. Private `.env` defaults to fixture, browser origin `http://localhost:5174`, public/LAN join origin `http://10.0.100.107:5174`, proxy `http://127.0.0.1:8011`. Additional trusted local aliases support independent rehearsal cookies. One backend worker, no reload.

Current operator instruction: stop cross-task coordination of live trials. The allocation messages below are historical; do not request further slots from another task. No further trial has been run, and all three sessions are closed.

## Status and milestones

The complete fixture loop, guarded live adapter/recovery, and accepted shared four-digit code migration are delivered. **Live acceptance remains incomplete**, and the live option is disabled. Actual provider session attempts from this worktree: **3**, all independently confirmed closed. The key and first generation work; the latest trial delivered 156 of 158 advertised frames and timed out at the 30-second step deadline. This batch's allowance is exhausted. No fixture or mocked output is recorded as live evidence.

| Milestone | Commit |
| --- | --- |
| Initial laptop SDK/provider research and executable spike | `240bb6db416f2ff7edaa12cae290ac3130b493ef` |
| Complete fixture game: private collection, reveal, replay, rematch | `1151bad4c3a648a2dd64adec1ec0d0fe28fc89a3` |
| Actual LAN HTTP join-link clipboard fallback | `9e6abd2` |
| Guarded live adapter, mock capture/closure checks, complete browser recovery | `ecef2d9` |
| Four-digit codes, leading-zero lifecycle/API/browser acceptance | `3a8752c` |
| Safe diagnostics for real generation trials; no paid attempts | `217eddf` |
| First real-trial frame metadata fix; 40 Word checks pass | `2fbd4a9` |
| Absent SDK frame identifiers handled explicitly; 42 Word checks pass | `853fe02` |

Merged shared integration normally through `1270f0b`. No shared manifest/config files edited by this session. Integration already merged the fixture/clipboard milestones. Word availability means the fixture loop is playable; it does not claim live acceptance.

## Delivered behavior

Separate host display, 3–4 player roster, deterministic four assignments, exact trimmed Unicode input and immutable accepted text, 45-second private collection, one retained generation task, progress, protected manual reveal, valid saved prefixes, End round, saved replay, and same-roster rematches. Ownership, stale-round and duplicate-action protection, host-only/range-capable disclosed media, inaccessible future text/media, 30-minute inactivity, three live attempts per process, 120-second overall/30-second step deadlines, one scoped 180-second provider session, and confirmed-cleanup admission guards are covered.

The live adapter creates a single scoped token, requests and captures each additive segment before the next, rejects ambiguous enqueue without retry, bounds raw-frame buffering/encoding, and independently checks the owned session's terminal state. Unknown identity, nonterminal states, closure errors, and cancellation preserve the guard. Safe evidence stays private under the game's `live-evidence/` directory. The paid spike reuses the same adapter.

## Verification

- `pytest backend/tests/word_by_word backend/tests/shared -q`: **59 passed** (38 Word + 21 shared). Fourteen Word checks use mock SDK/HTTP and synthetic frames. Two upstream TestClient deprecation warnings remain; no failed checks.
- Scoped Ruff: pass. TypeScript/Vite build: pass. Frontend ESLint: pass.
- Original fixture assets: four deterministic six-second 640×360 H.264/yuv420p clips, no audio, fast start, decoded/probed locally.
- CUA: actual host plus three, then four independently cookie-scoped browser player identities. Private assignments/submissions, accepted refresh, hidden pre-Play reveal, same-roster rematch, four-player assignment, saved playback, End, and LAN clipboard verified.
- Explicit internal fake with real UI/rules: 121-point correctable input, exact 120-point Unicode text, Japanese/emoji, actual input timeout, two-clip partial reveal, saved replay during unresolved cleanup, blocked rematch/reset, and successful Retry cleanup. Full text wraps in a measured 390-pixel iframe with no horizontal overflow. CUA's requested viewport override did not resize the browser; this limitation is recorded.
- Integration's separate `frontend/tests/combined.spec.ts` uses actual 390×844 browser contexts and a 1360×1000 host for Word/portal continuation and the connected three-game sequence. Source/evidence is at the merged integration commit; this session did not rerun that broader matrix.

Details: [fixture/browser evidence](../../research/word-by-word/fixture-rehearsal-2026-09-12.md), [provider gate and live record](../../research/word-by-word/laptop-gate-2026-09-12.md), [API contract](../contracts/word-by-word/README.md), [commands and live gates](../../../scripts/games/word-by-word/README.md).

## Four-digit code follow-up

Read and adopted the full accepted standard from `7e6b2b4`. Word uses shared atomic reservation/rotation, strict normalization after direct-join throttling, and shared entry UI. `0042` survives display, copied links, whitespace-trimmed joining, refresh and rematch. Invalid/non-string/non-ASCII formats are rejected with exact copy; reset collision retries and retires the old code. CUA confirmed the controlled `0042` flow and roster reset to `4960`. Historical five-character fixture evidence is superseded for code format. No shared-file conflicts; integration owns the final portal/code-only-link sequence.

## Blockers and integration requests

1. Dashboard prechecks were waived by the user's explicit direction to use the existing key. Integration allocated `2026-09-12-word-001`, `002`, and `003`; all three ran and their owned sessions independently returned HTTP 200 / `CLOSED`. This batch is exhausted. No fourth attempt is authorized.
2. Run the required two forest/fox/dance/confetti trials and one group-selected variation on the actual laptop/network. Confirm real wire messages, capture boundaries, additive continuity, elapsed time, independently terminal closure, measured spend, and saved playback after closure.
3. Prove the full cumulative 120-code-point Unicode contribution contract fits FastH3's 1,024-token bound. The implementation does not guess a tokenizer or truncate accepted text. This is a separate live admission gate.
4. Rehearse with 3–4 physical phones on the same LAN. Local browser identities and responsive frames are documented separately.
5. Resolved in integration `1270f0b`: shared example environment now exposes the game-local disabled defaults `WORD_BY_WORD_LIVE_ENABLED`, `WORD_BY_WORD_CAPTURE_VERIFIED`, `WORD_BY_WORD_PROMPT_LIMIT_VERIFIED`, `WORD_BY_WORD_LIVE_SLOT`, and `WORD_BY_WORD_PREVIOUS_SESSION_CLOSED`. These are read from private `.env` by the game; exact semantics are in the script README. Do not enable them without recorded evidence and the coordinator's allocation.

Resolved requests: pinned Reactor SDK 1.5.1 and HTTPX in shared dependency setup; FFmpeg/ffprobe 7.1.1 installed; explicit trusted browser origins and HTTP clipboard helper published by integration; independent owned-session closure endpoint/schema verified from the primary native SDK source.

## Real-trial request follow-up

The user explicitly requested actual generation trials. Integration reconfirmed that the first bounded slot is requested but ungranted, pending credits and prior-session closure. Fresh browser verification still reaches Reactor sign-in; the operator has been asked to sign in and supply those readiness facts. Actual session attempts remain **0**; fixture defaults and every live admission gate remain unchanged.

Prepared safe trial diagnostics in `live.py` and `spike.py`: stage, per-step prompt size and timing, incomplete frame capture, event/frame timing, queue peak, frame-ID gaps, independent closure status and cleanup duration. Focused `test_live.py`: **14 passed**; scoped Ruff and format check: pass. This is preparation, not actual provider evidence. No shared dependency/configuration request is needed. Integration published final shared acceptance at `4d973a8ecf68a3144b5f1888e064e21596f68ab0`; this follow-up does not change shared files.

### Actual first trial and correction

The subsequent user direction superseded the dashboard prerequisite. Trial `2026-09-12-word-001` authenticated successfully, acknowledged the first prompt, and received generation completion in 4.522 seconds. Capture stopped before playback with `missing_clip_frame_count`; zero clips saved. Total 14.066 seconds; cleanup 1.137 seconds; independent owned-session GET returned HTTP 200 / `CLOSED`. Actual spend is unmeasured. See the [actual evidence and limitations](../../research/word-by-word/laptop-gate-2026-09-12.md#actual-trial-2026-09-12-word-001).

Correction `2fbd4a9` preserves enqueue frame metadata across compact completion events, handles integral JSON floats, and reads existing queue metadata if needed without re-enqueueing. It also adopts the newer documented 800-character cap; maximum accepted cumulative text plus instructions is 732 code points. Unicode token fit remains unverified. **40 Word tests pass**, scoped Ruff/format pass. A second one-session allocation is requested; no new shared dependencies or configuration needed.

### Actual second trial and correction

Allocated `2026-09-12-word-002` parsed 158-frame clip metadata and reached raw playback, then stopped because absent SDK metadata appears as repeated zero IDs/timestamps. No clip saved. Total 12.728 seconds, cleanup 0.519 seconds; independent owned-session GET HTTP 200 / `CLOSED`. [Actual evidence](../../research/word-by-word/evidence/2026-09-12-word-002.json). Native SDK source and Reverse's existing finding confirm the absent-metadata sentinel. Correction `853fe02` accepts delivery order in that case, reports missing metadata honestly, and keeps meaningful duplicate-ID rejection and all other capture bounds. **42 Word checks pass**, scoped Ruff/format pass. A third exclusive attempt is requested; no fourth attempt authorized, no dependency/configuration change needed.

### Actual final batch trial — current blocker

Allocated `2026-09-12-word-003` generated the first clip in 4.387 seconds. The provider advertised 158 frames; capture received 156 without source identifiers/timestamps. Local queue peak was only 2 of 8. The matching finish event arrived, with the last frame 0.109 seconds later; the 30.004-second step timeout correctly rejected the incomplete capture. Total 38.415 seconds; cleanup 0.862 seconds; independent GET HTTP 200 / `CLOSED`. No saved clips or temporary partial remain. [Actual evidence](../../research/word-by-word/evidence/2026-09-12-word-003.json).

Current work: locate the two-frame shortfall or use a reliable provider export before another allocated batch. Do not weaken completeness checks to pass the gate. Full continuity, exact capture boundaries, full Unicode token fit and saved live replay are still unverified; actual account spend is unknown. All three owned sessions closed, 3/3 attempts consumed, no fourth requested. Production live flags stay disabled, fixture remains the default. Latest implementation checks remain **42 Word tests, Ruff and format passing**. No new shared dependency/configuration request yet; keep the coordinator informed if export requires one.

## Main landing verification

Refreshed `main` at `17da453ef15c6ee36157ccb2a71ff603876d3119` and merged it into the Word branch before landing. Resolved the earlier squash history's add/add conflicts by preserving current main shared/game files and the committed Word updates. Main's newer category scenarios remain intact. The complete remaining difference is ten Word-owned files.

Repository lint, Ruff formatting, TypeScript/Vite build and frontend ESLint pass. The combined backend suite initially lacked Prompt Royale's pinned tokenizer in this worktree; installed it with the repository's checksum-verified setup script, then **143 backend tests passed** (two upstream deprecation warnings). No further provider calls or cross-task live coordination were performed during landing.
