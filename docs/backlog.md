# Product backlog

[All docs](README.md)

Recorded: 17 September 2026. All items are pending implementation. Open decisions are noted below; game specifications describe current behavior.

## Across all games

### GEN-001 — Standardize host controls

Use identical button text for equivalent host actions in all three games, with consistent button order, placement, styling, and confirmation wording. After each round, use these exact labels:

- **Start another round:** return to round setup with the same players and room.
- **End game:** close the party and return the host to the game portal.

Verify that equivalent controls have identical wording and the same meaning and behavior across games.

### GEN-002 — Prefill player names

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

**Progress:** code and saved-frame review complete; live comparison pending. [Findings and experiment plan](research/word-by-word/2026-09-17-prompt-following.md).

### WW-004 — Rename the game to World by Word

Rename the game **World by Word** and give the **l** in **World** a contrasting accent color to highlight the word/world-model double meaning. Apply this treatment to the portal card, game heading, and branding. Keep the accessible name “World by Word.”

## Prompt Royale

### PR-001 — Enlarge each player's video and remove excess side bars

Size each video tile to the clip's original aspect ratio and fill the tile with the full frame, removing excess black side space. Verify the layout on laptop and phone screens, with labels and voting controls usable.

### PR-002 — Vote directly beside each clip without a reason

Place a **Vote** button beside each clip label. Clicking it submits the vote and marks the selected clip. Remove the reason field and any explanation step.

### PR-003 — Consolidate the arena playback buttons

Replace **Play arena** and **Replay all** with one clearly labelled button that restarts every clip from the beginning and loops them together.

## Reverse Prompt

### RP-001 — Support two to four players, including the host

Replace the fixed three-player roster with a host-selected count of **one to three guests**, for **two to four players total**.

- The host writes the original prompt; each guest takes a relay turn and submits a final guess.
- Match lobby capacity, start readiness, relay length, scoring, and results to the selected count.
- Support a complete round with one host and one guest, and verify all three supported player counts.
