# Word by Word: category examples for future tests

[All docs](../../README.md) · [Game spec](game-spec.md) · [Technical stack](tech-stack.md) · [Research](../../research/word-by-word/README.md)

Status: agreed test examples, 12 September 2026. Fixture version: `categories-v1`. These are intended results; no live output has been validated.

Use these categories, example answers, and expected additions for future Word by Word rehearsals, fixture preparation, and model evaluations. Keep the answers fixed when comparing runs. This document owns the test inputs and visual expectations; the [game specification](game-spec.md) owns the demo's slot assignments and reveal rules.

## 1. Three-player category example

Give everyone the same round theme. Each player contributes one idea in an assigned category. Collect answers privately, then reveal their effects in order: **Character → Action → Scene change**. Users control scene content through their contributions; these scenarios require no movement or look controls.

For the theme **Enchanted forest**, show:

| Player in the category example | Category | Phone instruction | Example answer |
| --- | --- | --- | --- |
| 1 | Character | “Who appears in the scene?” | A fox wearing a crown |
| 2 | Action | “What does the character do?” | Dances ballet |
| 3 | Scene change | “What happens around them?” | Glowing snow begins falling |

Each input also says: “Write a word, phrase, or short sentence. Keep it to one idea.” The Action player can answer without knowing the Character answer; apply that action to the character when the scene is assembled. Players see their own category and example, while other players' accepted answers stay private until reveal.

In the three-role example, rotate categories between players on successive rounds. Evaluate that rotation when testing this proposed flow. The current four-slot demo uses the existing assignment described below.

## 2. Mapping to the current demo

The current demo has four slots: **Place → Character → Action → Consequence**. To use these examples in that demo, submit the round theme as the Place answer and the Scene change answer as Consequence. The assigned tester enters the Place answer normally; do not autofill a live player's contribution. Reveal the place segment first, followed by the three additions. A separate model evaluation can establish the theme as its starting scene before applying the three additions.

Keep the demo's existing join-order ownership when rehearsing its phone flow:

| Joined player | Three-player demo | Four-player demo |
| --- | --- | --- |
| First | Place + Consequence | Place |
| Second | Character | Character |
| Third | Action | Action |
| Fourth | — | Consequence |

The three-player category example above and this four-slot demo have different assignments. Record which flow was tested; use the game specification's fixed assignments for current demo acceptance, including rematches. “Scene change” is the example's label for the demo's Consequence slot.

## 3. Standard scenarios

Use the theme and answers exactly as written, preserving capitalization. The expected effects below are reviewer criteria, not extra player submissions or guaranteed model behavior.

### WW-CAT-01: Enchanted forest — primary scenario

Starting theme / Place answer: **Enchanted forest**.

| Category | Example answer | Expected effect at this reveal |
| --- | --- | --- |
| Character | A fox wearing a crown | A fox with a visible crown appears in the established forest. |
| Action | Dances ballet | The same crowned fox performs recognizable ballet movements; the forest remains. |
| Scene change | Glowing snow begins falling | Luminous snow falls around the same dancing fox; its crown and the forest remain recognizable. |

Expected final scene: a crowned fox dances ballet in an enchanted forest as glowing snow falls.

### WW-CAT-02: Space station — default variation

Starting theme / Place answer: **Space station**.

| Category | Example answer | Expected effect at this reveal |
| --- | --- | --- |
| Character | A robot chef | A recognizable robot chef appears inside the established space station. |
| Action | Juggles oranges | The same robot chef juggles visible oranges inside the station. |
| Scene change | Gravity switches off | The robot and oranges visibly float while the robot continues trying to juggle; the station remains recognizable. |

Expected final scene: a robot chef juggles floating oranges as gravity switches off inside a space station.

### WW-CAT-03: Underwater city

Starting theme / Place answer: **Underwater city**.

| Category | Example answer | Expected effect at this reveal |
| --- | --- | --- |
| Character | An octopus magician | An octopus presented as a magician appears in the established underwater city. |
| Action | Performs a magic trick | The same octopus performs a visible trick; record what appeared and whether reviewers could recognize the action. |
| Scene change | Bubbles fill the street | A noticeable increase in bubbles fills the street around the same magician; the city and ongoing trick remain visible. |

Expected final scene: an octopus magician performs a trick in an underwater city as bubbles fill the street.

### WW-CAT-04: Haunted castle

Starting theme / Place answer: **Haunted castle**.

| Category | Example answer | Expected effect at this reveal |
| --- | --- | --- |
| Character | A nervous ghost | A ghost showing visible nervous behavior appears in the established castle. |
| Action | Hosts a tea party | The same ghost hosts a recognizable tea party in the castle. |
| Scene change | The furniture starts floating | Furniture visibly lifts around the same ghost and tea party; the castle remains recognizable. |

