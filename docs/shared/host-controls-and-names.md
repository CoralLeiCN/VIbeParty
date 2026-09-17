# Shared host controls and player names

[All docs](../README.md) · [App specification](../app-spec.md) · [Portal specification](../portal-spec.md)

Updated: 18 September 2026. Implemented requirements from GEN-001 and GEN-002 in the [product backlog](../backlog.md).

This standard owns equivalent host controls and player-name entry across all three games. Each game specification owns its roster, roles, round setup, and cleanup rules.

## Host controls

Show a consistent host-control group below the current round content. Use matching styling and confirmation wording across games. On laptop screens, place buttons left to right in the order below; on narrow phone screens, stack them in the same order. Keep visible focus, readable contrast, and controls at least 46 pixels tall.

| Context | First action | Second action |
| --- | --- | --- |
| Lobby | **Start round** | **End game** |
| Finished round | **Start another round** | **End game** |

**Start round** follows the game's existing readiness requirements. **Start another round** returns directly to round setup with the same room code, players, and identities; clear the previous round's content according to the game specification. Preserve generation quotas and block new work while required cleanup is pending. In Word by Word, an exhausted live allowance still permits returning to setup for fixture play.

**End game** is available to the authenticated host throughout the party. It opens this confirmation:

- Title: **End this game?**
- Description: **This clears the party, its replay, and its player list. Everyone will need to rejoin the next game.**
- Buttons, in order: **End game**, **Keep playing**.

Cancellation preserves the party and returns focus to the opener. Confirmation requests party closure and returns the host to the portal. Closure clears the roster and media and retires the room code and session access. If cleanup remains pending, the portal shows that state and blocks new admission until closure is confirmed. A failed request keeps the confirmation open with an error and retry. Guests cannot see or perform host actions.

Equivalent entry and invite actions use **Create party**, **Copy join link**, and **Copied!**. **Back to games** preserves the party; it does not close it. Word by Word and Prompt Royale use **End round** to stop work and show the round outcome. Reverse Prompt's **Stop & reset round** clears an unfinished relay and returns to setup, with its own confirmation.

## Player names

Prefill every existing player-name field, including playing-host and guest entry, with a random valid name. Use a short adjective and animal, such as `Sunny Otter`, within the shared 1–24-character limit. Let the player keep or edit it. Preserve edits while completing the form, including changes to other fields, polling, and validation errors; rerendering must not generate a new suggestion.

The submitted name follows the game's existing validation and duplicate-name rules. Word by Word currently has a separate display host with no name field; its guest entry follows this standard.

## Acceptance

- Verify the exact host labels, order, placement, and styling in all games on laptop and phone widths.
- Complete a round and start another; verify the room code, roster, and identities are retained while round content is cleared.
- Cancel closure, retry a failed closure, and confirm successful closure returns to the portal and invalidates guest access. Pending cleanup must block new admission.
- Submit suggested names unchanged and submit edited names. Verify edits survive form errors and ordinary rerenders.
- Verify guest views omit host controls and the server rejects unauthorized host actions.

The [implementation and verification record](../development/general-backlog-2026-09-18.md) records the completed checks.
