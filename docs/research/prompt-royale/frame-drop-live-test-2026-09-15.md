# FastH3: testing delayed frame capture — 15 September 2026

Three live trials show that waiting two seconds after `clip_finished` can recover
one additional content frame. It did not recover a complete clip or repair the
large frame deficit in the second trial. Every session was independently confirmed
closed. This experiment changed no game capture behavior.

## Method

Each trial used one new, 60-second-capped `reactor/fast-h3` session, the existing
standalone spike's fixed penguin prompt, seed 42, and a six-second request. FastH3
accepted 6.583 seconds, corresponding to 158 expected frames at 24 fps. Trials ran
sequentially on the same computer and connection, with no retries.

An additional lightweight raw-frame observer watched the entire playback and
remained registered until two seconds after the matching `clip_finished`. This
provides a paired comparison within each playback: what had arrived at finish and
what arrived during the extra wait. The ordinary game adapter still produced its
existing five-second MP4. Its 120 output frames include repeated images and are
not evidence that all source frames arrived.

The observer recorded callback times, small pixel samples and sample hashes. It
performed no full-frame hashing, encoding or disk writes on the media thread.
Maximum observer callback time was 2.10 ms, 0.74 ms and 0.35 ms across the trials.
Receiver transport statistics were sampled every second and at the end. These
are receiver statistics; the hosted server's sender counters were unavailable.

## Results

Counts below exclude the black end marker. They count decoded content callbacks,
not verified unique source indices: all frame IDs and timestamps were zero, and
no source metadata was present.

| Trial | Content by finish | Extra content during wait | Total content observed | Extra black markers | Peak video packet loss | Final video packet loss |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 154 | 1 | 155 | 1 | 0% | 0% |
| 2 | 53 | 0 | 53 | 1 | 2.17% | 0.60% |
| 3 | 155 | 1 | 156 | 1 | 0% | 0% |

In trials 1 and 3, the extra content arrived 22.38 ms and 10.95 ms after finish.
Each had a pixel-sample hash not seen earlier in that playback, and its thumbnail
showed the penguin scene. Black end markers arrived 65.54 ms, 19.58 ms and 54.15 ms
after finish. No further video callbacks arrived in the remaining observation
window, which exceeded two seconds in every trial.

All three tail contact sheets were visually inspected. The second trial's black
marker had compression noise: sample maximum 20/255 and mean 1.377/255. The first
two raw evidence files used a maximum-only black threshold of 12, which incorrectly
marked that callback as nonblack. The derived report corrects this using maximum
<= 24 **and** mean <= 3, together with visual inspection. Original evidence is
preserved. The second trial recovered zero content frames, not one.

| Trial | Final decoder count | Reported decoder drops | Video packets received / lost | Video bytes received | Maximum video jitter | Application queue overflows |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| 1 | 157 | 0 | 4,831 / 0 | 5,262,524 | 15 ms | 0 |
| 2 | 55 | 0 | 332 / 2 | 323,461 | 175 ms | 0 |
| 3 | 157 | 0 | 4,953 / 0 | 5,397,834 | 24 ms | 0 |

Decoder counters cover the whole connection, including any frames before the
observer registered and black markers. They cannot be equated directly to source
content counts. Peak packet loss is calculated only from samples with an inbound
video stream; earlier audio-only summary samples are excluded.

## What this establishes

1. **Late content is real.** Ending capture at `clip_finished` can discard useful
   video that arrives just afterward. Two of three trials directly observed this.
2. **Extra waiting is insufficient for complete delivery.** It recovered at most
   one content callback here. Trial 2 stayed at 53 content callbacks after the full
   grace period; even the decoder reported only 55 total frames. The large deficit
   therefore cannot be explained by the application ending capture early or
   overflowing its frame queue.
3. **Packet loss alone is not an established explanation for the large deficit.**
   Trial 2 received far less video data and only 55 decoded frames despite two
   reported lost video packets, two NACKs and zero reported decoder drops. Sender
   adaptation or drops before packet transmission are plausible, as are other
   transport/decoder effects; receiver evidence cannot select the cause. We need
   sender frame, encoder, bitrate and packet counters for the same session.
4. **The server flush hypothesis remains distinct.** The earlier
   [offline reproduction](frame-drop-root-cause-2026-09-15.md) established that the
   published FastH3/runtime combination discards queued tail frames. Today's live
   counts are compatible with that defect, but do not prove the hosted revision
   or identify which source frames were lost. This experiment did not change the
   hosted model's flush behavior.

The next complete-delivery fix needs a bounded server output drain plus source
frame identity, or a server recording/export path. A client grace period alone
would accept black markers unless frames can be attributed to the clip. The
current game also intentionally selects the first five receiver seconds from a
longer clip; these late tail callbacks do not restore missing motion inside that
five-second window.

## Artifacts and cleanup

Local diagnostic code: `.local/reactor-tail-probe/probe.py`. Derived analysis:
`.local/reactor-tail-probe/summarize.py` and `results.json`.

| Trial | Spike directory | Session ID | Elapsed including preparation | Closed |
| --- | --- | --- | ---: | --- |
| 1 | `20260915T200313Z-72ad6ad3` | `7d959c53-ece8-4e79-9a5d-e7c453adfb7d` | 21.591 s | Yes |
| 2 | `20260915T200401Z-f141c91f` | `8cea5323-0556-4c16-9b9e-edba7bae2d89` | 24.159 s | Yes |
| 3 | `20260915T200506Z-a87b3261` | `a9627f3d-d688-4064-9a9b-73bd04ca0e77` | 26.527 s | Yes |

Directories are under `.local/vibeparty/prompt-royale/spike/`. Each contains
`evidence.json`, a five-second `clip.mp4`, and `tail-contact-sheet.png`. Contact
sheets show the last four callbacks before finish, then every late callback;
blue bars identify pre-finish thumbnails and red bars identify post-finish ones.

All three prepared clips passed media validation, with 120 output frames each.
The existing hold-last fallback supplied 4, 81 and 2 repeated output frames,
respectively. This was a provider capture experiment, not another full game round.
The unresolved-provider marker was absent after cleanup. No service was restarted
and no report was sent externally.
