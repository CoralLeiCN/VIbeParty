# Live mode enabled, 12 September 2026

The user requested enabling Reverse Prompt after the earlier pause in live trials.
The playing host can select **Live · MiniMax FastH3 & local scoring** when creating
a party. This still uses the existing provider, three players, local scoring,
30-second relay turns, and session cleanup.

The primary checkout and this task's private `.env` now set
`REVERSE_PROMPT_LIVE_ENABLED=true` and share the quota at
`/Users/coral/repos/VIbeParty/.local/vibeparty-persistent/reverse-prompt/quota.json`.
The pinned MiniLM model is in that checkout's persistent model directory. The
quota lives outside disposable clips and Codex worktrees.

The original quota file was lost when integration worktree `5a4f` was removed.
Its balance was reconstructed from the saved [Reverse001](evidence/2026-09-12-reverse-001.json)
and [Reverse002](evidence/2026-09-12-reverse-002.json) evidence: two consumed and
independently closed attempts, seven remaining, no unresolved session. The
recovered entries explicitly record that the original attempt and session IDs
are unavailable; their IDs identify the evidence slots. This is a reconstruction
of the recorded balance, not a recovered byte-for-byte copy. No new allowance
was added. Future worktrees must use this same file.

The pinned scorer passed its socket-disabled load, validation and scoring check
with scores `[100, 82]`. Enabling the flag and entering a live round do not create
a provider session; generation begins when author A submits the first scene.
Full live relay and physical-phone acceptance remain unverified.

Verification: all 63 Reverse Prompt backend tests passed. On the restarted
`http://localhost:8000` app, the browser created a live room, two independent API
clients joined, and the host's Start round action reached **The original idea**
with an editable scene field. Both guest snapshots reported `start_blocked=null`
and seven remaining attempts. The temporary party was closed through the portal
without submitting a scene or consuming an attempt.
