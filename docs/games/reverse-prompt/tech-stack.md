# Reverse Prompt: hackathon technical stack

[All docs](../../README.md) · [Game spec](game-spec.md) · [Simplification](simplification.md) · [Research](../../research/reverse-prompt/README.md)

Version: 2.3 local FastH3 demo scope. Updated: 12 September 2026. Status: FastH3 replacement integrated from `cfc422c` and `9e71dbb`; local tests and the fixture walkthrough pass. Real provider acceptance remains open.

**The stack is sufficient for the three-player demo.** Use one persistent Python application, in-memory game state, and private local video files. The outstanding feasibility test is turning a fresh Reactor stream into a playable five-second clip within the demo's time budget. Follow the [game specification](game-spec.md); this document replaces the broader [backend requirements](../../backend-spec.md) for Reverse Prompt. See [before and after](simplification.md) and the [archived architecture](archive/tech-stack-v1.md).

## 1. Stack we will use

**Reactor FastH3 is selected for all three independent relay videos. Sentence Transformers scores guesses locally. No OpenAI API key or service is required.** Live video generation requires Reactor credentials and an exclusive allocation. The FastH3 adapter is integrated; its live flags remain disabled in the combined demo pending acceptance.

| Layer | Choice | Purpose |
| --- | --- | --- |
| Browser UI | React 19, TypeScript, Vite, CSS Modules | One responsive page, phase components, native video playback |
| Browser communication | Native `fetch`; one-second polling | Submit commands and retrieve an authorized snapshot |
| Frontend tooling | Node.js 24 LTS, npm lockfile | Build static assets; FastAPI serves them during the local demo |
| Backend | Python 3.13, FastAPI, Pydantic 2, Uvicorn | Rules, guest cookies, validation, media authorization, provider calls |
| State and concurrency | Python dataclasses/dictionaries, `asyncio.Lock`, retained asyncio task references | One room and one generation at a time, in one process |
| Video generation | Reactor FastH3 (`reactor/fast-h3`), locked `reactor-sdk` 1.5.1 | Fresh text-only video session for each relay step |
| Video preparation | FFmpeg and ffprobe | Produce and validate a short browser-compatible MP4 |
| Similarity scoring | Sentence Transformers, `sentence-transformers/all-MiniLM-L6-v2`, CPU PyTorch | One local embedding batch for the original and two guesses, then cosine scoring |
| Input handling | Local format/token validation; Reactor's generation-input filters | No separate app content classifier; presenter can stop/reset |
| API client | `reactor-sdk`; HTTPX if needed for Reactor token minting | Reactor requests with explicit timeouts; no embedding API client |
| Media and tiny persistent guard | Private local directory; one small JSON quota file | Temporary videos plus a restart-safe session allowance/block |
| Local runtime | Host laptop, one Uvicorn worker, HTTP over the same Wi-Fi or hotspot | Same-origin frontend/API; remote deployment is deferred |
| Python tooling and checks | uv lockfile, pytest, Ruff; TypeScript compiler | Reproducible dependencies and focused rule/privacy checks |
| Optional presentation | Manually exported VEED intro MP4 | Static asset only; no `fal-client` or VEED runtime key required |

The shared manifests and lockfiles contain the installed dependency set. The FastH3 replacement uses the existing generic SDK command interface and requests no new dependency or model-selector environment variable.

## 2. Small architecture and ownership

```mermaid
flowchart LR
    Phones[Three player browsers] -->|LAN HTTP: commands and polling| App[One FastAPI process on laptop]
    App --> State[In-memory room]
    App --> Reactor[Reactor FastH3]
    App --> Scorer[Local Sentence Transformers and CPU PyTorch]
    App --> FFmpeg[FFmpeg subprocess]
    FFmpeg --> Files[Private local MP4 files]
    App --> Files
    App --> Guard[Quota JSON file]
```

