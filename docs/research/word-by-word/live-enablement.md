# Live FastH3 option, 12 September 2026

Word by Word now uses `WORD_BY_WORD_LIVE_ENABLED=true` and a configured
`REACTOR_API_KEY` to enable the host's **Live FastH3** round option. The private
environment in this task has the flag enabled. Restart the server after changing
it; settings are loaded at startup.

This replaces the earlier capture/prompt verification flags and trial-slot flags
as app admission requirements. Those flags no longer need to claim that pending
checks have passed. The provider still requires its full advertised frame count,
validates saved clips, uses cumulative prompts and predecessor clips, enforces
timeouts and three live attempts per process, and independently verifies session
closure. Generation begins only after all four contributions are accepted.

The [last live trial](laptop-gate-2026-09-12.md#actual-trial-2026-09-12-word-003--capture-gate-failed)
received 156 of 158 advertised frames and saved no valid clip. This change does
not resolve that capture failure or establish continuity or maximum Unicode token
fit. No paid generation was run for this change.

Verification: the 68 Word by Word and shared backend checks passed, including the
updated presenter/credential admission check. One shared route check initially
failed because this new worktree had no frontend build; it passed after copying
the primary checkout's build, whose frontend source matches this task. Ruff,
formatting, and diff whitespace checks passed.

A preview is running at `http://127.0.0.1:8011`. Browser verification is pending:
automatic approval review requires explicit permission to submit the local host
passcode. The app on port 8000 has an active Word by Word party and has not been
restarted. No scenario was submitted; `WW-CAT-01` and the other standard live
scenarios remain unrun for this change.
