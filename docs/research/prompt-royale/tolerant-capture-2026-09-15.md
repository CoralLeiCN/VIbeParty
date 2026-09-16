# FastH3 capture tolerates missing frames — 15 September 2026

**Superseded on 16 September:** The user approved shorter clips. Capture now encodes
received frames once at 24 fps without padding; see the
[shorter-clip change and verification](shorter-clips-2026-09-16.md). The results below
describe the earlier image-hold policy.

Prompt Royale now accepts choppy clips. The user confirmed that smooth motion is
unnecessary for this game. A new three-player live round passed through generation,
arena playback, voting, a winner, play again and room cleanup.

## Cause and change

The [earlier retest](retest-2026-09-15.md) observed completed FastH3 playback but only
9–32 received frames per attempt. The adapter treated every frame as 1/24 second and
required 120 received frames. It therefore rejected all entries, even though the
received images could have been shown as a choppy five-second clip. The earlier
[Word by Word capture notes](../word-by-word/capture-buffering.md) also documented
frame-count and buffering failures; that game's policy is separate.

The new Prompt Royale policy:

- Capture only between the requested clip's matching start and finish events.
- Start the timeline at the first received image. Use receiver arrival times because
  SDK sender timestamps may all be zero.
- Hold each image until the next arrives, and the last image through the end of the
  five-second output. Encode a normal 24 fps MP4 with repeated images across gaps.
- Require a completed playback and at least two valid received frames in the capture
  window. Empty, single-frame, failed and unfinished captures remain unavailable.
- Keep the bounded frame queue, generation deadline, retry allowance and independent
  session closure. Delete partial source files on encoding failure or cancellation.

This removes the game's unnecessary smoothness requirement. It does not repair the
network packet loss seen in the earlier probe. Diagnostics now distinguish received
and captured frames, source images used in output, and repeated output frames.

## Verification

`make check` passed: **213 backend tests**, Ruff and formatting, frontend lint and
build. The updated browser-test attachment code also passed scoped ESLint.

Nine FastH3 regression cases use native-thread synthetic BGRA frames and real FFmpeg.
Successful cases include normal playback, 40-frame short playback, four images arriving
at 0/0.5/2/4 seconds, and two images arriving at 0/4 seconds. All produce a five-second,
120-frame silent MP4. Decoded color samples verify that gaps hold the preceding image
at the correct time and exclude idle frames. Other cases verify command rejection,
generation failure, zero/one-frame rejection and cancellation before playback finishes,
including partial-file removal and confirmed provider closure.

The live browser test passed in about 96 seconds in **room 4793** with three separate
browser contexts, including a 390-pixel phone viewport. It verified:

- Host presence while the document was hidden for 35 seconds.
- Three real five-second clips playing together and looping without media errors.
- Three votes and a scored winner: Bailey, with two votes.
- Play again, room closure and retirement of the old join code.

The live connection received frames at a healthy rate on this run. Severe frame loss
was exercised by the synthetic capture regressions, not reproduced by this live run.
Desktop and phone result screenshots were visually inspected.

| Attempt | Received | Captured in first five seconds | Source images used | Repeated output frames | Total seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| `7b85253dbb6c4222afcdfbd92178f810` | 154 | 123 | 111 | 9 | 22.981 |
| `ea90ae60a60e4acd80a4f495a300a33a` | 154 | 123 | 116 | 4 | 18.468 |
| `8bb3440ed5354e3ba1caaa0a67ffde8a` | 153 | 121 | 115 | 5 | 19.869 |

More than 120 received images can land within five seconds due to delivery jitter.
Images that arrive in the same output frame slot replace the pending image for that
slot; repeated output frames represent holding an image through later slots.

All three attempts succeeded without retry. All three owned sessions were independently
confirmed closed: `b912e075-49f2-4a14-ba82-b28da7b05064`,
`74a39e34-edb1-4b0f-af2a-fbb17df7dafc`, and `2f690b21-b589-4b3f-90c3-d461f36073a2`.
The service was started with the fix at port 8000. Physical-phone and four-player live
acceptance remain outside this three-browser rehearsal.

## Retained evidence

Paths relative to this checkout:

- Full check log: `.local/prompt-royale-tolerant-capture-check.log`.
- Live browser report: `.local/prompt-royale-tolerant-live-report/index.html`.
- Three generated MP4s and arena/desktop/phone screenshots: the report's `data/` folder.
- Private capture diagnostics: `.local/vibeparty/prompt-royale/diagnostics/`, using the
  attempt IDs above. Prompts, credentials and raw provider errors are excluded.

The live test ran around 23:14 UTC on 14 September, or 00:14 on 15 September in London.
