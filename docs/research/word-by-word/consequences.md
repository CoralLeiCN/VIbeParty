# Word by Word: Consequences reference

Status: reference note recorded on 12 September 2026. Consequences is the founder-selected reference. The [hackathon game specification](../../games/word-by-word/game-spec.md) resolves the adaptation's rules, and the [technical plan](../../games/word-by-word/tech-stack.md) selects its simplified implementation. Those documents take precedence over illustrative examples here. See the [before-and-after comparison](../../games/word-by-word/simplification.md).

## Confirmed direction

- Use the traditional party game **Consequences** as the main gameplay reference.
- Players contribute words, phrases, or short sentences that combine into a shared story.
- The experience is a video, with each contribution making an additive change to the scene. Each contribution should have a visible effect, and the scene should retain what earlier contributions established.

## How the reference game works

In the written version of Consequences, players contribute successive story elements on paper, fold their writing out of sight, and pass the paper to the next person. A common sequence supplies characters, a meeting place, what they say or do, and the resulting consequence. At the end, the paper is unfolded and the story is read aloud. The surprise comes from combining contributions that were written without knowing the whole story. [Consequences rules, h2g2](https://h2g2.com/entry/A758496).

There are variants: John Jay Homestead describes a version where each player writes a sentence and leaves only its ending visible to the next player, as well as a drawing version. Complete secrecy is therefore a choice for our adaptation, not a rule shared by every version. [John Jay Homestead activity sheet](https://johnjayhomestead.org/wp-content/uploads/Consequences.pdf).

The reference supplies three useful ideas: an assigned contribution, limited knowledge of others' contributions, and a shared reveal. The generated, evolving video is VibeParty's proposed adaptation of that reveal.

## Proposed adaptation

1. Assign each player a category: place, character, action, or consequence. Show a plain-language instruction and an example on their phone. Accept a word, phrase, or short sentence, with a 120-character demo limit per contribution.
2. Collect each player's contribution privately. Players see their own category and answer; the shared display shows participation progress. Collecting simultaneously is a digital adaptation of passing folded paper.
3. Lock accepted contributions, preserving the submitted text after trimming. Categories guide the idea without requiring a particular grammatical form. Show contributions as ordered story cards, with their category labels, rather than inserting whole sentences into a sentence template.
4. Reveal the contributions in sequence through one evolving video. Each reveal introduces the full contribution and its visible effect, while retaining the established characters, setting, and additions. Keep later contributions hidden, including in generated imagery, until their reveal.
5. Finish with the complete story cards, contributor names, and a replay of how the video developed. Keep the existing cooperative, unscored direction for now.

The demo specification selects private collection before the reveal to preserve the surprise of Consequences. Submitting after watching a video change is a later experiment.

### Illustrative round

| Assigned category | Player contribution | Intended reveal |
| --- | --- | --- |
| Place | a moonlit forest | Establish the forest scene. |
| Character | a fox in a tiny hat | Introduce the fox in the forest. |
| Action | They start breakdancing. | The fox begins breakdancing. |
| Consequence | Confetti rains from the sky. | Confetti falls around the same dancing fox. |

The final story displays these four contributions in order with their category labels and contributor names. This is our example, not a traditional Consequences script. The demo fixes this category order before collecting answers.

## Decisions recorded in the demo specification

- **Playback:** privately build four connected Reactor FastH3 segments, then let the host reveal one addition at a time on a shared screen. Each step targets approximately six seconds.
- **Contribution timing and size:** private collection before generation; a word, phrase, or short sentence per assigned category, up to 120 Unicode code points after trimming; one or two contributions per player.
- **Story structure:** place, character, action, consequence across three or four players; 45-second collection, without timer extensions.
- **Continuity and recovery:** maintain cumulative scene facts and predecessor conditioning; stop at a failed step and allow the saved valid prefix to play. Provider cleanup runs separately and blocks another live session until closure is confirmed.

The earlier visible-sentence flow, two-sentence default, immediate word disclosure, and single final generation are superseded. Provider access, capture, continuity, latency, and cost still need live verification; that uncertainty is separate from the now-specified gameplay rules.

See the [portal specification](../../portal-spec.md) for party entry and navigation and the [Word by Word technical stack](../../games/word-by-word/tech-stack.md) for demo implementation planning.
