# Product backlog

[All docs](README.md)

Recorded: 17 September 2026. Updated: 4 October 2026. General items GEN-001 and GEN-002 are complete. Game-specific delivery statuses and open decisions are noted below.

## Across all games

### GEN-001 — Standardize host controls

**Status:** Completed 18 September 2026. [Implementation and verification](development/general-backlog-2026-09-18.md).

Use identical button text for equivalent host actions in all three games, with consistent button order, placement, styling, and confirmation wording. After each round, use these exact labels:

- **Start another round:** return to round setup with the same players and room.
- **End game:** close the party and return the host to the game portal.

Verify that equivalent controls have identical wording and the same meaning and behavior across games.

### GEN-002 — Prefill player names

**Status:** Completed 18 September 2026. [Implementation and verification](development/general-backlog-2026-09-18.md).

Prefill every player-name field with a random valid name across all games, including host and guest entry. Let players keep or edit the name. Preserve their edits while completing the form.

## Word by Word

### WW-001 — Let the host play

- Let the host submit story contributions while retaining host controls.
- Include the participating host in the lobby's player count and preserve their identity through refresh and rematches.
- Keep the host's answers private on a shared display. **Open:** how the host accesses their private form.

### WW-002 — Cap the roster at four players, including the host

**Depends on WW-001.** Allow a maximum of **four players total: one playing host and up to three guests**. Include the host in the selected player count, lobby capacity, and assignments across Place, Character, Action, and Consequence. Reject joins beyond the selected count.

### WW-003 — Experiment with prompts for actions and consequences

Improve how reliably actions and consequences appear in the video.

- Compare category labels, connected sentences, and explicit motion descriptions using the standard scenarios. Test update timing separately.
- Link each action to its character and each consequence to the scene; preserve player meaning and original contribution cards.
- Review generated video for visible effects, response delay, and retained scene details. Use the results to choose changes to prompts, timing, or model.

**Progress:** code and saved-frame review complete. Stage-specific prompt instructions implemented 4 October 2026 to preserve the current character/action and exclude future-stage guidance; live comparison and visual-quality validation remain pending. [Findings and experiment plan](research/word-by-word/2026-09-17-prompt-following.md).

### WW-004 — Rename the game to World by Word

Rename the game **World by Word** and give the **l** in **World** a contrasting accent color to highlight the word/world-model double meaning. Apply this treatment to the portal card, game heading, and branding. Keep the accessible name “World by Word.”

## Prompt Royale

### PR-001 — Enlarge each player's video and remove excess side bars

Size each video tile to the clip's original aspect ratio and fill the tile with the full frame, removing excess black side space. Verify the layout on laptop and phone screens, with labels and voting controls usable.

### PR-002 — Vote directly beside each clip without a reason

Place a **Vote** button beside each clip label. Clicking it submits the vote and marks the selected clip. Remove the reason field and any explanation step.

### PR-003 — Consolidate the arena playback buttons

Replace **Play arena** and **Replay all** with one clearly labelled button that restarts every clip from the beginning and loops them together.

### PR-004 — Keep voting controls visible on phones

**Status:** Implemented 4 October 2026.

Pin the selected clip, countdown, Vote/Abstain actions, and locked confirmation while players scroll the arena. The [game spec](games/prompt-royale/game-spec.md#voting) owns selection and acceptance behavior.

### PR-005 — Explain a player's missing clip privately

**Status:** Implemented 4 October 2026.

Distinguish failed generation from a missed submission, and tell the affected player they can still vote when the round has enough eligible clips. Keep other players' identities private; see [generation feedback](games/prompt-royale/game-spec.md#generating).

## Reverse Prompt

### RP-001 — Support two to four players, including the host

Replace the fixed three-player roster with a host-selected count of **one to three guests**, for **two to four players total**.

- The current round's author writes the original prompt; every other player, including the host when not author, takes a relay turn and submits a final guess. Follow the author rotation in RP-003.
- Match lobby capacity, start readiness, relay length, scoring, and results to the selected count.
- Support a complete round with one host and one guest, and verify all three supported player counts.

### RP-002 — Reveal the story before guesses and scores

**Status:** Implemented 4 October 2026.

Reveal each prompt and its video together, in relay order, with the host advancing the shared reveal. Show guesses, scores, and the winner only after the last pair. This lets the group discover how the idea changed before seeing the outcome.

Requirements, controls, and acceptance: [sequential reveal](games/reverse-prompt/game-spec.md#rp-002--sequential-reveal).

### RP-003 — Rotate the author between rounds

**Status:** Implemented 4 October 2026 for the current three-player roster. RP-001 remains a separate expansion.

Rotate the author through the roster so everyone can write the original and interpret or guess on other rounds. Keep host controls with the party creator; being host does not permanently make that player the author or exclude them from guessing.

Requirements and acceptance: [author rotation](games/reverse-prompt/game-spec.md#rp-003--author-rotation).
