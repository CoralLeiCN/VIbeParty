# Reverse Prompt: hackathon simplification

[All docs](../../README.md) · [Game spec](game-spec.md) · [Technical stack](tech-stack.md) · [Research](../../research/reverse-prompt/README.md)

Updated: 12 September 2026. Decision: scope Reverse Prompt to a presenter-led hackathon demonstration with one room and three players.

The original stack could support a broader product, but required databases, queues, recovery machinery, and deployment work before demonstrating the interesting part. The simplified stack is sufficient for the demo. Its remaining technical uncertainty is Reactor capture, termination, and playback latency on the actual phones; that is the first implementation task.

These changes are applied to the [current game spec](game-spec.md) and [current tech stack](tech-stack.md). The full before versions are preserved in the [archived game spec](archive/game-spec-v1.md) and [archived tech stack](archive/tech-stack-v1.md). This is a documentation change; the application has not been built.

**Reactor remains the video generator. Sentence Transformers remains the local embedding scorer. The demo requires no OpenAI service or API key.**

## Gameplay before and after

Both versions are inspired by the classic game [Telephone](https://en.wikipedia.org/wiki/Telephone_game). The adaptation keeps its message-passing mechanic and adds AI-generated videos, human descriptions, final guesses, and similarity scoring; see the [game specification's inspiration and credit](game-spec.md#1-the-game-we-are-demonstrating).

| Area | Before: broader MVP | After: hackathon demo |
| --- | --- | --- |
| Players and rooms | 3–8 players; infrastructure supporting multiple rooms | Exactly 3 players, one room at a time |
| Lobby | QR/code join, ready states, waiting guests | Code join, three names, host Start |
| Roles | Random author/order, author rotation on replay | Host is author; guests interpret in join order |
| Input clocks | 45-second windows, 30-second extensions, deadline races | No input countdown; presenter controls pacing |
| Generation | 180-second phase, up to two paid attempts | 90-second phase, one attempt; failure ends round |
| Relay recovery | Skip failed/missed steps and reuse last good clue | Complete all three videos or reset |
| Final guessing | Deadline, missing guesses, partial participation rules | Wait for both guesses, then score |
| Scoring failure | Retry within 60 seconds | One local scoring batch with a 15-second deadline; unscored reveal on failure |
| Reconnect | Durable round recovery, host migration, departures | Refresh works while process lives; restart loses round |
| Presentation | Separate paired display, optional reusable avatar clips | Use host browser for final/reveal; optional single intro |
| Results | Full reveal plus broader retention/replay management | Three prompt/video cards, two guesses, score/tie, Reset |

The core remains: `P0 → V0 → P1 → V1 → P2 → V2 → guesses → reveal`. Each clip uses only its own submitted prompt, each interpreter receives a private clue, and final guesses are scored against `P0`. The original author remains unscored.

## Technology before and after

| Responsibility | Before | After | Accepted tradeoff |
| --- | --- | --- | --- |
| Frontend state/navigation | React Router, TanStack Query, WebSockets | React phase components, native fetch, 1-second polling | Updates may appear about a second later |
| Game persistence | PostgreSQL, SQLAlchemy, psycopg, Alembic | In-memory Python room | No round survives backend restart |
| Work scheduling | Celery, Redis, generation/utility workers, dispatcher | Retained asyncio tasks in one FastAPI process | One room, no independent worker recovery |
| Concurrency correctness | Transactions, outbox, leases, fencing, reconciliation | Short lock, immutable submissions, round/step IDs | No multi-process scaling |
| Video storage | Private S3 and boto3 | Authorized local MP4 files | One server; no archive or object-store redundancy |
| Scoring | Sentence Transformers, MiniLM model, CPU PyTorch in utility worker | Same local model and CPU runtime, loaded once in the FastAPI process | Keep model/dependency footprint; remove separate scoring worker; no scoring API calls |
| Moderation | External text checks, sampled output frames, reports, audit tables | Local format/length validation, Reactor generation-input filters, presenter stop/reset | No separate name/guess classifier, app preflight moderation, or comprehensive output review |
| Spending controls | Currency reservations, durable attempt ledger, retry accounting | Persistent nine-attempt allowance, one session at a time, provider duration cap | Manual operator recovery for uncertain termination |
| Runtime | Docker Compose with app, workers, dispatcher, database, Redis; S3 | One FastAPI worker on the host laptop; LAN HTTP | Same-network phone access; remote deployment deferred |
| VEED | Optional scripted asset preparation through Fabric/fal | Optional manually exported static intro | No dynamic host or runtime VEED integration |
| Verification | Full backend/frontend/browser/CI suite and migration checks | Focused pytest, Ruff/TypeScript checks, three-browser live rehearsal | Narrow evidence for the exact demo path |

The small persistent quota file is intentional: game state can be disposable, but restarting must not silently authorize more paid generations. No database or job recovery service is required to enforce that limited rule.

## Required stack after simplification

- **Frontend:** React 19, TypeScript, Vite, CSS Modules, native fetch/polling; Node 24 and npm for builds.
- **Backend:** Python 3.13, FastAPI, Pydantic 2, Uvicorn with one worker; standard-library state, locks, and tasks.
- **Video:** Reactor FastH3 via the locked `reactor-sdk`, FFmpeg/ffprobe, private local disk. The user selected this replacement on 12 September; see the current technical plan for its integration and live-verification status.
- **Scoring:** Sentence Transformers with `sentence-transformers/all-MiniLM-L6-v2`, CPU PyTorch, and cosine similarity; preload a pinned model for local inference.
- **Input checks:** Local format/token limits and Reactor's generation-input filters; no app moderation API. HTTPX is needed only if Reactor token minting uses it.
- **Local runtime and checks:** Host laptop, one Uvicorn worker, LAN HTTP, uv/npm lockfiles, pytest, Ruff, TypeScript. Verify SDK/scorer compatibility on the laptop before the demo.
- **Optional only:** VEED-exported intro MP4. No VEED/fal dependency in the running game.

Provider evidence and the reason for each choice are linked in the [technical specification](tech-stack.md) and [Reactor/VEED research](../../research/reverse-prompt/README.md). Exact package versions and live compatibility remain to be verified during implementation.

## What we still must build and prove

1. Generate one real Reactor clip, download and convert it, terminate the session, and play it on the demo phones. Measure the entire operation.
2. Build the three-player loop, enforce private snapshots/media, and show the ordered reveal.
3. Preload the local Sentence Transformers model, verify scoring without network access and reject over-limit text; handle duplicate submission, reset during generation, and provider failure.
4. Rehearse a full live round and a failure/reset before adding VEED or visual polish.

There is no need to build the deferred product infrastructure to show this game. There is still a need to verify that the live video path works; a scripted rehearsal cannot prove that.
