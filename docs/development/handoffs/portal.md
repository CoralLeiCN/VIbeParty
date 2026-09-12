# Portal and shared application handoff

Owner: A — `codex/app-integration`. Verified 12 September 2026 on the host Mac, Python3.13/Darwin arm64. The portal and all three complete fixture games run together over local HTTP. Live-provider acceptance and physical-phone rehearsal remain open.

## Delivered

React19/TypeScript/Vite frontend, FastAPI backend, locked Python/npm dependencies, local setup/dev/demo commands, explicit game registration and private per-game media. Shared contracts cover scoped cookies, session discovery without presence updates, room-code resolution, one-party admission, cleanup before release, errors, exact allowed origins, and polling with cancellation/timeouts/reconnect.

The responsive portal includes all three game cards, host/join routes, direct and legacy links, authorized Continue party, Back to games, host close/switch confirmation, cleanup recovery across refresh, stale-dialog dismissal, expired-session and network recovery, labelled forms and keyboard focus handling. Word by Word preserves a separate host and3–4 player phones; Prompt Royale includes its host among3–4 players; Reverse Prompt has exactly3 players with the host as author A.

## Reproduce

```sh
bash scripts/setup.sh
bash scripts/dev.sh       # API8000 + Vite5173; open http://localhost:5173
# Stop development before starting the combined demo.
bash scripts/demo.sh      # frontend + API on8000, one worker, no reload
bash scripts/check.sh
npm --prefix frontend run test:portal
PORTAL_URL=http://<laptop-LAN-IP>:8000 npm --prefix frontend run test:integration
```

Use the actual laptop LAN origin in private `.env` for PUBLIC_ORIGIN and BROWSER_ORIGIN and open that address on every device. The verified address in this session was `http://10.0.100.107:8000`. The sample API_PROXY_TARGET is blank so changing BACKEND_PORT also changes the Vite proxy. Setup verifies pinned public tokenizer/model assets; it never allocates paid allowances. Persistent quota/model files live outside disposable clips.

## Verification

- `bash scripts/check.sh`:139 backend tests pass; Ruff/format, ESLint, TypeScript and production build pass. Test folders are packaged to avoid cross-game filename collisions. Two upstream deprecation warnings remain.
- Six portal Playwright scenarios: responsive home, accurate roles, keyboard/code entry, direct refresh, all route destinations, player/host continuation, cleanup waiting across refresh, network versus expiry, and stale confirmation after another tab switches. Widths320/390/768/1360 have no horizontal overflow. The public wrong-code check uses the real API; five scenarios simulate session/availability/close contracts. These simulations are explicitly separate from connected game evidence.
- The real combined browser scenario completes **Word by Word → Reverse Prompt → Prompt Royale** using four isolated browser cookie contexts, one laptop viewport1360×1000 and three phone viewports390×844. No API responses are intercepted. Word fixture contributions use its supplied examples through real API commands; host/join/navigation/reveal and the other games' submissions use browser controls.
- Word: separate host plus3 phones; manual generic room-code join and displayed join URL; refresh, all4 contributions/reveals, saved replay; host/player return and continuation. Close/switch rejects the old code/media and requires a fresh roster.
- Reverse: host A plus B/C; complete3 scene turns and2 guesses, sample88/46 result; all3 saved videos decode/play, results survive continuation/refresh. Close/switch rejects old code/media.
- Prompt: playing host plus3 phones; choose bundled topic,4 private entries,4-tile arena playing on each device, host/player return and continuation with stable arena, voting/results, portal close, old media denied. Owner's separate browser scenario also covers3 players, generated fixture topics, exclusions and playback recovery.
- CUA independently inspected phone home/join, keyboard focus and invalid-code recovery. It verified the actual `scripts/dev.sh` Vite5173→API8000 proxy with GET discovery, JSON form submission and direct-route refresh. Development stops before the combined demo restarts.
- FFmpeg/ffprobe7.1.1 and Reactor1.5.1 native import verified. Pinned tokenizer checksum verified. MiniLM scored exact100/paraphrase82 with sockets blocked, token limit256, warm batch~12ms. All fonts are bundled locally. npm audit reported0 advisories.

Browser source: `frontend/tests/portal.spec.ts` and `frontend/tests/combined.spec.ts`. Connected scenarios need an idle fixture server and close only their own authenticated rehearsal party.

## Four-digit code acceptance

Adopted specification `7e6b2b48478079d1c34f1d2a3ba2ddd2432f1863` without replacing the newer portal design. Every game now uses a coordinator-generated four-ASCII-digit string and the same browser input/validation. No numeric coercion, uppercase conversion, truncation or padding. Missing/non-string/short/long/internal-space/letter/fullwidth inputs receive the exact format error. Malformed direct attempts count against server rate limits. Explicit activation overrides and caller-supplied code updates were removed after all consumers migrated.

