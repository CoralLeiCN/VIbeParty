# PORTAL-001: returning host recovery

Implemented and verified 17 September 2026.

Word by Word now offers **Recover host access** from its host entry and the blocked portal switch dialog. Recovery requires the configured host passcode in passcode mode. Local mode requires a random per-party code from the private file on the server laptop, accessible through `uv run python -m scripts.host_recovery`. The file is created with mode 0600 and never served by an API. Round resets preserve it; closure and startup remove it.

Recovery checks a public opaque party ID against the current room, rotates the host token, and retains the roster, round, provider cleanup state and generation limits. It does not close the party. The switch dialog keeps its destination and presents the normal close confirmation after host discovery succeeds. A recovered host can retry pending cleanup, and the next game remains blocked until closure is confirmed.

Host cookies now include a seven-day Max-Age, while server-side inactivity expiry remains unchanged. An invalid cookie no longer makes the portal claim that an active party has ended. The original report did not establish the hostname, profile or cookie lifecycle that caused session loss; that historical cause remains unconfirmed.

## Verification

| Check | Result |
| --- | --- |
| `bash scripts/check.sh` | Passed: backend lint/format, frontend lint/build, 239 Python tests. |
| `host-recovery.spec.ts`, real local-mode server | 3 Chromium tests passed. |
| `host-recovery.spec.ts`, real passcode-mode server | 3 Chromium tests passed. |
| Existing portal and room-entry browser suite | 10 Chromium tests passed, including player restrictions and cleanup/refresh switching. |
| Browser visual review | Recovery form and instructions reviewed in the in-app browser; spacing tightened within the scrollable dialog. |

The new backend checks cover missing/incorrect proof, room codes and alternate origins granting no authority, player restrictions, untrusted Origin rejection, bounded attempts, stale party IDs, invalidation of previous host sessions, continued player access, private file permissions/removal, reset persistence, and recovery while cleanup remains pending. The browser checks cover lost cookies, incorrect proof, explicit close confirmation, creating Prompt Royale after switching, direct host entry with a stale cookie, all tabs closed and reopened, a full Chromium restart with its persistent profile, and switching to an alternate hostname without host authority.

Scenario: **PORTAL-001**. Browser checks used the **WW-CAT-01 / categories-v1** fixture lobby without starting a round or submitting any of its four slots. These initial checks did not generate live media. The subsequent online verification is recorded below. Pending cleanup was exercised through controlled backend state and the existing portal response fixture. The repository check completed with existing dependency deprecation warnings and a frontend bundle-size warning.

For the new browser suite, use an isolated fixture server and run from `frontend`:

```sh
PORTAL_URL=http://localhost:8137 HOST_PASSCODE='your-server-test-passcode' \
  RECOVERY_MEDIA_ROOT=/absolute/path/to/server-media-root \
  npx playwright test --config playwright.integration.config.ts host-recovery.spec.ts
```

Configure both `localhost` and `127.0.0.1` origins at that port for the hostname check. Run once with `LOCAL_MODE=true` and once with `LOCAL_MODE=false`. The browser tests create and close their own parties and must use a disposable server.

## Online verification

**Passed 17 September 2026, 20:00:16–20:00:59 UTC.** The user's follow-up authorized one real session (`2026-09-17-host-recovery-001`), with no generation retry. This was a custom Chromium browser check against an isolated server at localhost:8141, using the existing Reactor credential and the committed Place-only forest seed. The initial harness invocation stopped at a label selector before creating a provider session; the selector was corrected before the single live attempt.

Scenario **WW-CAT-01 / categories-v1**, current one-player demo: Live recovery tester owned all four slots. Exact answers: Place = `Enchanted forest`, Character = `A fox wearing a crown`, Action = `Dances ballet`, Consequence = `Glowing snow begins falling`. Submissions arrived in Consequence → Character → Place → Action order. No image generation was needed.

- Real LingBot World 2 playback started with currentTime=0.254, paused=false, readyState=4 and no media error.
- Clearing host cookies made discovery anonymous. The blocked Prompt Royale switch dialog accepted the private local recovery code and restored the host while the round was still STREAMING.
- The old host cookie then received 401 for both state access and closure. The player remained authenticated and the same round continued.
- Generation completed with all four exact answer cards. Provider prompt updates occurred at 0, 6.333, 12.583 and 18.875 seconds.
- A single 25.125-second MP4 (8,381,446 bytes) was saved. Replay after refresh advanced with paused=false, readyState=4 and no media error. Full FFmpeg decoding passed.
- Provider cleanup independently confirmed terminal closure; the recorded provider state was `closed=true`, with `provider_closing=false` in the game.
- The original dialog retained Prompt Royale as its destination. **Close & switch** completed, the old recording became unavailable, and the recovered host created and closed a Prompt Royale party successfully.

[Sanitized browser/provider evidence](evidence/2026-09-17-host-recovery.json) excludes session IDs, cookies and credentials. The custom harness, raw provider evidence, recording and screenshot remain private under `.local/live-host-recovery-20260917/`. This verifies the live functional path on this laptop; physical phones and generated visual quality were not evaluated. Actual spend was not measured.
