# Reverse Prompt local operation

Run from the repository root. Shared dependencies/start commands are owned by the integration session.

```sh
UV_CACHE_DIR=/private/tmp/vibeparty-reverse-uv uv sync --all-extras --frozen
.venv/bin/python scripts/games/reverse-prompt/model_setup.py .local/vibeparty-persistent/models/all-MiniLM-L6-v2
.venv/bin/python scripts/games/reverse-prompt/offline_check.py .local/vibeparty-persistent/models/all-MiniLM-L6-v2
bash scripts/dev.sh
```

Private `.env` settings for this worktree: `BACKEND_PORT=8013`, `FRONTEND_PORT=5176`, `API_PROXY_TARGET=http://127.0.0.1:8013`, `BROWSER_ORIGIN=http://localhost:5176`. Set `PUBLIC_ORIGIN` to the laptop's LAN HTTP origin for phone joining, and `ADDITIONAL_BROWSER_ORIGINS` only for other trusted local testing aliases. Keep `GENERATION_MODE=fixture` and `REVERSE_PROMPT_LIVE_ENABLED=false` until the integration session grants a trial. Set `EMBEDDING_MODEL_PATH` to the pinned local model directory. Organizer entry uses `ORGANIZER_CODE` if supplied, otherwise shared `HOST_PASSCODE`.

Open `/games/reverse-prompt/host`, select Scripted rehearsal, and create A with the organizer code. B/C join the displayed code in separate browser cookie stores. Each actor explicitly submits the supplied script at their turn; B/C separately submit their final guesses. The reveal labels sample scores and replays the stored clips. The three fixture assets are original geometric animations; rebuild with `build_fixtures.py` only when intentionally changing the script/assets.

Room codes are four ASCII digits such as `0042`, distinct from the organizer passcode. Preserve leading zeros when copying or typing. Portal entry and the game's form use the same validator. Round Reset retains the roster/code; Close party clears the roster and old lookup. A new party receives a new shared code reservation.

## Coordinated live checks

Current checkpoint, 12 September 2026: the user stopped further live-trial coordination. Live generation is disabled. Reverse001 saved one real clip; Reverse002 failed on its first generation and stopped unscored. Both sessions were independently closed, with seven attempts remaining at the last verified checkpoint; the two unused slot allocations were cancelled. The integration worktree holding the canonical ledger has since been removed, and that file is unavailable. Restore the original campaign record to durable storage before live operation; do not replace it with a fresh nine-attempt allocation. The procedure below is retained for operation after an explicit change to that instruction; it does not authorize another call.

Ask the integration session for the exclusive live slot and the single persistent campaign path. No automatic initialization is performed. The coordinator deliberately authorizes this once, with nine attempts:

```sh
.venv/bin/python scripts/games/reverse-prompt/quota_operator.py /absolute/persistent/campaign/quota.json initialize
```

Set `REVERSE_PROMPT_QUOTA_FILE` to that exact shared campaign path; keep it outside the media root and preserve it across worktrees/restarts. Never copy or replace it to obtain another allowance. Set the backend-only Reactor key and enable `REVERSE_PROMPT_LIVE_ENABLED=true` only for the granted slot. No key/token belongs in a URL or frontend variable.

```sh
.venv/bin/python scripts/games/reverse-prompt/spike.py --slot coordinator-reference
.venv/bin/python scripts/games/reverse-prompt/quota_operator.py /absolute/persistent/campaign/quota.json inspect
```

The spike consumes one attempt before token mint/connect, enforces a90-second generation deadline and closes its session in `finally`, writes a private MP4, and reports sanitized capture/closure evidence. It uses MiniMax FastH3 (`reactor/fast-h3`): enqueue a 5.167-second text-only clip, confirm its matching generated event, explicitly play it, and capture120 decoded frames after its matching start event into FFmpeg. Output is five seconds at24fps and1344×768. It does not require Reactor's optional recording API or browser screenshots. The output remains genuine generated content from that one session; this route does not generate frames without cloud access.

