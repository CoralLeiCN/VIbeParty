# Prompt Royale handoff

Branch: `codex/prompt-royale`. Worktree: `/Users/coral/.codex/worktrees/caba/VIbeParty`.
Backend 8012, frontend 5175; API proxy http://127.0.0.1:8012. Browser origin localhost:5175,
public invite origin http://10.0.100.107:5175. Default fixture video and fixture topics.

## Commits and readiness

- Foundation: `eb831d80310ae548374143f236c90caf73a90c00`.
- Shared dependency milestone: `a75766fe66d21fd860cb8c54f26cb3ba1a7f1891`.
- Offline tokenizer/spike evidence: `6e175c0`.
- Shared portal/polling, all other fixture games and LAN clipboard helper merged through
  `35ecb71`, preserving ancestry (local merge `13d87ce`).
- Full Prompt Royale fixture/provider milestone: `5607c23`, merged by integration at `6fb7767`.
- Host authentication/presence review fix and test packaging: `f8b3173`.
- Initial fixture handoff bookkeeping: `1e4dfe6`.
- Shared room-code specification: `7e6b2b4`; helpers `4b4164d`, portal/resolver `35ecb71`.
- Prompt Royale four-digit room-code migration and browser evidence: `e9c3c21`.

Fixture gameplay is available. Live is disabled by default and rehearsed capacity is zero.
All supplied implementation lives in the assigned game/backend/test/script/research paths.
Shared manifests, lockfiles, configuration and portal changes come from integration merges.

## Implemented

Playing host and 3–4 total players; normalized/suffixed names, opaque HttpOnly membership;
bundled topics and separately configured LLM suggestions with exact-ID confirmation,
regeneration and stale-completion protection; immutable private prompts; full UMT5 token
validation; bounded generation and one recovery pass; stable anonymous 2×2 arena;
coordinated playback/repeat/pause/retry; exclusions; ten-second ballots; no self-voting;
positive-score ties, abstention and no-winner results; refresh, play again and guarded close.

Server deadlines, host absence and expiry run independently of browser requests. Media/range
authorization follows phase and eligibility. Individual ballots remain private. Counters
survive replay/close. Late files are discarded; failed media cleanup blocks party release.

Live code uses scoped one-session/60s Helios tokens, two entry slots, 6s start pacing,
received-media timestamps, bounded HTTPX recording download, deterministic first-five-second
H.264 preparation, byte caps, saved-source/download recovery and independent terminal-state
checks. A persistent unresolved-session marker blocks admission after a crash; no paid replay.

Topic choice: OpenAI gpt-4.1-mini-2025-04-14 via HTTPX, 10s total timeout, max_output_tokens64,
160 accepted topic code points, no automatic retries, separate 16-call maximum, store:false.
Credentials and player input never enter the frontend or topic request.

## Verification

- 61 focused game/shared tests passed after room-code migration, 25.18s. Existing
  Starlette/TestClient deprecation warnings.
- Before the room-code migration, complete backend collection succeeded and all 87 backend
  tests passed in 29.53s after merging integration fixes. Test packages prevent same-name modules in different games colliding.
- Review regressions cover non-ASCII incorrect host codes (403), malformed Unicode (422),
  missing/placeholder host configuration (503), and accepted duplicate commands refreshing
  host presence while rejected commands leave it unchanged.
- Ruff and git diff --check pass; TypeScript, production build and ESLint pass.
- One Playwright scenario passed full three- and four-player rounds, both topic modes,
  generation/confirmation reset, draft refresh, private stable arena, concurrent looping,
  Pause all/Replay all, vote/results, exclusion, Play again and End room.
- Actual laptop LAN HTTP origin run passed in 29.7s, including Copy link, failed-video retry,
  and blocked-playback recovery. Separate contexts include 1280×900 and 390×844 viewports.
- Integration reports its combined LAN browser scenario passed all three games in 21s,
  including Prompt Royale with a playing host and three guests, playable four-tile arena,
  refresh/continuation, voting and cleanup before switching with fresh rosters.
- Shared four-digit-code migration: controlled `0042` LAN full-round rehearsal passed in
  30.1s; direct-form correction and code-only links passed in 1.4s. API checks reject invalid
  and non-string codes, count malformed attempts toward throttling, preserve zeros and
  membership on resume, retire codes on close/expiry, and prevent old-session restoration
  when a retired code is reused. Normal secure random generation was restored after rehearsal.
- Native reactor-sdk1.5.1 initialization and tokenizers0.23.2 validated on Python3.13.3/macOS arm64.
  Exact pinned tokenizer SHA checked; full-input >500-token rejection demonstrated.
- FFmpeg/ffprobe7.1.1 generate and validate all four original labelled fixture clips.

Commands and launch settings: [runbook](../../../scripts/games/prompt-royale/README.md).
API/snapshot details: [contract](../contracts/prompt-royale/README.md).
Screenshots and browser evidence: [rehearsal](../../research/prompt-royale/fixture-rehearsal.md).
Provider/tokenizer details: [laptop spike](../../research/prompt-royale/laptop-spike.md).

## Live gates / pending user or integration work

**No paid calls made, no provider sessions created, no exclusive slot granted.** Integration
is waiting for operator balance/quota/prior-session closure confirmation. OPENAI_API_KEY was
missing; the user was asked to configure it securely. Fixture tests do not pass the live gate.

Remaining: run the allocated capture and topic spikes; verify actual timing, media and closure;
rehearse three then four live players with measured deadline/cost; verify physical phone Safari,
Chrome and projected playback. A 390px Chromium context is not a physical phone check.

The standalone spike scripts are ready and require an allocation argument. They exit nonzero
on failed gates, write concise evidence, and never print keys, JWTs or private prompts.
Do not increase live capacity or remove an unresolved marker without operator evidence.

## Dependency and configuration requests

Resolved by integration: reactor-sdk/tokenizers/HTTPX pins, FFmpeg, Playwright, configurable
8012/5175 proxy/origins, polling preservation/hidden-tab pause, and HTTP clipboard fallback.
`prepare_tokenizer.py` now honors --destination and process/root .env PROMPT_ROYALE_TOKENIZER,
resolves relative paths against the checkout, and checksum-validates existing files.
Integration may wire it into shared setup. No outstanding package dependency request.

## Room-code adoption

Uses the shared atomic reservation, backend normalizer and frontend input. All codes are
four-digit strings. Play again, refresh and continuation retain the roster and code. End
room/expiry remove lookup and sessions after cleanup. There is no separate roster-clearing
reset in Prompt Royale; creating the next party allocates a code under shared admission.
No compatibility activation override remains. The portal specification merge conflict was
resolved using the integration owner's published version; no integration conflict remains.
Integration owns full-suite/cross-game acceptance after all owners migrate.
