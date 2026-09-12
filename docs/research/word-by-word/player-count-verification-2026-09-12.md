# Word by Word player count verification

Date: 12 September 2026. The host can select 1–4 players in the lobby (default 3). The selected count controls admission and start readiness, persists through refresh/rematches, and cannot drop below the joined roster without a party reset.

## Automated checks

`pytest backend/tests/word_by_word backend/tests/shared -q`: **68 passed**, with two existing TestClient deprecation warnings. Scoped Ruff lint/format, frontend ESLint, and TypeScript/Vite build passed.

Scenario **WW-CAT-01**, fixture version `categories-v1`, was exercised with an explicit fake provider for each count 1, 2, 3, and 4. The four-slot inputs were `Enchanted forest`, `A fox wearing a crown`, `Dances ballet`, and `Glowing snow begins falling`, submitted in reverse reveal order. All four contributions were assigned, private until reveal, accepted once, and attributed in order. Each round used one fake provider with four segments; rematches retained count, roster, and assignment order.

Service and API checks covered strict integer validation, host-only settings, stale requests, lobby-only changes, pending cleanup, rejecting excess joins, waiting for the selected count, resuming a full lobby, and resetting before reducing the roster.

## Browser rehearsal

Codex in-app browser against the isolated, visibly labelled `rehearsal_server.py --scenario full` on port 8011. Host and players used independent cookies at localhost, 127.0.0.1, and a.localhost. The server's provider factory only copies local fixtures; no Reactor requests were possible.

Scenario **WW-CAT-01**, repeats 1 and 2: one-player and two-player four-slot demo flows, using the exact answers above through visible forms. The one-player flow assigned all four categories to Solo Tester. The two-player flow assigned Place + Action to Solo Tester and Character + Consequence to Second Tester. Both completed collection and all four reveals with exact text and correct contributor names. The host showed no answers before Play. Both rematches retained the selected count and players.

Lobby checks passed: changing 3 → 1; refresh retaining 1; one-player start; changing 1 → 4 → 2 between rounds; start disabled while waiting; player screens showing the selected count without a settings control; and the 1-player option disabled after two players joined. The host selector and surrounding layout were visually inspected in the desktop browser. Resetting before reducing the count was covered by the API checks.

Category labels and forms were visible. The existing form hints still use the older forest/fox/confetti examples; the scenario answers were entered manually. Videos were unrelated prerecorded fixtures, as the internal banner states. Generated visual additions, continuity, physical-phone playback, live capture, billing, and provider timing were not evaluated by this change.
