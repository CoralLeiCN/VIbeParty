# Word by Word local checks

Run from the repository root with the shared locked environment. Normal app development uses backend 8011 and Vite 5174, HTTP, and `GENERATION_MODE=fixture`. Copy the integration environment setup and keep credentials private. `API_PROXY_TARGET=http://127.0.0.1:8011`; `BROWSER_ORIGIN` must match the frontend; `PUBLIC_ORIGIN` is the laptop's actual LAN address for join links. Separate browser identities require separate hostnames/profiles because cookies are not isolated by port.

```sh
.venv/bin/pytest backend/tests/word_by_word backend/tests/shared -q
.venv/bin/ruff check backend/games/word_by_word backend/tests/word_by_word scripts/games/word-by-word
npm --prefix frontend run build
npm --prefix frontend run lint
```

`make_fixtures.py` regenerates the original deterministic H.264 example assets using FFmpeg. The normal fixture game accepts only their matching fixed contributions.

`rehearsal_server.py --scenario partial` runs the built frontend on `http://localhost:8011` with an obvious INTERNAL TEST FAKE banner. Stop the ordinary backend first. It exercises arbitrary input, two saved clips, a synthetic step failure, and unresolved cleanup that succeeds on Retry cleanup. `--scenario full` saves all four. Add `--code-0042` for controlled leading-zero join/lifecycle checks; it replaces only this rehearsal process’s initial random draw and leaves shared admission/rotation in place. It never constructs a Reactor provider. Stop it after checking and restore the ordinary backend. Its private media uses a separate disposable directory.

## Coordinated paid spike

Do not run this command until integration has allocated this exact trial. A new process does not grant another allowance. No paid command is part of setup or tests.

```sh
.venv/bin/python scripts/games/word-by-word/spike.py \
  --env-file .env --output .local/word-live/TRIAL-ID \
  --slot ALLOCATED-TRIAL-ID --previous-session-closed
```

The output directory must be new. One invocation makes at most one constrained session and four enqueues, with 120 seconds overall and 30 seconds per step. Default text is the documented forest/fox/dance/confetti example. For the group-selected trial, pass `--contributions-json /private/path/four-texts.json` (an array of four accepted strings). This never logs their contents. The evidence file records safe timing/frame metrics and independent closure; inspect all clips, boundaries, continuity, and saved replay, and record measured account spend separately. A failed/ambiguous request is not retried. Never transfer the slot until closure is confirmed.

The user explicitly directed the first trial to use the existing API key without dashboard account prechecks. For that allocated trial, replace `--previous-session-closed` with `--account-precheck-waived`; private evidence records the waiver without claiming prior closure was verified. The API establishes credential/funding validity. This does not waive exclusive allocation, attempt limits, or independent closure of any session created by the trial. Account spend can remain unmeasured if the dashboard is unavailable.

## Enable live play

Set `WORD_BY_WORD_LIVE_ENABLED=true` in the root private `.env`, configure
`REACTOR_API_KEY`, and restart the server. The host can then select **Live FastH3**
in the lobby. Generation begins only after all four contributions are accepted.

The presenter's live setting replaces the earlier capture/prompt verification and
trial-slot configuration gates. Enabling it does not establish capture quality,
continuity, or maximum Unicode token fit; the earlier failed capture remains in
the [trial evidence](../../../docs/research/word-by-word/laptop-gate-2026-09-12.md).
Keep credentials private; never put them in URLs or browser code.

The app separately enforces three live session attempts per process, one generation task, deadlines, ownership, disclosure, and unresolved-cleanup guards. Live evidence is stored privately beside the game's clips under `live-evidence/`; it survives round/file cleanup. Neither fixture checks nor mocked captures satisfy live acceptance.
