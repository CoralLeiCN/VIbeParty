# FastH3: `set_flush_on_clip_end`

Verified against the official schema and hosted sessions on 16 September 2026.
This command controls the image shown at clip boundaries. Its required `enabled`
Boolean defaults to `true`: the stream returns to black. Setting it to `false`
keeps the last image visible. The hosted comparison also found more content frames
arriving at normal completion when flush was disabled.

## Documented behavior

| Situation | `enabled: true` (default) | `enabled: false` |
| --- | --- | --- |
| A clip finishes normally | Return to black until another clip plays. | Keep the completed clip's last image visible. |
| `stop` interrupts a clip | Return to black; with autoplay enabled, the next ready clip can start. | Keep the stopped clip's last image visible until another clip starts. |
| A clip is followed by an unrelated clip | Use a black boundary between clips. | Retain the preceding image across the boundary. |
| Autoplay advances into a clip whose `continue_from_clip_id` names the current clip | Seamless continuation. | Seamless continuation. |

The continuation case is built to begin on its source's last frame, so the flush
toggle does not determine that transition. A fresh session starts with black output
and flush enabled. `reset` clears the queues and history, interrupts playback, and
restores all session defaults, including flush. Reapply and verify the desired
setting after a reset.

Turning flush off does not undo an explicit stop: the documented `stop` behavior
discards the remaining buffered transport content. A held image does not imply
continued generation, replay, or delivery of the rest of a stopped clip.

These cases are specified in the [official FastH3 schema](https://docs.reactor.inc/model-api-reference/fast-h3/schema).
Our live comparison exercised **normal completion only**. Stop, reset and linked
continuations were not tested in that comparison.

## Send the command and verify it

Use a connected, ready Python SDK `reactor` instance. For a capture session, set the
value before enqueueing and playing its clip:

```python
state_reply = await reactor.send_command("get_state", {})
if "set_flush_on_clip_end" not in state_reply["data"]["valid_commands"]:
    raise RuntimeError("This session does not currently accept the flush command")

reply = await reactor.send_command("set_flush_on_clip_end", {"enabled": False})
if reply.get("type") != "flush_accepted":
    raise RuntimeError("FastH3 did not accept the flush setting")

state_reply = await reactor.send_command("get_state", {})
if state_reply["data"].get("flush_on_clip_end") is not False:
    raise RuntimeError("FastH3 did not confirm flush was disabled")
```

Use `{"enabled": True}` to restore the default. `flush_accepted` confirms the command;
`state_update.data.flush_on_clip_end` reports the current value. A rejected command
produces `command_error`. The example shows the command exchange; callers still need
their existing command timeouts and session cleanup. These are model messages and
state fields, separate from the SDK's connection `status_changed` event.

## Observed normal-completion behavior

Four hosted sessions used the same prompt, seed and six-second request, in the order
on, off, off, on. The provider accepted 6.583 seconds, implying about 158 frames at
24 fps. Each run generated a new clip; this was not repeated playback of one object.
An observer stayed attached for two seconds after the matching `clip_finished`.

| Setting | Non-black callbacks across two runs | Non-black callbacks after `clip_finished` | Black boundary observed |
| --- | --- | --- | --- |
| Enabled | 155 and 156 | 2 in each run | Yes |
| Disabled | 158 and 158 | 4 in each run | No |

With flush disabled, the final callback arrived 138.2 ms and 151.9 ms after
`clip_finished`. No further callbacks arrived during the rest of the observation
window; holding the final image did not produce an ongoing series of duplicate
callbacks. All sampled video loss counters were zero. All four sessions closed
successfully. See the [live test report](../../research/prompt-royale/flush-control-live-test-2026-09-16.md)
for timings, receiver statistics and retained evidence.

This supports disabling flush to reduce truncation at normal completion. It does
not prove that every unique generated frame arrived: frame IDs and timestamps were
zero and metadata was absent. Distinct decoded image hashes are not source-frame
identities. The result also does not explain earlier severe losses under different
delivery conditions. The 152 ms observed tail is not a guaranteed upper bound.

The setting does not establish a complete-file download path. Recording requests
were accepted with both values, but all four excerpt downloads remained HTTP 202
until their ten-second deadlines. Transport smoothing was not changed in this
comparison; `set_flush_on_clip_end` controls clip boundaries.

## Prompt Royale integration status

The current [adapter](../../../backend/games/prompt_royale/fast_h3.py) does not send
this command, so it uses the provider's default. It stops accepting frames at the
matching `clip_finished` and saves each accepted image once at 24 fps, capped at
120 images. At least two images are required; fewer than 120 produce a shorter clip.

To use the tested tail benefit, a future adapter change must both disable flush and
retain the frame handler for a bounded interval after normal `clip_finished`.
Keep that interval within the existing session and round deadlines, preserve the
output cap and shorter-clip fallback, and end promptly on cancellation or stop.
Turning the setting off alone cannot recover late callbacks after the handler has
detached. Complete source-frame accounting would additionally need reliable frame
identity or a verified complete recording.

The two-second grace was a diagnostic choice. It has not been added to game capture,
and this documentation update changes no runtime setting.