Capture has a bounded16-frame queue, validates the1344×768 landscape canvas/payloads and available timestamp order/span, and stops accepting frames at120. A playback-end event before120 frames rejects the short video. Compact completion events preserve enqueue metadata or trigger one read of the matching existing queue item; they never trigger another generation. Missing/mismatched clip identities, invalid frame counts and failed or ambiguous commands end unscored without retry. The game retains one session across three independent clips, including both30-second B/C turns. No continuation or image inputs are passed. Settings are applied once; each clip has distinct correlation/capture state. The token caps the session at360 seconds, with a345-second application round cap. Each accepted prompt still consumes its own persistent generation attempt. The final clip waits for verified session closure before guessing; failure, timeout, reset and shutdown also close it. Queue overflow ends unscored rather than silently dropping frames. SDK metadata zero means absent identity; it is not deduplicated as one frame. Encoding cancellation kills and awaits the FFmpeg process before cleanup. The same private media permissions and independent provider closure checks apply. `model=reactor/fast-h3`, `capture_method=decoded_frames`, declared source frames, received/encoded frame counts, frame rate, startup/generation/total elapsed time and available source timestamp span are included in spike evidence. The90-second limit remains per generation; the entire-session limits above include both thinking turns. Measure real event/media ordering and total delay before live acceptance. See the [FastH3 switch evidence](../../../docs/research/reverse-prompt/fasth3-switch.md).

An ambiguous mint or connect keeps the unresolved marker, even without a session ID. Verify Reactor closure independently before operator reconciliation; resetting gameplay never clears it. `confirm-closed` requires the exact attempt ID and a nonempty description of that independent check. Never use it merely because a deadline elapsed.

Each completed attempt now saves diagnostic evidence alongside its persistent quota record: outcome, last phase, available timings/frame counts, capture state and independently confirmed closure. Failure records retain an exception category and fixed local error messages, excluding player text, credentials and SDK/HTTP response bodies. `quota_operator.py ... inspect` shows this evidence after restart. Diagnostic storage does not refund attempts or clear an unresolved session, and failure to store it does not mask the generation result. The older002 attempt has no such diagnostic detail; its exact cause remains unknown.

After the one-clip gate passes, restart the service without reload and create a Live room. Complete A→B→C→both guesses→local scores→reveal. With a separately coordinated slot/allowance, run `spike.py --slot reference --force-timeout` for a deliberately failed attempt. A normal generation failure has no retries and no automatic fixture fallback. Report consumed attempts and terminal-session evidence to A before slot transfer. Finally disable live mode again.

## Checks

```sh
.venv/bin/pytest backend/tests/reverse_prompt -q
.venv/bin/ruff check backend/games/reverse_prompt backend/tests/reverse_prompt scripts/games/reverse-prompt
npm --prefix frontend run build
npm --prefix frontend run lint
```

Use three independent browsers/phones over the same trusted LAN HTTP address for final acceptance. The desktop CUA alias rehearsal is documented in the research evidence; actual demo phones and real provider calls are additional gates. On restart identities/rounds disappear; the persistent quota and unresolved marker survive. Delete only Reverse Prompt's disposable clips after owned work stops; keep model/quota storage.

## Retained round session

The latest user request replaces separate sessions and unlimited relay thinking with one session and30-second B/C turns. Both private-clue countdowns start when the server publishes the clue, include viewing/typing, and survive refresh. Expiry stops unscored and closes the session. A's original and both final guesses have no countdown. Rehearsal exercises the same timer behavior without provider traffic. The older live evidence used separate sessions; it does not verify this new session-reuse implementation.

Quota compatibility: `session_attempt` links consecutive attempt records to one session. The original ledger's limit and allowance do not change. While the group is open, restart/new-session generation remains blocked; terminal verification closes all its records atomically. Old code cannot read an in-progress multi-attempt group, so upgrade the game as a unit and never run old and new adapters against the same active campaign.
