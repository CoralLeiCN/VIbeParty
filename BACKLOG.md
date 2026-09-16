# VibeParty backlog

Updated: 16 September 2026. Word by Word starting-image work is complete; the portal recovery item remains open.

## 1. Live LingBot World 2: starting image

Completed 16 September 2026. [Implementation and verification record](docs/research/word-by-word/2026-09-16-starting-images.md).

| ID | Work | Status |
| --- | --- | --- |
| WBW-001 | Host uploads a starting image for the current round, with preview and readiness. | Fixed |
| WBW-002 | Generate through the host’s saved Codex ChatGPT login using `codex exec`. | Fixed; real image generation and artifact retrieval verified |
| WBW-003 | Each generated starting image uses only the first joined player’s accepted Place answer. | Preserved and regression tested |

The host selects **Generate with Codex**, **Upload an image**, **Generate with OpenAI API**, or **Configured server image** in the live lobby. Selection is explicit and frozen when the round starts. Uploads and generated images are cleared with the round; a configured image never overrides a different selected source. Generation still starts after all four answers are accepted.

Uploads accept still PNG/JPEG/WebP files up to 10 MiB and 16 megapixels. The backend validates content, normalizes orientation, removes metadata, and stores a private PNG. Only the current host can upload or preview it. The selected image is passed to LingBot before `start`.

Codex readiness distinguishes missing CLI, missing ChatGPT login and disabled/unavailable image support, with a recheck action. The bounded subprocess receives fixed instructions and Place as scene data; shell, apps, plugins, browser, computer and delegation tools are disabled. Its result must be an image from that invocation's artifact directory. Timeout/cancellation terminates the process, no automatic generation retries run, and failures produce actionable round messages.

**Verification:** WW-CAT-01 uses Place = `Enchanted forest`, Character = `A fox wearing a crown`, Action = `Dances ballet`, Consequence = `Glowing snow begins falling`. The real Codex adapter produced a validated 1536×1024 PNG in 49 seconds with the existing login and no API key. Browser upload/preview/refresh/rematch checks passed with simulated Reactor transport, including reversed submission order. Backend checks cover authorization, invalid images, source precedence, prompt scope, timeout/cancellation, and cleanup. Live Reactor video was not rerun for this change; see the linked record for the verification boundary.

## 2. Returning host cannot close Word by Word and switch to Prompt Royale

### PORTAL-001 — Recover host access when an existing party blocks switching

**Classification:** Valid recovery bug. The missing recovery path is confirmed by source inspection; the exact reason this user's host session was no longer recognized remains unconfirmed.

**Status:** Open. **Priority:** High — blocks the host from starting another game through the UI.

**Reported steps:**

1. Start Word by Word as host.
2. Close all tabs, then return to `http://localhost:8000/#games`.
3. Click **Host Prompt Royale**.
4. The dialog says “There’s a party in progress” and asks Word by Word's host to close it. Its only actions are **Join current party** and **Back to games**. The returning host has no close/switch action.

**Expected:** A returning host can resume control of the existing party or recover host access, then explicitly close it and continue to Prompt Royale. The existing close flow should explain that everyone must rejoin and wait for provider cleanup before opening the next game.

**Findings:**

- The screenshot's **Join current party** label matches the dialog branch where no session is recognized. A recognized player would see **Continue party**; an authenticated host with `can_close` would see **Close & switch**. See [dialog permissions and actions](frontend/src/app/portal/SwitchDialog.tsx#L35) and [portal session selection](frontend/src/app/portal/Portal.tsx#L35).
- Party existence and browser identity are separate. `/api/session` can return `status: "anonymous"` while still reporting an active Word by Word party. Host identity depends on the `vp_word_by_word` cookie matching the room's host token. Opening the portal or adding `#games` does not establish that identity. See [session discovery](backend/shared/api.py#L42) and [Word by Word role discovery](backend/games/word_by_word/integration.py#L71).
- Recovery is absent even at the Word by Word host route: if a room exists and the cookie is missing or invalid, `Game.host()` returns `409 host_already_present` with “Reopen the host screen in its original browser.” This happens in local mode and, when passcode admission is enabled, even after the correct passcode is supplied. The close endpoint also requires the original host identity. See [existing-host rejection](backend/games/word_by_word/service.py#L124) and [close authorization](backend/games/word_by_word/integration.py#L84).
- **Back to games** preserves the active party, and **Join current party** provides no host recovery. Together with the existing-host rejection, this leaves a host who has lost their session without a UI route to regain control and switch games.
- The Word by Word cookie has no `Max-Age` or `Expires` set. This warrants checking browser-session lifecycle, but does not prove that closing tabs deleted it. A different browser/profile, a changed hostname such as `localhost` versus the LAN address, or an invalid/replaced cookie are also investigation candidates. The original hosting address and browser context were not established in this review. See [cookie issuance](backend/games/word_by_word/integration.py#L56) and [cookie isolation contract](docs/development/contracts/shared.md#L21).
- The party is not necessarily stuck forever: Word by Word defaults to expiry after 1,800 seconds of inactivity and attempts cleanup. This delayed fallback does not provide immediate host recovery, and unresolved provider cleanup can still block release. See [expiry default](backend/games/word_by_word/service.py#L41) and [expiry handling](backend/games/word_by_word/service.py#L478).

**Backlog work:**

- Diagnose why the returning browser lacks a recognized host session. Check the original and returning hostname/profile, cookie presence and persistence, and the `/api/session` status before and after closing tabs. Record only presence/status, never token values.
- Add an explicit way for the legitimate host to recover access to an existing party, with an appropriate ownership check for local mode and passcode mode. Expose it from the blocked switch dialog and the existing game's host entry.
- After recovery, restore **Continue party**, **Close party**, and **Close & switch** as appropriate. Preserve the selected destination so the host can continue to Prompt Royale once closure finishes.
- Explain when the current browser is not recognized as host and provide a recovery action. Keep player and guest restrictions, explicit close confirmation, and provider cleanup checks.

**Acceptance:**

- Closing and reopening tabs in the same browser with a valid host cookie restores the host and allows switching from Word by Word to Prompt Royale.
- When the host cookie is unavailable, the legitimate host can complete the recovery flow and close/switch without restarting the backend or waiting for inactivity expiry.
- Check browser restart and alternate hostname/profile cases separately; a different hostname or `#games` alone must not grant host authority.
- Players and guests cannot take over or close the party through ordinary host/join actions. Recovery requires the chosen ownership check.
- Closing clears the previous party only after cleanup is confirmed, then opens Prompt Royale's host flow. Pending cleanup remains visible and continues to block new generation.

**Verification record:** Reviewed the supplied screenshot, portal and backend source, and existing authorization tests. [The current shared test](backend/tests/shared/test_local_mode.py#L70) explicitly expects host creation and close to fail after cookies are cleared, then restores the saved host cookie to regain access; it does not exercise host recovery. [Portal tests](frontend/tests/portal.spec.ts#L173) cover switching with an already recognized host session. The available browser tool had no open tabs from the reported session, so its cookie state and tab-closing sequence were not reproduced. No party was created, closed, reset, or switched, and no tests were run for this backlog-only review.
