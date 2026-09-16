# FastH3 frame loss investigation — 15 September 2026

**16 September correction:** A hosted session advertises `set_flush_on_clip_end`,
which current documentation describes as choosing black versus a held final frame.
The earlier claim that no client control existed was too broad. A subsequent
[four-session comparison](flush-control-live-test-2026-09-16.md) received 158
non-black callbacks in both disabled runs, versus 155/156 with it enabled, after
allowing late frames. This supports a small tail benefit, not a guarantee of complete
source-frame delivery. Recording downloads still remained HTTP 202; see the
[recording observations](repeat-download-2026-09-16.md).

The published FastH3 server code has a reproducible end-of-clip truncation path.
An offline run using its actual `_play_clip` and `_emit_clip` methods plus the
unmodified Reactor runtime 3.2.6 media pacer submitted 158 numbered frames but
delivered only 156. The final two were still queued when FastH3 called `flush()`.
Waiting for the output sink to receive all frames before the normal finish flush
delivered all 158. This test used no GPU or network.

This establishes a defect in the inspected source/runtime combination. It does
not establish which revision Reactor hosted during our earlier game runs or prove
that the same defect caused every missing frame in those runs.

**Follow-up live test:** Three subsequent sessions observed video through two
seconds after `clip_finished`. Waiting recovered one content frame in two trials
and none in a run with only 53 content callbacks. See the
[live test results](frame-drop-live-test-2026-09-15.md) for the separate evidence,
including why packet loss alone does not establish the large-drop cause.

## Offline reproduction

| Case | Generated | Delivered to pacer sink | Queued at flush | Missing frames | Elapsed |
| --- | ---: | ---: | ---: | --- | ---: |
| Published immediate flush | 158 | 156 | 2 | 157, 158 | 6.655 s |
| Wait for delivery before normal finish | 158 | 158 | 0 | None | 6.735 s |

The pacer's overflow counter was zero in both cases. Runtime 3.2.6 `flush()` empties
the queue without incrementing that counter. Zero overflow cannot rule out this loss.

The reproduction loads the two FastH3 methods directly with Python's AST. Tiny,
numbered RGB frames replace generation; an in-memory callback replaces the WebRTC
sink. The actual pacer and its value types run unchanged. The second case adds a
bounded wait for all sink callbacks before the original finish/flush path continues.
It demonstrates the drain requirement, not a deployed fix or complete WebRTC delivery.

Artifacts are in `.local/reactor-frame-drop-review/`: `reproduce.py`, `results.json`
(including source SHA-256), and the inspected `fasth3.py`, `reactor.yaml`, `pacer.py`
and `values.py`. Run with `.venv/bin/python .local/reactor-frame-drop-review/reproduce.py`.

## Separate evidence: substantial loss during delivery

The [earlier isolated probe](retest-2026-09-15.md) received 27 callbacks and captured
26. Playback samples showed approximately 17.5–22.6% video packet loss, 235–249 ms
round-trip time, jitter reaching 665 ms, and 106 NACK requests. The final sample had
only 25 decoded frames. No application queue overflow was recorded.

These measurements establish substantial impairment along the media delivery path.
They do not locate it to the laptop network, intermediate route or Reactor's sender.
The reproduced two-frame truncation is insufficient to explain only 27 callbacks.

Our adapter also stops accepting frames at `clip_finished`. That message travels
separately from video and does not acknowledge local frame receipt. The probe's last
callback arrived about 2 ms after finish. Its pixels were not retained and source
metadata was absent, so we cannot determine whether it was useful video or the
server's black boundary frame. Blindly accepting late callbacks could add black
frames or media from another playback.

## Fixes by layer

1. **Reactor/FastH3 server:** drain output with a bounded deadline before clearing the
   stream and declaring normal playback finished. Include in-flight delivery, not
   just an empty queue check. Keep immediate flushing for explicit stop/reset.
   A later hosted session exposed `set_flush_on_clip_end`, but its advertised
   last-frame hold is not a verified delivery barrier. Waiting in our app cannot
   undo frames already discarded on the server.
2. **Frame identity and capture:** tag emitted frames with clip ID, source index and
   timestamp. Then accept delayed matching frames until the expected count or a
   bounded deadline, while excluding duplicates and black boundary frames.
3. **Transport:** compare sender packet/frame/drop counters with receiver statistics
   for the same session, then compare another network or host. This can localize
   the loss before changing the route, relay, encoder load or bitrate. No specific
   cause among those has been established.
4. **Complete-file delivery:** enable server recording or an export endpoint and
   download the finished clip over HTTP. Recording is disabled in the inspected
   FastH3 manifest. This requires the hosted model owner or a controlled deployment.

The [hold-last-frame fallback](tolerant-capture-2026-09-15.md) lets the game finish
with choppy clips. It does not recover source frames or fix transport loss.
This investigation changed no application behavior, restarted no service, created
no provider sessions and sent no report to Reactor.

Sources: [FastH3 source](https://github.com/reactor-team/infinite-livestream/blob/main/fast-h3/fasth3.py),
[runtime 3.2.6](https://pypi.org/project/reactor-runtime/3.2.6/),
[runtime output documentation](https://docs.reactor.inc/deploy/development/reactor-model/run-loop),
[FastH3 manifest](https://github.com/reactor-team/infinite-livestream/blob/main/fast-h3/reactor.yaml),
and [recording documentation](https://docs.reactor.inc/concepts/recordings).
