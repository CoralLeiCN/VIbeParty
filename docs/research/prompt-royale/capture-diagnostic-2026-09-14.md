# Prompt Royale capture diagnostic — 14 September 2026

The user requested verification of whether Helios returned frames or the application
failed to capture them. One Helios attempt was run at 20:38 UTC, with a 60-second
session cap and no retry. The live app was stopped after confirming no party was active.

## Observed result

| Measurement | Result |
| --- | --- |
| Model | `reactor/helios`, default 2x scale |
| Connection ready | 16.923 seconds |
| First decoded frame | 19.519 seconds |
| Frames received | 735 |
| Frames with timestamp 0 | 735 |
| Frames with nonzero timestamps | 0 |
| Model events | Prompt accepted, generation started, 23 chunks completed |
| Failed stage | Waiting for six seconds of frame timestamp progression |
| Capture elapsed, including closure | 60.946 seconds |
| Recording requested | No; the frame gate was never satisfied |
| Saved playable clips | 0 |
| Independent provider closure | Confirmed |
| Actual spend | Not measured |

This reproduces a concrete capture bug: the frame callback receives video, but only
nonzero sender timestamps advance the capture gate. With every timestamp zero, the
gate never opens and the 60-second timeout fails the entry before recording is requested.
It does not establish which failure occurred in the earlier room, whose errors were
not retained, but it reproduces the reported symptom with recorded evidence.

This diagnostic adds frame counters, stage names, exception types and closure results;
it does not change the capture gate or establish recording/download/MP4 readiness.
Each attempt now retains a private JSON record outside disposable room clips, and
failed attempts emit a server warning. Prompts, credentials, recording URLs and raw
provider payloads are excluded.

## Local evidence

- `.local/vibeparty/prompt-royale/spike/20260914T203828Z-d91caf17/evidence.json`
- `.local/vibeparty/prompt-royale/diagnostics/0748c5f075294ee88057c90db07c9181.json`

Verification: all 61 Prompt Royale backend tests passed, including new cases that
distinguish no frames, zero-timestamp frames, recording failure and preparation failure,
and check that diagnostics exclude credentials and prompts. Ruff checks passed for
the changed Python files.
