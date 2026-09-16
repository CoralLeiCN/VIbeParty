# Hosted FastH3 flush comparison — 16 September 2026

For the command contract, stop/reset/continuation behavior and integration status,
see the [FastH3 flush behavior reference](../../games/prompt-royale/fast-h3-flush-behavior.md).

Disabling `set_flush_on_clip_end` improved the observed end of the stream in both
live comparisons. With the default enabled, the observer received 155 and 156
non-black frame callbacks before the stream cut to black. With it disabled, both
runs received 158 non-black callbacks, matching the frame count implied by the
accepted 6.583-second duration at 24 fps. Four callbacks arrived after
`clip_finished` in each disabled run.

This supports end-of-clip flushing as a cause of a small tail deficit on these
connections. It does not establish why earlier sessions delivered only 9–53 frames,
nor guarantee complete source-frame delivery under impaired network conditions.
The change was tested in isolated diagnostic sessions; the game adapter was not
modified by this experiment.

## Method

Four sequential sessions ran in the order on, off, off, on. Every session used one
new generation with the existing fixed penguin scene, seed 42 and a six-second
request. All were accepted at 6.583 seconds. These are separate generations with
matching inputs, not four replays of the same generated object.

Before enqueueing, the probe sent the explicit boundary setting, required
`flush_accepted`, and read `get_state` again to verify the requested Boolean. State
after playback also confirmed the setting. Autoplay was disabled. This command is
separate from transport smoothing; the experiment did not configure smoothing.

The ordinary game capture ran alongside an observer that continued through two
seconds after the matching `clip_finished` message. The observer retained callback
timing, small image hashes, black-frame classification and one-second receiver
statistics. Contact sheets of the last four frames before finish and all subsequent
frames were visually inspected in all four runs. Sampling work in the native frame
callback took at most 0.568 ms. Encoding the contact sheets happened after detaching
that observer.

## Frame results

The counts below are non-black decoded-frame callbacks. They are not verified
source-frame identities.

| Run | Flush | Before finish | After finish | Total non-black | Black after finish | Last non-black arrival after finish |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | On | 153 | 2 | 155 | 1 | 32.7 ms |
| 2 | Off | 154 | 4 | 158 | 0 | 138.2 ms |
| 3 | Off | 154 | 4 | 158 | 0 | 151.9 ms |
| 4 | On | 154 | 2 | 156 | 1 | 37.8 ms |

With flush enabled, black arrived at 76.9 and 82.5 ms after finish. With it disabled,
the final content image remained and no further callbacks arrived between the last
reported frame and the end of the two-second observation window. There was no
ongoing stream of repeated held-frame callbacks. All non-black sample hashes were
distinct within each run, including the late samples, and contact sheets showed
content rather than black in the disabled runs.

Every callback still had frame ID zero, timestamp zero and no metadata. Different
decoded image hashes can reflect lossy compression as well as different source
frames. Therefore 158 callbacks and 158 distinct sampled hashes are evidence of
matching the expected count, not proof of receiving every unique generated frame.

| Run | Video packets received | Reported lost packets | NACKs | Decoded frames | Decoder-reported drops | Final jitter |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 5,558 | 0 | 0 | 157 | 0 | 17 ms |
| 2 | 5,321 | 0 | 0 | 158 | 0 | 18 ms |
| 3 | 5,714 | 0 | 0 | 158 | 0 | 18 ms |
| 4 | 5,204 | 0 | 0 | 157 | 0 | 19 ms |

All sampled video streams reported zero lost packets. Decoder counters cover the
connection, including possible early frames and black markers, so they need not
equal the content observer count. These receiver statistics do not expose frames
that were never submitted by the sender.

## Recording result

Each session also requested one fixed two-second excerpt, three seconds after its
first non-black playback frame. After the tail observation, the probe attempted one
download with a ten-second deadline. All four requests were accepted, but each
download received four HTTP 202 responses and timed out. No playlist reached 200
and no server media file was downloaded.

Disabling flush did not make server recording available within this tested window.
This remains distinct from local capture: every run produced a validated five-second
H.264 game MP4 containing 120 received frames, with no recorded application queue
overflow. The game caps output at five seconds, so these local MP4s do not contain
the complete 6.583-second generated clip or the observer's late tail.

## Implication for capture

The tested combination is `set_flush_on_clip_end` with `enabled: false` **and**
continuing to observe briefly after `clip_finished`. Switching the boundary setting
alone cannot make an adapter that detaches at `clip_finished` collect the four late
frames. A bounded grace period is required to use this observed benefit. The
two-second diagnostic window worked here; the latest content arrived after about
0.15 seconds, which is not a general delivery deadline guarantee.

The game currently stops capture at `clip_finished` and retains its shorter-clip
acceptance policy. This experiment recommends the disabled boundary setting plus
bounded late capture as a follow-up implementation. It does not replace that
fallback or establish a reliable full-video export.

## Evidence and cleanup

Each session had a provider-enforced 60-second cap and independent closure
verification before the next session started. All four were confirmed closed; the
unresolved-provider marker was absent afterward. No service restart or production
setting change was needed. No report was sent externally.

| Run | Session ID | Lifecycle | Evidence directory under `.local/vibeparty/prompt-royale/spike/` |
| --- | --- | ---: | --- |
| 1 | `f8299fd4-4ab7-46a1-a31c-a12fe331a705` | 30.989 s | `20260915T234352Z-7a90f39f` |
| 2 | `c4a0e9c6-4f39-41be-8aea-a1ca1f6d6cff` | 35.927 s | `20260915T234435Z-2d4e5cd5` |
| 3 | `5252b8c0-73a2-471c-9906-ff3eb9e3b7a3` | 30.976 s | `20260915T234531Z-f03c1823` |
| 4 | `e44898c2-b82f-4a0e-bf5b-ac5bc1be972c` | 31.509 s | `20260915T234613Z-6199f3bb` |

Each directory contains `evidence.json`, `tail-contact-sheet.png` and the normal
`clip.mp4`. The local diagnostic, logs and combined summary are in
`.local/reactor-flush-probe/`; the probe reuses `.local/reactor-tail-probe/probe.py`.
UTC timestamps fall on 15 September; the local London date was 16 September.
The diagnostic compiled successfully and all four media validations passed.

The [official FastH3 schema](https://docs.reactor.inc/model-api-reference/fast-h3/schema)
documents the boundary control as black versus a held final image. The
[previous repeated-download report](repeat-download-2026-09-16.md) records its
discovery and corrects the earlier claim that no client control existed. The
[offline flush reproduction](frame-drop-root-cause-2026-09-15.md) remains evidence
about the inspected public source/runtime combination; it is not direct inspection
of the implementation running in these hosted sessions.
