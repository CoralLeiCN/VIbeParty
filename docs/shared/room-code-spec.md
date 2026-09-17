# VibeParty: shared room code standard

[All docs](../README.md) · [App specification](../app-spec.md)

Status: accepted design, 12 September 2026. Applies to the portal, Word by Word, Prompt Royale, and Reverse Prompt. Implemented across all three games and the portal; leading-zero and lifecycle acceptance is recorded in the [portal handoff](../development/handoffs/portal.md).

This document owns room code format, entry, generation, and lifecycle across all games. Each game's specifications own its admission rules, player roles, session authorization, expiry timing, and cleanup requirements.

## 1. Format and entry

- A room code is exactly **four ASCII digits**, `0000` through `9999`. Leading zeros are valid: `0042` is a complete code.
- Store and transmit codes as strings in room state, JSON, and URL query parameters. Preserve all four digits in displays, copied links, and redirects. Internal room IDs remain separate from the entry code.
- Trim surrounding whitespace, then require a full match of `[0-9]{4}` in both the browser and server. Reject non-string API values, letters, internal spaces, punctuation, non-ASCII digits, and shorter or longer input. Do not pad, truncate, or convert numeric input into a code.
- Use the label **Room code**, a single text field with a numeric keyboard (`type="text"`, `inputmode="numeric"`, `pattern="[0-9]{4}"`), and support pasting the whole code. A join link prefills this field; the player still completes the game's join form.
- For invalid format, show **Enter a 4-digit room code.** For a valid format with no available party, show **That party isn't available. Check the code with your host.** Keep the field editable. Full-room and in-progress messages follow the game's admission rules.

Examples:

| Input | Result |
| --- | --- |
| `0042`, `1234`, `0000`, `9999` | Valid format; look up the room. |
| ` 0042 ` | Trim to `0042`, then look up the room. |
| `42`, `12345`, `12 34`, `ABCD`, `１２３４` | Reject with the format message. |
| JSON number `42` | Reject; the API requires a string such as `"0042"`. |

## 2. Generation and lifecycle

- Generate codes on the server using a cryptographically secure random choice from the four-digit range, formatted with leading zeros. Reserve the code atomically with room creation; codes must be unique among active rooms across all games served by the application. Retry a collision without replacing an existing room.
- Generate a code when a room is created. Resuming the room, refreshing, returning to the portal, and starting another round with the same party keep the code. All three games use **Start another round** for this action. Reverse Prompt also preserves the code when resetting an incomplete round.
- A party reset that clears the roster rotates to a different code and removes the previous lookup. Closing or expiring a room removes its lookup; an in-memory server restart loses all room lookups and sessions. Creating a new party, including after switching games, generates a new code. Follow the game's cleanup guards before admitting new work.
- Codes may be reused after retirement; they never restore previous membership. Use the separate room ID and authenticated session to identify an existing party and participant.

## 3. Shared joining and authorization

The portal's generic join and each game's join endpoint use the same format and validation. The planned `POST /api/party/resolve` resolves the code to the game's join destination while preserving its string value, for example `/games/reverse-prompt/join?code=0042`. A code-only link such as `/join?code=0042` uses the same resolution. The game validates the code again when admitting a player.

A code locates a room. Host access codes and organizer passcodes are separate configuration; game-scoped session cookies authorize membership, roles, actions, and private media. Rate-limit code resolution and join attempts on the server, including calls made directly to game endpoints. Resolution exposes only the join destination.

The integration foundation owns shared code generation, validation, and lookup under `backend/shared/`, with shared entry presentation under `frontend/src/shared/`. The [parallel development plan](../parallel-development-plan.md#3-foundation-contract-complete-before-branching-game-implementation) must reference this standard when publishing exact implementation contracts.

## 4. Implementation acceptance

- For each game, create a room and join through manual portal entry, a copied link, and the game's direct join form. Verify a leading-zero code such as `0042` throughout, using a controlled fixture when needed.
- Check invalid formats in the UI and direct API requests, a valid but unknown code, and rate limiting on both resolution and game joins. Verify collision handling without overwriting an active room.
- Verify that refresh, continuation, and another round preserve the code; a roster-clearing party reset changes it; closure, expiry where supported, and restart remove the old lookup and sessions.
- Verify that knowing the code alone cannot perform host actions or read private game state or media.
