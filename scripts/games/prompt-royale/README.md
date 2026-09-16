# Prompt Royale local runbook

From the repository root:

```sh
uv sync --frozen --extra live
npm ci --prefix frontend
.venv/bin/python -m uvicorn backend.app:app --host 0.0.0.0 --port 8012 --no-access-log
```

In a second terminal: `npm run dev --prefix frontend -- --force`.
Private root .env: BACKEND_PORT=8012, FRONTEND_PORT=5175,
API_PROXY_TARGET=http://127.0.0.1:8012, BROWSER_ORIGIN=http://localhost:5175,
PUBLIC_ORIGIN=http://<laptop-LAN-IP>:5175, GENERATION_MODE=fixture.
Use the actual LAN origin for all browsers in a group rehearsal. The final integrated
server uses the shared demo command/port 8000; do not run multiple workers or reload live work.

Prompt Royale uses `reactor/fast-h3` for real generation. No tokenizer download is
needed for this model or for fixtures. FFmpeg/ffprobe must be on PATH or configured
through game settings. The optional `prepare_tokenizer.py` installs the old Helios
tokenizer only for a `capture_spike.py --model helios` comparison.

Focused checks:

```sh
.venv/bin/ruff check backend/games/prompt_royale backend/tests/prompt_royale scripts/games/prompt-royale
.venv/bin/pytest backend/tests/prompt_royale backend/tests/shared -q
npm run build --prefix frontend
npm run lint --prefix frontend
cd frontend
ROYALE_URL=http://<laptop-LAN-IP>:5175 npx playwright test -c src/games/prompt-royale/e2e/playwright.config.ts
```

The browser scenario creates/clears its own fixture rooms and needs no other active party.
It reads only HOST_PASSCODE from private .env; no keys are printed or sent by the test.
Use isolated browser contexts/profiles because cookies are not isolated by port.

## Current capture: shorter clips accepted

The [16 September change](../../../docs/research/prompt-royale/shorter-clips-2026-09-16.md)
encodes received frames once at 24 fps, up to five seconds. Sparse video produces a
shorter clip, without padding. Capture regressions and a three-browser fixture round
with mixed clip lengths passed. A subsequent
[three-player live rehearsal](../../../docs/research/prompt-royale/end-to-end-2026-09-16.md)
also passed with three real five-second clips, scored results, rematch setup and
confirmed room/provider cleanup.

## Earlier live gate: three-player round passed with image holds

The [capture fix and verification](../../../docs/research/prompt-royale/tolerant-capture-2026-09-15.md)
records the user's acceptance of choppy motion, sparse-frame regression coverage and a
successful three-player live round. That earlier policy held images through gaps;
completed playback did not require 120 received images. Four-player and physical-phone live
acceptance remain unverified.

The [earlier 15 September retest](../../../docs/research/prompt-royale/retest-2026-09-15.md) failed with incomplete captures. An isolated probe measured substantial video packet loss, despite successful clip generation. All sessions were confirmed closed.

Earlier results: See the [FastH3 migration and live rehearsal](../../../docs/research/prompt-royale/fast-h3-2026-09-14.md):
one standalone capture and a three-player round completed with playable clips, scored
results, replay and verified session cleanup. Clips took about 20–22 seconds per attempt.
The [earlier end-to-end verification](../../../docs/research/prompt-royale/end-to-end-2026-09-14.md)
records the host presence fixes and historical Helios failures.

Coordinate every live trial with integration. Obtain an exclusive slot and an explicit
attempt/call allowance after the operator checks account balance, quota and prior session
closure. Do not infer permission from installed SDKs or a configured key.

After allocation, the following commands perform at most one call each and write evidence
under .local/vibeparty/prompt-royale/spike. They are not fixture commands:

```sh
.venv/bin/python scripts/games/prompt-royale/capture_spike.py --allocation <granted-slot>
.venv/bin/python scripts/games/prompt-royale/topic_spike.py --allocation <granted-slot>
```

Each capture run gets its own timestamped directory under
`.local/vibeparty/prompt-royale/spike/`, containing `evidence.json` and a clip when successful.
The game also retains one JSON diagnostic per capture attempt under
`.local/vibeparty/prompt-royale/diagnostics/`, outside disposable room clips. These records
include the failed stage, connection state timings, total frames, zero-timestamp frames,
exception types, structured SDK error codes, HTTP status
when available, and independent session closure. They exclude prompts, credentials,
recording URLs and raw provider error messages. Failed attempts also emit a warning to
the server console. The records survive closing a room and restarting the server.

