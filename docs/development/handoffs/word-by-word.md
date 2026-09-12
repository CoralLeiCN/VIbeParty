# Word by Word handoff

Owner: Session B, branch `codex/word-by-word`, worktree `/Users/coral/.codex/worktrees/651c/VIbeParty`.
Foundation: `eb831d80310ae548374143f236c90caf73a90c00`.
Development: API 8011, frontend 5174. Private `.env` defaults to fixture, browser origin `http://localhost:5174`, public/LAN join origin `http://10.0.100.107:5174`, proxy `http://127.0.0.1:8011`. Additional trusted local aliases support independent rehearsal cookies. One backend worker, no reload.

## Status and milestones

The complete fixture loop, guarded live adapter/recovery, and accepted shared four-digit code migration are delivered. **Live acceptance remains blocked**, and the live option is disabled. Actual paid attempts from this worktree: **0**. No fixture or mocked output is recorded as live evidence.

| Milestone | Commit |
| --- | --- |
| Initial laptop SDK/provider research and executable spike | `240bb6db416f2ff7edaa12cae290ac3130b493ef` |
| Complete fixture game: private collection, reveal, replay, rematch | `1151bad4c3a648a2dd64adec1ec0d0fe28fc89a3` |
| Actual LAN HTTP join-link clipboard fallback | `9e6abd2` |
| Guarded live adapter, mock capture/closure checks, complete browser recovery | `ecef2d9` |
| Four-digit codes, leading-zero lifecycle/API/browser acceptance | `3a8752c` |

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

1. Integration has not granted a paid trial slot. The official provider account dashboard requires operator sign-in/readiness confirmation. No session was opened to work around that.
2. Run the required two forest/fox/dance/confetti trials and one group-selected variation on the actual laptop/network. Confirm real wire messages, capture boundaries, additive continuity, elapsed time, independently terminal closure, measured spend, and saved playback after closure.
3. Prove the full cumulative 120-code-point Unicode contribution contract fits FastH3's 1,024-token bound. The implementation does not guess a tokenizer or truncate accepted text. This is a separate live admission gate.
4. Rehearse with 3–4 physical phones on the same LAN. Local browser identities and responsive frames are documented separately.
5. Resolved in integration `1270f0b`: shared example environment now exposes the game-local disabled defaults `WORD_BY_WORD_LIVE_ENABLED`, `WORD_BY_WORD_CAPTURE_VERIFIED`, `WORD_BY_WORD_PROMPT_LIMIT_VERIFIED`, `WORD_BY_WORD_LIVE_SLOT`, and `WORD_BY_WORD_PREVIOUS_SESSION_CLOSED`. These are read from private `.env` by the game; exact semantics are in the script README. Do not enable them without recorded evidence and the coordinator's allocation.

Resolved requests: pinned Reactor SDK 1.5.1 and HTTPX in shared dependency setup; FFmpeg/ffprobe 7.1.1 installed; explicit trusted browser origins and HTTP clipboard helper published by integration; independent owned-session closure endpoint/schema verified from the primary native SDK source.
