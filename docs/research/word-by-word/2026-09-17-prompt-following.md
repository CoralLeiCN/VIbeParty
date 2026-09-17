# Word by Word: action and consequence prompt experiment

Date: 17 September 2026. Related backlog item: [WW-003](../../backlog.md#ww-003--experiment-with-prompts-for-actions-and-consequences).

Status: code inspection, provider guidance review, and retrospective frame review complete. New generation comparison: not run. No application behavior changed.

## Current prompt behavior

At commit `18b6aee`, [`scene_prompt`](../../../backend/games/word_by_word/providers.py) prepends a fixed instruction to the accepted answers through the current category. The final prompt for standard scenario `WW-CAT-01` is:

```text
Playful illustrated scene, wide fixed camera, minimal camera movement. Preserve the established setting and the same character appearance. Apply the action to the existing character. Add only the current idea. Place: Enchanted forest
Character: A fox wearing a crown
Action: Dances ballet
Consequence: Glowing snow begins falling
```

There is a general instruction connecting the action to the character, but no sentence composer or language-model rewrite. Each update retains earlier contributions and excludes future answers. The starting image uses Place only. [`LingBotProvider.run`](../../../backend/games/word_by_word/live.py) sends updates to `reactor/lingbot-world-2` about six seconds apart by default, measured against the paced captured stream. Prompt acceptance advances the category; visible realization is not checked.

Reactor describes `set_prompt` as a natural-language scene description that replaces the active prompt at a chunk boundary. Its acknowledgement establishes acceptance, not whether a requested visual effect appeared. [API reference](https://www.reactor.inc/models/lingbot-world-2/api).

The current [prompt guide](https://docs.reactor.inc/model-api-reference/lingbot-world-2/prompt-guide) recommends concrete subject references, observable action sequences, and compatible descriptions of the scene and its events. It also recommends fresh sessions when judging prompt revisions and acknowledges model limitations. This supports testing connected, concrete prose; it does not establish that this model reliably follows our game inputs. The game's gradual reveals also differ from examples that establish a character and props in the starting image. Keep future contributions out of the image and earlier prompts during this experiment.

## Retrospective review: WW-CAT-01

Source: [16 September live recording](evidence/2026-09-16-lingbot-ww-cat-01.mp4), its [timing evidence](evidence/2026-09-16-lingbot-ww-cat-01.json), and [starting image](evidence/2026-09-16-lingbot-seed.png). This is the repository's saved test, not a confirmed identification of the video the user watched. The original test deliberately excluded visual-quality evaluation.

Method: inspect the starting image and twelve timestamped video frames at 0, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, and 25 seconds. The recording contains 603 frames at 24 fps and lasts 25.125 seconds. See the [review contact sheet](evidence/2026-09-17-prompt-review.png). This samples appearance and continuity; it cannot fully establish motion between frames.

| Category | Recorded update time | Sampled observation | Assessment |
| --- | --- | --- | --- |
| Place: Enchanted forest | 0 s | The forest setting remains recognizable throughout the sampled frames. A humanoid figure appears by 6 s, before the Character update. | Setting present; unrequested subject also appears. |
| Character: A fox wearing a crown | 6.417 s | A fox-like head appears on the existing figure around 8–12 s; a crowned fox is clear by 14–16 s. Later frames show more than one fox. | Requested elements present, with identity drift and duplication. |
| Action: Dances ballet | 12.625 s | Later frames show changing fox poses and positions, but do not establish recognizable ballet. | Action unverified; no visual pass from these samples. |
| Consequence: Glowing snow begins falling | 18.917 s | No clear falling luminous snow in the 20, 22, 24, or 25 s samples. | Requested effect not evident in the sampled frames. |

Overall: partial and inconclusive for motion; this recording does not establish effective following of all four contributions. The delay before a recognizable crowned fox and the later missing effects make both wording and timing plausible factors. Neither cause is proven by this review.

## Proposed comparison

Start with three fresh `WW-CAT-01` sessions, one per prompt variant, using the exact standard answers and the same Place-only image, explicit model seed, camera instructions, capture settings, and six-second category interval. Record the actual seed and provider/model version. Reusing the image avoids adding image-generation variation. The current prompt generator remains variant A.

| Variant | Change under test | Example of the final scene text |
| --- | --- | --- |
| A — Current | Existing style instructions and cumulative category labels. | The exact prompt above. |
| B — Connected sentences | Retain the same style instructions; replace the labels with prose that binds the actor, action, and event. | A fox wearing a crown dances ballet in an enchanted forest as glowing snow begins falling around it. |
| C — Concrete motion | Retain B's structure and style instructions; expand the action and consequence into visible behavior. | A fox wearing a crown dances ballet in an enchanted forest. The fox rises onto its hind toes, extends its forelegs, and turns in a pirouette. Glowing snowflakes descend around the dancing fox, visible against the trees and above the forest floor. |

For B, assemble each stage separately: `An enchanted forest.` → `A fox wearing a crown is in an enchanted forest.` → `A fox wearing a crown dances ballet in an enchanted forest.` → the final sentence above. C uses B's first two stages, adds its motion description only at Action, and adds snow only at Consequence. These are proposed effective prompts, not new player answers or validated improvements. Preserve exact submissions on cards. Use relations such as “as” or “around”; do not invent a causal claim such as dancing causing the snow.

Evaluate the full recordings using the [standard scenario criteria and result record](../../games/word-by-word/test-scenarios.md). Record when the crowned fox, recognizable ballet, and luminous falling snow first appear, and whether the setting, character identity, crown, and ongoing action survive each update. Store the exact effective prompts, command times, any available chunk timing, saved media, closure confirmation, billable duration, and actual cost when available. Grade effects as clear, partial, absent, or unassessable. Compare videos without showing variant labels to the reviewer where practical.

The first three runs are a pilot, not a reliability result. If there is a promising variant, compare it with A for the second `WW-CAT-01` repetition and one `WW-CAT-02` run per variant, retaining that scenario's exact inputs and a shared Place-only image within each pair. Use the standard mapping: theme → Place; Scene change → Consequence. These follow-ups are a separate batch within the existing attempt and spending limits.

If effects remain late or absent, compare six versus twelve seconds per category while holding wording and all other settings fixed. Record time to the first visible effect rather than assuming command acknowledgement marks its appearance. If wording and timing changes still fail, evaluate model suitability as a separate experiment. Prompt composition is a hypothesis, not a promised fix.

Execution status: every proposed variant run is **not run**. Any live batch should be recorded in the existing [trial ledger](../../development/live-provider-slots.md), with a fixed attempt count and independently confirmed session closure. The historical saved-video review consumed no new generation sessions.