FastAPI serves the built frontend and API. Use `--workers 1`; disable auto-reload for the demonstration. Multiple workers would have separate room dictionaries, so replicas and autoscaling are unsupported. Persistent generation work also rules out short-lived serverless request handlers. [FastAPI worker documentation](https://fastapi.tiangolo.com/deployment/server-workers/).

Retain references to generation/scoring tasks on application state and clean them up through application lifespan. Normalize and validate text locally, then use a short lock to check role/round/phase, accept one immutable submission, and advance state. Never hold the lock across provider I/O or inference. After asynchronous work, recheck room, round, phase, and submission IDs before publishing. Reset invalidates the round immediately and signals active work to stop. Stale work can clean up its own files but cannot publish to another round.

Use async SDK calls where supported; keep blocking calls off the event loop with `asyncio.to_thread`. Run FFmpeg as a bounded subprocess and terminate it on cancellation. Cancelling an await does not kill a blocking thread: the task still owns provider cleanup and its private temporary directory until work finishes. Keep new generation blocked until that cleanup is resolved. [Python asyncio tasks](https://docs.python.org/3.13/library/asyncio-task.html).

Suggested files are sufficient: `frontend/src/App.tsx`, `api.ts`, `components/`, and `styles/`; `backend/app/main.py`, `game.py`, `reactor_video.py`, `scoring.py`, `media.py`, and `tests/`. Avoid a game plugin framework, generic workflow engine, repository layer, or provider marketplace abstraction.

## 3. State and HTTP contract

Keep one `Room` containing its random internal ID, a separate four-digit room code string, three player records, host ID, and current `Round`. Each player has a server-issued random guest token. A round holds its ID, phase, step index, three immutable prompts, three local media descriptors, two guesses, final scores/outcome, and submission receipts. No history survives reset or restart.

Follow the shared [room code standard](../../shared/room-code-spec.md) for generation, validation, join links, lifecycle, and implementation acceptance. The round **Reset** keeps the roster and code; a server restart removes the room lookup and requires everyone to join a newly created room.

```text
lobby → author_input → generating(0) → relay_input(1)
      → generating(1) → relay_input(2) → generating(2)
      → guessing → scoring → reveal
Any generation failure → error; host reset → lobby
```

| Route | Contract |
| --- | --- |
| `POST /api/room` | Organizer code and name create the only room; reject if one exists |
| `POST /api/join` | Validate the four-digit room code string and name, claim a free lobby slot, and issue guest cookie |
| `GET /api/state` | Return only this guest's public state, own accepted text, and allowed media IDs |
| `POST /api/start` | Host only; exactly three players, scoring model ready, no unresolved session, at least three unused attempts |
| `POST /api/submit` | Round ID, expected phase/step, client submission UUID, text; server derives player/role |
| `POST /api/reset` | Host only, expected round ID; stop current work and return to lobby when cleanup permits |
| `GET /api/media/{media_id}` | Authenticate and recheck current phase/role; support byte ranges |

Return `200` with the submission receipt after local validation and acceptance; generation or scoring continues in its retained task. Same ID/body returns the same receipt without scheduling duplicate work. Different content for the same ID, a filled slot, or the wrong phase returns `409`. Invalid text returns `422` without occupying the slot; corrected input uses a new UUID. Store duplicate receipts only for the current round. Check Start/Reset under the same lock and reject stale host commands. Join retries from an already issued guest cookie return that guest instead of consuming a slot.

Poll every second while visible, immediately on focus and after commands, with one request in flight and a short error backoff. Show a connection message after repeated failure. Snapshots carry room/round ID and monotonically increasing revision; ignore older responses. Replace private UI state when its phase permission ends. Input drafts stay component-local and clear on round change.

Use a random opaque `HttpOnly`, `SameSite=Strict` guest cookie, same-origin fetch, JSON-only mutations, and an Origin check against the configured browser origin. Omit `Secure` for the trusted local HTTP demo so phones can send cookies to the laptop's LAN address. Names and room codes are not identity. Keep the organizer code server-side and apply simple per-IP attempt limits to create/join. Secrets and Reactor tokens never reach the browser. A restart invalidates guest sessions; no recovery account is necessary.

Resolve media IDs through the current round's server map, never a client-supplied path. Authorize every GET/HEAD/range request using the game's visibility table and send `Cache-Control: private, no-store`. Do not mount the private media directory as static files. A copied URL does not grant access. Local cleanup does not retract a clip someone already watched or captured.

## 4. Reactor integration and essential limits

Use fixed model `reactor/fast-h3` and a fresh creator-owned session per accepted prompt. The input is that prompt plus the existing fixed instruction: “A single continuous shot depicting the described scene. No captions or on-screen text.” Keep the original player text separately for scoring. Never pass previous prompts, images, videos, or session state into the next generation. Consume only `main_video`; the game's saved output remains silent even though FastH3 also generates audio. [FastH3 overview](https://docs.reactor.inc/model-api-reference/fast-h3/overview).

The game owner has specified the following replacement contract. Local tests and a real FastH3-to-phone spike must establish its behavior before live acceptance:

1. Persist one consumed attempt and set the unresolved-session guard before contacting Reactor. Mint a token restricted to `reactor/fast-h3`, `max_sessions=1`, and `max_session_duration_seconds=90`. Retain the 90-second application deadline covering connection, generation, capture, encoding and validation.
2. Confirm acknowledgments for `set_autoplay(false)`, `set_canvas` with aspect `16:9`, and `set_flush_on_clip_end(true)`. Enqueue the current text plus fixed instruction with opaque attempt metadata and `seconds=5.167`. Require a correlated `clip_queued` identity, a matching completion event and a declared 124-frame source length. A compact completion event may omit that length: preserve acknowledged metadata or make one read-only lookup of the same playout item; never enqueue again. A differing duration fails this selected contract. The command/event definitions are documented in the [FastH3 schema](https://docs.reactor.inc/model-api-reference/fast-h3/schema).
3. Explicitly play that clip ID. Admit decoded BGRA frames only after its matching `clip_started` event. Save the first 120 frames, and reject playback that ends early. SDK frame/event ordering must be measured on the actual connection; provider-fake ordering is insufficient evidence.
4. Transfer frames through the existing bounded 16-frame queue into an owned FFmpeg subprocess. Expect 1344×768 frames for this selected canvas; reject changed dimensions, known timestamp reordering, a source timestamp span over 15 seconds, or queue overflow. Preserve the handling of absent frame IDs/timestamps. Encode five seconds of silent H.264/yuv420p at 24 fps, with faststart, no source metadata and an output below 10 MiB. No provider recording download or automatic retry is part of this route.
5. Terminate the creator session once the selected frames are saved, or on error/reset. Independently verify terminal state before clearing the persistent guard or publishing media. Keep encoder launch/cancellation owned, kill/await it when required, then validate the MP4 with ffprobe and bounded decoding within the remaining deadline. The provider duration cap remains a crash fallback.

Existing FFmpeg tests establish encoding and frame order for supplied frames, and the prior provider fakes cover independence, quota and cleanup. The replacement must add coverage for clip acknowledgment, generation, explicit playback, frame admission and failed/short playback. Live timing and phone compatibility remain open. See the [game handoff](../../development/handoffs/reverse-prompt.md), [Python SDK](https://docs.reactor.inc/sdk-reference/python/reactor) and [token authentication](https://docs.reactor.inc/authentication).

**Use one active provider session, one attempt per step, and no automatic session-creation retries.** Initialize a persistent `demo-quota.json` explicitly with nine remaining attempts and no unresolved session. Decrement atomically before connection, never refund ambiguous attempts, and never replenish on room reset or process restart. A missing/corrupt guard file blocks live mode until the operator initializes or repairs it. Do not bake automatic quota initialization into startup.

Keep the unresolved flag set if termination is uncertain or the process crashes. The presenter/operator checks the provider session has ended before explicitly clearing it; gameplay reset cannot clear it. This replaces a durable job reconciler with a manual recovery step. Nine attempts allow up to three complete live rounds, including rehearsal; failed attempts reduce that allowance. This is an attempt limit, not a dollar billing ledger. Session duration matters because Reactor bills active ready time, including idle time. [Session limits](https://docs.reactor.inc/resources/rate-limits), [Billing](https://docs.reactor.inc/resources/billing).

## 5. Scoring and text moderation

Keep **Sentence Transformers with `sentence-transformers/all-MiniLM-L6-v2` and CPU PyTorch**, as in the original design. The model produces 384-dimensional embeddings and defaults to truncating inputs beyond 256 word pieces. Validate normalized text with the pinned tokenizer without truncation; reject input beyond the model's actual `max_seq_length`, including special tokens, in addition to the 300-code-point limit. Expose the token limit and corrective error to the UI. [Model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2).

Download a pinned model/tokenizer revision during local setup and record its immutable commit in the runtime manifest. Keep these files outside disposable round media. Load them from the local model directory once at startup, run a warm-up, and disable Start if loading/self-test fails. No model download, hosted inference, or API key is needed while scoring a round. The immutable model revision is recorded in its setup manifest; compatible versions are locked centrally and have passed the offline check on this Mac.

Encode `[P0, guess_B, guess_C]` once in a local batch on CPU with normalized embeddings, evaluation mode, and identical preprocessing. Use `asyncio.to_thread` so inference does not block polling/media requests. Require three complete finite nonzero vectors of the expected size; calculate cosine and rounded scores using the game formula and store the result once. Sentence Transformers documents cosine-based semantic comparison. No vector database, LLM judge, or separate scoring service is required. [Similarity documentation](https://sbert.net/docs/sentence_transformer/usage/semantic_textual_similarity.html).

Keep the 15-second scoring deadline; inference failure or timeout produces an unscored reveal. A timed-out thread may still finish, so retain its reference, discard stale results, and do not start another inference on that model until it finishes. Warm-up and offline scoring checks must pass on the demo server. This restores a local model/dependency footprint while removing scoring-network calls.

There is **no separate app moderation API** in the demo. Local validation checks format and length; render names/guesses as plain text. Reactor screens generation input and may terminate a rejected session after billable time starts. Do not describe these checks as a free preflight or comprehensive output moderation. Use benign prompts and presenter stop/reset; dedicated name/guess classification, output-frame scanning, reports, and audit tables are deferred. [Reactor moderation](https://docs.reactor.inc/resources/content-moderation).

## 6. Local operation and optional VEED

Run on the host laptop with Python 3.13, CPU PyTorch/Sentence Transformers, FFmpeg/ffprobe, and a private writable data directory. Verify the pinned Reactor SDK and scoring dependencies against the actual laptop OS/architecture in the first spike; follow the [local environment guidance](../../environment-setup.md) if a dependency needs a local runtime adjustment. Measure warm model memory, inference latency, and conversion memory together on this machine. The selected scorer uses CPU inference. The pinned native SDK, FFmpeg and scorer dependencies have passed local import/encoding/offline checks; real provider capture remains unverified. [Reactor SDK distribution](https://pypi.org/project/reactor-sdk/).

Build the frontend and download the pinned scoring model during local setup. FastAPI serves the Vite build and API directly over HTTP. Run one Uvicorn worker without reload, binding to `0.0.0.0:8000` for phone access. Set `PUBLIC_ORIGIN=http://<laptop-LAN-IP>:8000` and open that address on the host and player phones on the same Wi-Fi or hotspot. Use `http://localhost:8000` only for laptop-only checks. During development, Vite proxies API requests to FastAPI; Origin checks must match the browser-facing address. Verify firewall/network access, keep the laptop awake, and confirm outbound internet access for Reactor. Remote hosting, Caddy, domains, and TLS setup are deferred.

Required configuration: `REACTOR_API_KEY`, `ORGANIZER_CODE` (or shared `HOST_PASSCODE`), `PUBLIC_ORIGIN`, `MEDIA_ROOT`, `REVERSE_PROMPT_QUOTA_FILE`, `REVERSE_PROMPT_LIVE_ENABLED`, and `EMBEDDING_MODEL_PATH` pointing to the downloaded, pinned model. The quota and model files must survive process restarts and local rebuilds; keep them outside disposable build/round directories. Round media is ephemeral. On startup delete stale round media, start with an empty lobby, load/warm the local scorer, and preserve any unresolved-session flag. Never log credentials or player content; phase, latency, error category, and remaining attempt count are enough.

VEED is optional polish: create one generic intro manually, export an MP4, and play it as a static asset. No runtime call, queue, TTS integration, or avatar conversation is required. The researched Fabric API animates a supplied image/audio pair; that does not replace Reactor's scene-generation job. If there is no ready VEED export, omit the intro. [VEED/Fabric research](../../research/reverse-prompt/README.md#veed-findings), [Fabric API](https://fal.ai/models/veed/fabric-1.0/api).

## 7. Build order and evidence needed

| Order | Deliverable | Exit check |
| --- | --- | --- |
| 1 | One Python Reactor-to-MP4 spike on the demo laptop | Live clip plays on actual phones through the LAN URL; session termination and cap verified; record total latency |
| 2 | One-room game loop with fixed local clips | Three browsers reach reveal; refresh and private access work |
| 3 | Live Reactor adapter | Three independent generations complete; duplicate submission and forced failure handled |
| 4 | Local Sentence Transformers scorer and final result UI | Pinned model preloaded; offline exact/paraphrase/unrelated examples, token limit, ties, and inference failure checked |
| 5 | Local laptop and phone rehearsal | Three people finish live over the LAN origin; private files, restart guard, reset, and phone playback checked |
| 6 | Optional visual polish/VEED intro | Core demo still passes; no added runtime dependency |

Use focused pytest checks for role/phase authorization, duplicate and stale submissions, cosine rules, failed scoring, session quota, and reset during generation. Check TypeScript and Ruff; rehearse the full flow in three browser sessions, including one real phone. A separate browser testing stack, migration tests, multi-room load tests, and a broad CI matrix are deferred. These checks map to [DEMO-01 through DEMO-08](game-spec.md#7-demo-acceptance).

The integrated fixture application, FastH3 provider-fake/encoder tests and offline scoring checks pass. Real provider capture and physical-phone rehearsal remain open; consult the coordinator's [trial record](../../development/live-provider-slots.md) for the active slot and single persistent campaign path before paid work.

## Adopted application integration (foundation)

This game plugs into the shared local FastAPI/React application. The [shared contract](../../development/contracts/shared.md) owns exact prefixed API paths, module exports, session discovery, Origin/cookie rules, exclusive party admission, code rotation, and confirmed close-before-switch behavior. Browser routes are `/games/reverse-prompt/host` and `/games/reverse-prompt/join?code=…`. Prefix every API route above with `/api/games/reverse-prompt` in place of `/api`. Use the game-specific private directory from `GameContext.settings.media_dir(game_id)`. Game rules, role distinctions, timers, attempt accounting and media authorization above remain authoritative. Shared dependencies and configuration are owned by Session A; do not change manifests/lockfiles in a game worktree.
