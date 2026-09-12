# VibeParty — VEED generation inputs

Target: **2:00**, landscape 16:9. The transcript is **268 words**, approximately two minutes at **134 words per minute including pauses**. Final duration depends on the generated speech; preview and adjust pace or pauses so the assembled video ends at 2:00.

## Inputs

- `presenter.png`: original fictional clay-style presenter, created with the built-in image generator for this demo; 1672 × 941 pixels. Use this same image for every clip.
- `transcript.txt`: full narration, with no production notes to be read aloud. “Vibe Party” is the spoken spelling of VibeParty.
- Four numbered text files: narration split at topic boundaries for separate generations.

## Delivery

Warm, clear, conversational English. A friendly game host, with light excitement at each reveal. Use the same voice for all clips. Start around 134 words per minute, allow natural sentence pauses, and avoid exaggerated announcer delivery. Keep the camera steady and the presenter's face unobstructed.

## Suggested edit timing

These are target edit windows, not measured generated durations.

| Target time | Section | Narration file | Words |
| --- | --- | --- | ---: |
| 0:00–0:29 | Welcome and joining | [01-intro.txt](01-intro.txt) | 64 |
| 0:29–0:59 | Word by Word | [02-word-by-word.txt](02-word-by-word.txt) | 68 |
| 0:59–1:27 | Prompt Royale | [03-prompt-royale.txt](03-prompt-royale.txt) | 62 |
| 1:27–2:00 | Reverse Prompt and closing | [04-reverse-prompt-and-close.txt](04-reverse-prompt-and-close.txt) | 74 |

## Generate

1. In VEED, create the spoken audio from each numbered transcript, using one voice and consistent pacing. Preview the pronunciation of the three game names.
2. For each Fabric generation, use `presenter.png` and the corresponding audio. Fabric takes an image and audio; it does not take the transcript directly at the fal endpoint.
3. Join the four clips in order in the VEED timeline. Set the final video to 16:9, add captions if desired, and adjust speech timing and pauses to finish at exactly 2:00.

[VEED's Fabric API documentation](https://support.veed.io/en/articles/15230480-veed-fabric-1-0-api) specifies a maximum of one minute per API call. These four short sections stay comfortably within that limit. [Requested model](https://fal.ai/models/veed/fabric-1.0).

## Source accuracy

The narration follows the project's README and game descriptions. The forest, fox, breakdancing and confetti sequence comes from the existing Word by Word sample fixtures. The script identifies the current demo's labelled sample rounds. It does not claim that footage was generated live in this task.

No video or audio generation has been run on VEED or fal; these files are the inputs for that step.
