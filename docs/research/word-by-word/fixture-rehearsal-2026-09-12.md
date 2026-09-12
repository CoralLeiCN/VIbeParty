# Fixture evidence — 12 September 2026

This evidence covers scripted local assets and fake providers. **No Reactor generation occurred and no live acceptance gate is passed.**

## Automated evidence

`pytest backend/tests/word_by_word -q`: 22 passed. Covers 3/4 assignments; exact trimmed Unicode text and 120-code-point boundaries; empty/over-limit correction; immutable duplicate input; ownership; duplicate start/next; future prompt exclusion; host/player snapshots; missing/wrong game cookies; JSON Origin enforcement; authenticated session discovery without timer refresh; byte-range authorization; 45-second collection expiry; bounded fake-provider step timeout; usable prefix; cancellation and stale round IDs; same-roster rematch; reset/atomic code rotation; 30-minute inactivity expiry; unresolved close blocking another game; three live-mode fake attempts surviving reset/close; and actual fixture MP4 decode/metadata.

Ruff, frontend TypeScript check/build and ESLint pass. TestClient emits upstream HTTPX/AnyIO deprecation notices; tests succeed.

## Browser rehearsal

CUA in-app browser on the actual laptop, frontend5174/API8011 over HTTP. Host uses localhost; one browser player uses the configured LAN origin10.0.100.107:5174 for cookie isolation. Two/three additional independent API clients are supplied by `rehearsal_players.py`. This is **not a three-physical-phone test**.

- Host entry, disabled start below3 players, visible join code and LAN join link.
- Three-player roster Ada/Bo/Cy; Ada receives place and consequence. Four accepted contributions start preparation without another host action.
- Player refresh restores both accepted answers and the original deadline.
- Host ready screen contains no contribution or video until Play.
- Manual Play/Next reveals the four exact contributions with names; phones show only the disclosed prefix and no video.
- Native saved-video playback observed: readyState4,640×360,6-second duration, advancing currentTime; illustrated forest, fox, dancing, confetti inspected.
- Results Replay progressed from saved clip0 to clip3 and ended at6 seconds. No provider request.
- Phone390×844 viewport inspected: forms/status/cards fit, text wraps, labelled controls remain usable.
- Back to games → Continue party restores results. Another round returns the same Ada/Bo/Cy roster. Adding Dee produces4 players; Ada then has only place.
- In the4-player round, Hide video removes the media; End round after the first Play leaves only place on host and phone results, despite four saved clips.
- Server restarted once in fixture mode: stale host cookie shows “This party has ended. Join again to play.” Startup clears only the game's private clips.

Still required: all-phone browser rehearsal after shared origin-alias update, actual3–4 physical phones on the demo network, full-length live input/layout rehearsal, genuine FastH3 additive output, actual billing and independent provider closure evidence. Operator/coordinator live readiness is pending.

## LAN clipboard follow-up

Merged shared HTTP clipboard helper `13ebbac398efd1c101fdff5f298a5a871c69eace` and wired the Word host button with a visible manual-copy fallback. On the real LAN HTTP host URL at port 5174, CUA clicked **Copy join link**, the button changed to **Copied!**, and the browser clipboard contained the matching LAN join URL and room code. This was an actual clipboard fallback check; no provider traffic was involved.

## All-browser roster follow-up

Actual CUA browser rehearsal on this laptop: LAN HTTP host at `10.0.100.107:5174`, then isolated browser cookie identities at `localhost`, `127.0.0.1`, `a.localhost`, and `b.localhost`, all port 5174. Trusted aliases were explicitly configured in the worktree's private environment. A raw `127.0.0.2` alias did not connect on this laptop; no network settings were changed to make it work.

Three players (Ada, Bo, Cy) joined through the UI. Ada received Place and Consequence, Bo Character, Cy Action. All four examples were submitted from those browser forms. Host saw counts only; all phones reached the still-secret reveal. A phone refresh preserved its role. Manual Play disclosed only Place; End retained only that card. Another round retained the same roster/code, and Dee joined through the fourth browser identity. In the four-player round everyone had one assignment; all four browser forms submitted and reached the protected reveal without exposing future text or video. These are browser identities, **not four physical phones**.

## Internal fake: exact text, partial results, and recovery

Ran `scripts/games/word-by-word/rehearsal_server.py --scenario partial` on port 8011 using the real built frontend and game rules with a hardcoded local provider fake. A sticky **INTERNAL TEST FAKE** banner explicitly stated that arbitrary input and unrelated prerecorded video do not represent AI generation. This server cannot construct a Reactor provider. It was stopped after verification and the normal fixture application restored.

- Entered 121 Unicode code points, including an astral emoji and accents. Counter showed `121 / 120`, a correctable message appeared, and submission was disabled. Corrected to exactly 120 code points with surrounding U+2003/U+00A0 whitespace; the accepted text retained all interior text exactly and removed only that surrounding whitespace.
- The first rehearsal reached the actual 45-second input deadline while browser inspection was underway. All clients showed incomplete results, with no story disclosed. A same-roster rematch succeeded.
- Next round collected the 120-point Place, a Japanese Character with emoji, an English sentence Action, and a two-sentence Consequence with emoji through browser forms. A fake timeout at step 3 saved only the first two clips. Host displayed the partial-story label; future Action/Consequence remained undisclosed.
- Played the two saved additions manually, finished, and replayed them while cleanup was unresolved. Another round and Reset were disabled. **Retry cleanup** changed the fake closure result to confirmed and enabled both controls without another generation.
- The full 120-point card and Japanese text were present in host/phone DOM and wrapped visually. The browser viewport override reported success but did not resize: measured width remained 1280. Therefore mobile-width evidence uses an explicit 390×844 CSS-pixel iframe with the actual app; its content viewport measured 375 pixels after scrollbar, document width also 375, card width 339. Screenshot inspection confirmed complete wrapping with no horizontal overflow. This is responsive-layout evidence, not a physical-device test.

## Four-digit code adoption

The shared standard `docs/shared/room-code-spec.md` supersedes the historical five-character codes above. Word now constructs its room from the coordinator's atomically reserved four-digit string and uses shared strict normalization in direct admission. Roster-clearing reset calls the coordinator's atomic rotation; same-roster rematches retain the string. Browser entry uses the shared text field/numeric keyboard/ASCII pattern, without uppercase conversion or length truncation.

Focused API checks force initial `0042`, then force a reset collision with `0042` before drawing `9012`. They verify copied/join URLs, trimmed manual input, preserved refresh/host resume/rematch, reset and retired lookup, role protection, closure, rejected numeric/non-string/non-ASCII/malformed input, and direct throttling including invalid-format attempts. The shared helper suite covers generation/lookup collision rules. Latest Word + shared result: **59 passed** (38 Word, 21 shared); Ruff, build and ESLint pass.

CUA used the explicit internal fake with `--code-0042` to keep this reproducible without paid calls. Host displayed `0042`; copied URL retained `code=0042`; direct join prefilled all digits. Inputs `42` and `１２３４` showed **Enter a 4-digit room code.**; unknown `0043` showed **That party isn't available. Check the code with your host.**. The field stayed editable, ` 0042 ` joined successfully, and refresh preserved player/code. Roster-clearing Reset changed the code to `4960`, cleared the roster, and a direct retry of retired `0042` showed the unavailable message. The normal fixture server was restored afterward. Integration owns the final all-game portal/code-only link sequence.
