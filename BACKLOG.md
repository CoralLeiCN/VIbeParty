# VibeParty backlog

Reviewed: 16 September 2026. This file records findings and proposed work only; no application changes were made.

## 1. Live LingBot World 2: starting image

Requested behavior: let the user upload a starting image or generate one through the host machine's existing Codex OAuth login using `codex exec`. Generated starting images should use the first player's answer to “Where does the story happen?”

### Triage

| ID | Finding | Classification | Status |
| --- | --- | --- | --- |
| WBW-001 | Users cannot upload a starting image through the game. | Valid feature gap | Open |
| WBW-002 | The game cannot generate its starting image through local Codex authentication and `codex exec`. | Valid feature gap; execution needs verification | Open |
| WBW-003 | The existing API image generator already uses only the first player's Place answer. | Existing behavior; no confirmed defect in answer selection | Retain when adding the new source |

### WBW-001 — Upload a starting image

**Finding:** The host UI exposes fixture/live mode and player count, with no image upload or image-source selector. The game's request models and routes accept text contributions and round controls, with no upload endpoint. `WORD_BY_WORD_SEED_IMAGE` points to a file already on the server; it is a developer configuration override, not a user upload flow.

**Evidence:** [Host controls](frontend/src/games/word-by-word/index.tsx#L419), [request models and routes](backend/games/word_by_word/integration.py#L35), [configured image handling](backend/games/word_by_word/live.py#L79).

**Backlog work:** Add a per-round upload choice and connect the selected image to the existing LingBot reference-image step. Decide whether the uploader is the host or the player assigned Place; the request does not specify that role.

**Acceptance:**

- The designated user can select an image through the game and see whether it is ready for the round.
- A valid upload can satisfy starting-image readiness without an OpenAI image API key; Reactor video configuration is still required.
- Validate image content and size, associate it with the correct round, and clear it with that round's media.
- Upload mode passes that image to LingBot before generation starts. A later round does not silently inherit the previous round's image.

### WBW-002 — Generate through local Codex OAuth and `codex exec`

**Finding:** Automatic image preparation currently calls `POST https://api.openai.com/v1/images/generations` with `OPENAI_API_KEY`. There is no Codex subprocess or authentication integration. Live readiness accepts only that key or a configured local seed image, so a Codex login alone cannot enable the current flow.

**Evidence:** [Live readiness](backend/games/word_by_word/live.py#L39), [image generation request](backend/games/word_by_word/live.py#L93), [disabled live option](frontend/src/games/word-by-word/index.tsx#L428).

**Feasibility:** Local CLI inspection found `codex-cli 0.153.4`; `codex exec --help` confirms noninteractive execution. Official documentation says [`codex exec` reuses saved CLI authentication](https://learn.chatgpt.com/docs/non-interactive-mode#authenticate-in-automation), documents [ChatGPT sign-in](https://learn.chatgpt.com/docs/auth#sign-in-with-chatgpt), and describes [CLI image generation using `$imagegen`](https://learn.chatgpt.com/docs/image-generation). These support investigating the requested integration. Producing and retrieving an image through a noninteractive run on this machine remains unverified; no generation command or login change was performed. The `--image` CLI flag attaches an input image and does not itself request image generation.

**Backlog work:** Verify image generation and artifact retrieval through `codex exec` using the host's saved login, then add that image-source option to the backend and round UI.

**Acceptance:**

- The chosen Codex path uses the host's existing login and produces a usable local image without requiring `OPENAI_API_KEY` for that path.
- Readiness distinguishes missing CLI, missing login, and unavailable image generation, with actionable feedback.
- The image prompt contains the accepted Place answer and fixed scene instructions only; no later answers enter the request.
- The backend receives a validated image file for the current round and passes it to LingBot before `start`.
- Cancellation, timeout, failed execution, or missing output ends preparation cleanly within the round deadline. No automatic generation retries are introduced.
- The image-generation task treats the player's answer as scene data and runs with access limited to the files needed for that round.

### WBW-003 — Preserve generation from the first player's Place answer

**Finding:** Place is slot 0 and asks “Where does the story happen?” Slots are assigned in join order, so the first joined player owns Place. The provider receives answers in slot order and calls `starting_image(texts[0], directory)`. Its generated-image prompt includes Place only and requests one image. This uses the Place answer even if another player submits first.

**Evidence:** [Categories and question](backend/games/word_by_word/domain.py#L13), [slot ownership](backend/games/word_by_word/service.py#L242), [ordered provider input](backend/games/word_by_word/service.py#L329), [starting-image call](backend/games/word_by_word/live.py#L203), [Place prompt](backend/games/word_by_word/live.py#L86), [existing mocked test](backend/tests/word_by_word/test_live.py#L198).

**Related behavior to account for:**

- Image preparation starts after all four answers are accepted, as specified by the current game flow. It does not begin immediately when Place is submitted. If immediate preparation is intended, record it as an additional timing change. See [collection completion](backend/games/word_by_word/service.py#L285) and [round flow](docs/games/word-by-word/game-spec.md#3-play-a-round).
- A configured `WORD_BY_WORD_SEED_IMAGE` takes precedence and bypasses Place-based image generation. The code does not check that the file matches the current Place, so a fixed development image can disagree with a new answer. This is a documented override, not evidence that the generated-image prompt selects the wrong answer. Source selection added for WBW-001/002 should make this choice explicit and prevent the override from silently replacing a selected generation path.
- User-uploaded images supply the starting scene directly. The requirement to generate from Place applies to the generation choice; how an upload should relate to Place remains a product decision.

**Acceptance to retain:** Each generated starting image uses only the current round's accepted Place answer, regardless of submission order. Character, Action, and Consequence remain excluded until their existing video stages.

### Verification record

This review inspected source, existing tests, prior verification notes, local CLI version/help, and official Codex documentation. Tests were read but not rerun; no browser rehearsal, image generation, or live LingBot session was started.

The [existing WW-CAT-01 verification record](docs/research/word-by-word/2026-09-16-lingbot-continuous-flow.md#online-results) reports two successful live runs using a separately generated, configured seed image. It explicitly states that the app's automatic image API path was tested with mocks and was not called online. Those results do not establish that upload or `codex exec` integration exists.

For future verification of WBW-001/002, use [WW-CAT-01 and the current four-slot mapping](docs/games/word-by-word/test-scenarios.md): Place = `Enchanted forest`, Character = `A fox wearing a crown`, Action = `Dances ballet`, Consequence = `Glowing snow begins falling`. Record the selected source, submission order, actual image artifact, and whether LingBot accepted it before starting. Current result for both proposed sources: **not run; integration absent**.

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
