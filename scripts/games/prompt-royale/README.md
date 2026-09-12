# Prompt Royale local runbook

From the repository root:

```sh
uv sync --frozen --extra live
python3 scripts/games/prompt-royale/prepare_tokenizer.py
npm ci --prefix frontend
.venv/bin/python -m uvicorn backend.app:app --host 0.0.0.0 --port 8012 --no-access-log
```

In a second terminal: `npm run dev --prefix frontend -- --force`.
Private root .env: BACKEND_PORT=8012, FRONTEND_PORT=5175,
API_PROXY_TARGET=http://127.0.0.1:8012, BROWSER_ORIGIN=http://localhost:5175,
PUBLIC_ORIGIN=http://<laptop-LAN-IP>:5175, GENERATION_MODE=fixture.
Use the actual LAN origin for all browsers in a group rehearsal. The final integrated
server uses the shared demo command/port 8000; do not run multiple workers or reload live work.

Token setup accepts `--destination`, process PROMPT_ROYALE_TOKENIZER, or that variable in root
.env. Relative paths resolve against the repository root. Existing files are checksum checked.
Only the tokenizer is downloaded; no video model weights or topic credentials are needed
for fixtures. FFmpeg/ffprobe must be on PATH or configured through game settings.

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

## Live gate: currently not passed

Coordinate every live trial with integration. Obtain an exclusive slot and an explicit
attempt/call allowance after the operator checks account balance, quota and prior session
closure. Do not infer permission from installed SDKs or a configured key.

After allocation, the following commands perform at most one call each and write evidence
under .local/vibeparty/prompt-royale/spike. They are not fixture commands:

```sh
.venv/bin/python scripts/games/prompt-royale/capture_spike.py --allocation <granted-slot>
.venv/bin/python scripts/games/prompt-royale/topic_spike.py --allocation <granted-slot>
```

Capture validates the pinned tokenizer, creates a Helios-only token capped to one session
and 60 seconds, receives six seconds of timestamped media, downloads the recording while
connected, prepares the first five seconds, and independently confirms provider closure.
There is no creation retry in the spike. Inspect evidence.json and the private MP4. A failed
spike is a failed live gate even if fixture tests pass.

The adapter verifies GET /sessions/{id} with API version headers. Terminal CLOSED/INACTIVE
or 404 establishes closure. It may issue bounded DELETE then recheck; SDK disconnect alone
is insufficient. Pending session IDs (never JWTs) are recorded outside disposable clips.
An unresolved-provider.json marker blocks shared admission on restart. The operator must
verify every named session, or the whole account for a missing ID, before clearing it.
Never remove the marker merely to unblock a game.

Topic provider: OPENAI_API_KEY, gpt-5.6-luna, reasoning effort none, total timeout 10s, 64 output tokens,
160 accepted characters, no automatic retries, maximum 16 calls separate from video starts.
Generation sends only the generic topic instruction, with store:false and no tools.

Live gameplay stays disabled by default. Explicit launch setup needs the current slot,
PROMPT_ROYALE_LIVE_ENABLED=true, GENERATION_MODE=live, verified tokenizer/provider access,
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