Expected final scene: a nervous ghost hosts a tea party in a haunted castle while the furniture floats.

## 4. Prompt assembly example

Keep player submissions separate from the effective model prompt. Each update includes the theme, the newly revealed contribution, and established facts through that step. Preserve the original answer on contribution cards. The fixed camera below is a rendering instruction; players do not operate it.

For `WW-CAT-01`, an illustrative sequence is:

| Step | Effective model prompt |
| --- | --- |
| Setup / Place | Theme: Enchanted forest. Establish a forest clearing surrounded by tall trees. Playful illustrated style, fixed wide shot. |
| Character | Theme: Enchanted forest. Character: A fox wearing a crown. Introduce this character in the established clearing with the crown visible. Retain the forest, illustrated style, and fixed wide shot. |
| Action | Theme: Enchanted forest. Character: A fox wearing a crown. Action: Dances ballet. The same crowned fox begins ballet movements in the clearing. Retain its appearance, the forest, illustrated style, and fixed wide shot. |
| Scene change | Theme: Enchanted forest. Character: A fox wearing a crown. Action: Dances ballet. Scene change: Glowing snow begins falling. Add luminous falling snow around the same crowned fox as it continues dancing. Retain the forest, illustrated style, and fixed wide shot. |

Future contributions must not enter an earlier step's prompt, starting image, generated asset, or public display. For model evaluations requiring an initial image, prepare it from the theme alone and record the image used. Wait until a change is visibly established before applying the next update in a continuous-stream evaluation. For the current demo, follow its private generation and manual reveal sequence.

## 5. How to use these in future tests

Use `WW-CAT-01` twice and `WW-CAT-02` once for the demo's existing three-live-run acceptance check. These replace the earlier unstructured `forest → fox → dancing → confetti` baseline. `WW-CAT-03` and `WW-CAT-04` are named alternatives for targeted tests or an explicitly chosen variation; record any substitution. Respect the existing session-attempt and spending limits.

For every scenario run:

1. **Category form:** verify the assigned category, instruction, and matching example answer are visible. Live answers remain editable until accepted; examples do not submit themselves. Apply the existing 1–120-code-point validation and ownership checks. Keep separate empty, over-limit, punctuation, and non-ASCII cases from the game specification.
2. **Private collection:** have players submit independently, including in a different order from the reveal. Only participation progress is public during collection; accepted answers remain locked and private.
3. **Ordered additions:** review Character, then Action, then Scene change after the theme is established. Each addition must become recognizable at its own reveal; later answers must not appear early.
4. **Continuity:** check the setting, character identity, distinctive details, and action after every update. A missing crown, replacement character, lost action, or unrelated scene is a failed visual criterion even if the command succeeded. Intended changes such as floating furniture are allowed; earlier facts must remain recognizable where compatible.
5. **Result and replay:** verify the exact accepted answers, categories, and contributors appear in order. For the current demo, replay all four saved segments after closing the provider session without generating again.
6. **Record evidence:** complete the record below with actual observations and media timestamps. A pending or failed scenario must not be presented as a verified success. A clearly labelled fixture rehearsal tests the app flow; only actual generated output can establish live visual quality.

Keep the rest of the [demo acceptance checks](game-spec.md#8-demo-acceptance), including timeout, refresh, duplicate actions, hidden media, and cleanup. These scenarios supply repeatable story inputs for those checks.

## 6. Reusable result record

Save dated results in the [research directory](../../research/word-by-word/). Record only these agreed test inputs and relevant observations; exclude credentials and player session cookies.

```text
Date / tester:
Fixture version: categories-v1
Scenario ID / repeat number:
Flow: three-role evaluation / three-player demo / four-player demo
Mode: live / fixture
Model / version / SDK / rendering preset / seed, if used:
Starting image reference, if used:
Theme and exact category answers / any deviation:
Player-to-category assignments:
Category instructions and examples visible: pass / fail / not tested
Submission privacy, ownership, locking, and reveal order: pass / fail / not tested
Place/setup: expected effect / observed effect / media timestamp
Character: expected effect / observed effect / media timestamp
Action: expected effect / observed effect / media timestamp
Scene change: expected effect / observed effect / media timestamp
Earlier details retained or lost after each update:
Startup / per-step generation and capture time / time to visible change:
Transition stalls or unexpected cuts:
Provider closure / billable duration / actual cost:
Saved media reference / replay after closure:
Overall: pass / fail / partial / not run
Follow-up:
```
