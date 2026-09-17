# VibeParty backlog

Updated: 17 September 2026. Starting-image work and returning-host recovery are complete. No open items.

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

**Status:** Fixed 17 September 2026. **Priority:** High.

**Reported problem:** After closing all tabs and returning to `http://localhost:8000/#games`, a host whose cookie was missing or invalid saw only **Join current party** and **Back to games** when trying to host Prompt Royale. No recovery route existed.

**Implemented:**

- **Recover host access** is available in the blocked switch dialog and Word by Word host entry.
- Passcode mode requires the configured host passcode. Local mode requires a private per-party recovery code on the server laptop, shown by `uv run python -m scripts.host_recovery` from the running project with matching settings.
- Recovery checks the current party and replaces the old host session while preserving the round and player sessions. Guest/player actions, room codes, hostnames and `#games` do not grant host authority.
- The chosen destination stays selected. The recovered host can continue the party or explicitly close and switch; provider cleanup must complete before the next game opens.
- Word by Word host cookies persist across browser restart for up to seven days, subject to server-side party expiry. The portal no longer labels an active party as ended merely because its cookie is invalid.

**Verification:** 239 backend tests and 16 Chromium browser checks passed, including lost/stale cookies, both recovery modes, tab reopening, browser restart, alternate hostname, ownership restrictions and pending cleanup. A subsequent online WW-CAT-01 check also passed: one real LingBot session, recovery during streaming, complete recording/replay, confirmed provider closure, and switching to Prompt Royale. [Implementation and verification record](docs/research/word-by-word/2026-09-17-host-recovery.md).

The original cookie-loss cause remains unconfirmed because the original hostname/profile and cookie lifecycle were not captured. The new checks establish the behavior of valid cookies and explicit recovery when they are unavailable.