Capture defaults to FastH3 (`--model fast-h3`). It validates the complete prompt against
FastH3's 800-character API limit and creates a FastH3-only token capped to one session
and 60 seconds. After SDK readiness, it reads live duration limits, disables autoplay,
enqueues a six-second scene (the provider returns its accepted duration), waits for
`clip_generated`, and explicitly plays that clip. SDK BGRA frames are captured through a
bounded buffer into a local MP4; the optional Reactor server recorder is not used.
Only frames during the matching `clip_started` / `clip_finished` interval count. Success
requires completed playback and at least two captured frames. Each received frame is
encoded once at 24 fps, up to 120 frames. Capture can continue past five receiver seconds
until matching playback ends or the frame cap is reached. Missing frames produce a shorter
clip; no repeated images are added to fill five seconds. FFprobe validates a playable silent
H.264 output up to five seconds. All sessions are independently confirmed closed. Diagnostics retain
clip ID, duration bounds, stage timings, captured/dropped frames, actual output duration,
and rejected command names without raw payloads.

There is no creation retry in the spike. Inspect the run's evidence.json and private MP4.
A failed spike is a failed live gate even if fixture tests pass. Use `--model helios` to
reproduce the earlier streaming/recording experiments.

For an explicitly allocated startup experiment, the standalone capture supports
`--startup-timeout 300`: give connection setup an outer five-minute deadline, then
allow up to 60 seconds for capture. The token lifetime and server-enforced session cap are
extended together (480-second token, 360-second session cap for this example).
The default `--startup-mode sdk` uses `reactor.connect()` and reports
`reactor.on("status_changed", ...)` events immediately. It also prints the last
callback state and frame counts every 15 seconds. The installed Python SDK has its
own fixed 20-poll startup limit, which can end the attempt before the outer deadline.

To observe callback state for a full five minutes, including an early SDK failure:

```sh
.venv/bin/python -u scripts/games/prompt-royale/capture_spike.py \
  --allocation <exclusive-allocation-id> --startup-timeout 300 \
  --startup-mode sdk --observe-seconds 300
```

The observer makes one creation attempt. If that attempt ends early, subsequent
progress reports show `capture_finished: true` and the last callback status. They
do not represent continued waiting for a GPU or a new session attempt.

The separate `--startup-mode rest` experiment creates through REST, polls the same
session for runtime capabilities/transport, then attaches the SDK. This avoids the
native SDK's fixed poll limit. The adapter owns termination of the adopted session,
including when startup times out. REST startup is opt-in.
Use an exclusive slot with no active game; this standalone
override does not fit within the normal game's 180-second round deadline.

The adapter verifies GET /sessions/{id} with API version headers. Terminal CLOSED/INACTIVE
or 404 establishes closure. It may issue bounded DELETE then recheck; SDK disconnect alone
is insufficient. Pending session IDs (never JWTs) are recorded outside disposable clips.
An unresolved-provider.json marker blocks shared admission on restart. The operator must
verify every named session, or the whole account for a missing ID, before clearing it.
Never remove the marker merely to unblock a game.

Topic provider: OPENAI_API_KEY, gpt-5.6-luna, reasoning effort none, total timeout 10s, 64 output tokens,
160 accepted characters, no automatic retries, maximum 16 calls separate from video starts.
Generation sends only the generic topic instruction, with store:false and no tools.

The host can switch **Video generation** between **Fixture rehearsal** and
**Real generation · Reactor** in the lobby, including after returning from a finished round.
The choice applies to the whole room and is locked during a round. Topic suggestions keep
their separate PROMPT_ROYALE_TOPIC_MODE setting. GENERATION_MODE sets the initial video
mode for new rooms; it can stay at fixture while real generation is available in the lobby.

Live gameplay stays disabled by default. Explicit launch setup needs the current slot,
PROMPT_ROYALE_LIVE_ENABLED=true, verified FastH3 provider access,
PROMPT_ROYALE_REHEARSED_CAPACITY matching a passed rehearsal for the selected 1–4 player count, and an allocated
PROMPT_ROYALE_LIVE_SESSION_STARTS (maximum 16). Remaining starts must cover two per player.
Rehearse three players then four, including physical Safari/Chrome and projected playback,
within the 180-second generation deadline. Record actual time, failures, closure and charges.
Never silently replace live media or topics with fixtures.

Play again deletes the finished round and topic selection. End room cancels owned work,
verifies provider closure, deletes media and sessions, then releases shared admission. If
file cleanup fails, admission remains blocked until cleanup is retried successfully.
Startup purges only this game's orphaned clip directory. Operator: purge remaining game
media within 24 hours after the event; provider retention is separate.