The combined LAN scenario passed with a controlled `0042` for each new party. Manual portal entry, copied links, direct forms, whitespace trimming, refresh and continuation preserve it. Word and Prompt accept all three entry paths during the complete rounds; a separate passing Reverse direct-form check supplements its manual/copied round. Same-roster Another round, Play again and Reverse Reset preserve the code. Word Reset party clears its roster, generates a different four-digit code, and retires the previous lookup. Shared collision tests retry an excluded code without replacing the party; closure/restart invalidation and code-only authorization are covered by shared/game tests. The integration test setup initially read Reverse's create acknowledgement as a snapshot; it was corrected to fetch state, and the affected direct-form scenario passed.

For reproducible leading-zero acceptance, stop the normal server, run `.venv/bin/python -m scripts.rehearsal_room_codes`, then `PORTAL_URL=http://<laptop-LAN-IP>:8000 PORTAL_EXPECT_CODE=0042 npm --prefix frontend run test:integration`. This explicit harness forces fixture mode, disables every live flag, uses separate disposable media, and overrides only its own process's code generator. Stop it and restore `bash scripts/demo.sh` for normal secure random codes. The final demo uses the normal command.

Six final portal browser scenarios pass against the strict resolver. The complete three-game controlled-code sequence and supplementary direct-join scenario pass. Screenshots below include `0042` on actual game screens. Phone views remain desktop Chromium contexts, not physical devices.

## Evidence

[Desktop portal](../evidence/portal/desktop.png) · [phone home](../evidence/portal/phone-home.png) · [phone join](../evidence/portal/phone-join.png) · [cleanup confirmation, simulated contract](../evidence/portal/cleanup.png)

[Word results](../evidence/portal/word-connected.png) · [Reverse results](../evidence/portal/reverse-connected.png) · [Reverse phone](../evidence/portal/reverse-phone-connected.png) · [Prompt arena](../evidence/portal/royale-connected.png) · [Prompt phone](../evidence/portal/royale-phone-connected.png) · [Prompt results](../evidence/portal/royale-results-connected.png)

## Commit milestones

Normal merges preserve each game branch's ancestry. The foundation SHA was reported immediately and sent to all three game owners before their implementation.

| Milestone | Integration commit |
| --- | --- |
| Runnable foundation | `eb831d80310ae548374143f236c90caf73a90c00` |
| Shared verified native dependencies | `a75766fe66d21fd860cb8c54f26cb3ba1a7f1891` |
| Complete portal UI | `0f3fe9f41323c273ba0c341364d0a5bd5b17060d` |
| Word playable fixture, source1151bad | `3e3d3306a74f2580c096197c9079785a43d8def9` |
| Reverse playable fixture, source65322cc | `faa6b16ac93ae558cd025b9dbd754fcda783a390` |
| Reverse cleanup/quota and LAN clipboard hardening, source98875cf | `2bc48cc707a361599486ef9cdcd964b7b7b7ede6` |
| Stale portal close-dialog recovery | `e291fee71eb29df069bdb4f6c9e28367bc4187f6` |
| Prompt playable fixture, source5607c23 | `6fb77672f577b354c9e88ccfdace152827685c1b` |
| Reverse organizer guard, source30f6e5a | `e271eaefc5580ba98e0e216505e409bbbc0ef5eb` |
| Prompt host guard/presence, sourcef8b3173 | `3f43fb0cd6e614ce5da310ec4c85a8a35dc15f96` |

Additional integrated milestones:

| Milestone | Commit |
| --- | --- |
| Full portal / three-game fixture acceptance | `a9e5c2426b290fb622fe47bf7836589d2fa06fd0` |
| Word guarded FastH3 adapter and recovery, source26c63b0 | `3b925e8b7d3c7c9e0c6f19e9d901a3ee5ed098da` |
| Reverse direct capture and evidence, source91926b5 | `f5c625ab8131666a971def2af2832ad266a1002c` |
| Shared four-digit helpers | `4b4164d37aff88a32bf5ad5fc7d9c1439df71ec7` |
| Strict portal code resolution | `35ecb7154540f8da37fa1add8f68d0e56cadcbfa` |
| Word code migration, source3a8752c | `5f598be3bd4fbce2fc989fa78b8490136e4d9869` |
| Prompt code migration, sourcee9c3c21 | `9d5928810270b7f2f8c5944a42c68963a01cb177` |
| Reverse code migration, source67bb2b2 | `8d99cad8f55c7b1ce9c715a9205fbf036d199f7a` |

## Remaining release gates

No Session A paid attempts or exclusive provider slots were granted. [Trial ledger](../live-provider-slots.md) records requests. Reactor's [billing documentation](https://docs.reactor.inc/resources/billing) says account usage/billing APIs are still in development. The read-only dashboard attempt redirected to sign-in; no signed-in account was available. Shared balance and earlier-session closure therefore still need operator confirmation before any slot transfers or Reverse persistent campaign allocation.

Live generated footage and game-specific live acceptance remain unverified. Prompt live topic generation also needs its configured provider credential. Guarded Word FastH3 and Reverse direct-frame capture adapters are integrated; their real provider trials remain unverified. Desktop Chromium phone viewports are not physical phones: actual Safari/Chrome playback, laptop firewall and group LAN rehearsal remain open. Remote deployment is deferred.
