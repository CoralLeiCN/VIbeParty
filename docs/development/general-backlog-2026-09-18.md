# General backlog implementation

18 September 2026. Scope: [GEN-001 and GEN-002](../backlog.md). Requirements: [shared host controls and player names](../shared/host-controls-and-names.md).

## Host controls

All three games use the same host controls below the current round content, with matching button order, styling, and responsive layout. The lobby uses **Start round** followed by **End game**. Finished rounds use **Start another round** followed by **End game**.

**Start another round** returns to setup with the same room, players, and identities, clearing the previous round's content. Reverse Prompt no longer asks the host to confirm a reset after results. Word by Word can return to setup when its live allowance is exhausted; further live starts remain blocked, and fixture play remains available.

**End game** opens the same confirmation in each game. **Keep playing** dismisses it and restores focus to the opener. Confirmation calls the shared, authenticated party-close endpoint and returns the host to the portal. If cleanup is still pending, the portal tracks it and keeps new admission blocked. Errors stay in the dialog with a retry. Guest screens never show host controls.

Equivalent creation and invite actions use **Create party**, **Copy join link**, and **Copied!**. Word by Word and Prompt Royale use **End round** to stop a round and show its outcome. Reverse Prompt retains its separate **Stop & reset round** action during an unfinished relay because it clears content and returns to the lobby.

## Player names

Every existing host and guest name field starts with a random adjective and animal, such as `Sunny Otter`. Suggested names fit all three games' 24-character limit. The default is initialized once per mounted form; ordinary rerenders, polling, other fields, and validation errors preserve edits. Players can submit the suggestion unchanged. Word by Word's host currently has no player-name field; playing-host support remains tracked under WW-001.

## Verification

- Frontend production build and ESLint pass. Backend Ruff lint and format checks pass.
- All 239 backend tests pass, including returning to Word by Word setup after exhausting live attempts while retaining the roster and enforcing the live limit.
- All 15 Chromium checks pass (10 portal/entry checks and 5 integration/recovery checks). Browser entry checks cover accepted suggested names, edited names retained after an invalid room code, guest refresh, host-only controls, confirmation cancellation and focus restoration, failed closure and retry, and return to the portal.
- Complete fixture rounds check identical result controls at 1360px and 390px widths, rematches preserving room codes and players, and closure invalidating guest access and old media. Host recovery and switching checks use the updated labels.
- Word by Word rehearsal: **WW-CAT-01**, three joined players, current four-slot mapping. Place = `Enchanted forest`; Character = `A fox wearing a crown`; Action = `Dances ballet`; Consequence = `Glowing snow begins falling`. The fixture round reaches results with all four cards, saved replay, and a rematch retaining the room and roster. This verifies the interface and lifecycle using scripted media; no live model generation was run.

Browser screenshots are written under the ignored `frontend/test-results/` directory by the combined integration test.
