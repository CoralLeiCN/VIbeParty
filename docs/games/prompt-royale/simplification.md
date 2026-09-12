# Prompt Royale: hackathon simplification — before and after

Decision: 12 September 2026. The goal is one reliable, supervised, four-player demonstration of the creative round. This updates the specifications; it does not implement an application.

The current [game specification](game-spec.md) and [technology stack](tech-stack.md) supersede the earlier design for this demo. The broader three-game specifications remain future/shared context.

## Before and after

| Area | Before: version 1.0 | After: demo version 1.2 | Tradeoff |
| --- | --- | --- | --- |
| Application | API, dispatcher, capture workers, media workers | One FastAPI process | A process restart ends the room. |
| Room data | PostgreSQL, SQLAlchemy, psycopg, Alembic | In-memory objects and one lock | No durable history, migrations, or restart recovery. |
| Jobs | Celery, Redis, leases, outbox, reconciliation | Tracked asyncio tasks; two entry slots | No worker redelivery or distributed scheduling. |
| Browser updates | WebSockets plus snapshot fallback | One-second HTTP polling | Approximately one-second update lag; simpler refresh handling. |
| Media storage | S3-compatible bucket, boto3, signed URLs | Private local files through authorized API routes | One host, no storage service or independent media scaling. |
| Provider retries | Durable retry handling, up to two billed attempts per entry | One retry in the existing async task; at most two creation attempts, reusing captured media when possible | No queue/recovery service; retry must fit the original deadline and call allowance. |
| Spending | Transactional reservations and price reconciliation | Per-round/per-run attempt limits and dashboard checks | Operator tracks remaining allowance across restarts. |
| Roster | Ready checks, late-player lobby, removal, host transfer | 3–4 players, fixed host, join only between rounds | Host return or room reset replaces membership recovery. |
| Timers | Prompt/vote extensions and per-clip watchdogs | Fixed prompt/vote timers and one screening deadline | Fewer settings and transition cases. |
| Topics | Curated or custom | Small bundled list | Less setup and input validation. |
| Display | Separate pairing/session/permissions | Phones; project the ordinary public screening/results screen | No dedicated spectator experience. |
| Output handling | Required but unselected automatic review adapter | Provider input checks plus host Skip/Abort in supervised play | No automated output-safety claim; revisit for public play. |
| VEED | Optional library and preparation workflow | Optional intro/celebration prepared once | No new runtime provider dependency; the core game works without it. |
| Checks | Broad tooling, distributed failure suite, ten-room load target | Focused rule/API checks, one browser flow, live rehearsals | Validates demo behavior rather than production recovery/scaling. |
| Retention | Automated expiry service with monitoring | Delete on replay/end/startup; operator purge after demo | No monitored deletion guarantee while the server is down. |
| Deployment | Multi-service Docker Compose deployment | One Linux host, Caddy, one Uvicorn worker | No autoscaling; container packaging optional. |

## What stays

Keep the four-player hard cap, three-player minimum, one round at a time, private prompts, identical clip settings, five-second videos, anonymous screening, one server-counted vote, no self-voting, shared winners for ties, bounded provider lifetime, and clearly labelled fixture mode. Keep Quiplash / Jackbox Games credited in the rationale and credits UI.

Reactor remains the main live integration risk. The simplification removes infrastructure work; it does not establish capture reliability or guarantee that four clips finish within 180 seconds. Keep FFmpeg and the live rehearsal.

## Stack after the change

React + TypeScript + Vite; CSS Modules; fetch polling; Python + FastAPI/Pydantic/Uvicorn; in-memory state and asyncio; Reactor SDK and HTTPX; model-compatible tokenizer; FFmpeg/ffprobe; local files; Caddy. Node/npm and uv manage dependencies. pytest/Ruff, TypeScript/ESLint, and one Playwright flow provide focused checks. VEED/fal is optional asset preparation only.

The [stack usage map](tech-stack.md#how-the-stack-is-used) assigns each technology to its part of the round. The single retry lives in the existing asyncio task and adds no infrastructure or retry dependency. A second failure becomes unavailable; rejected or uncertain sessions are never blindly retried.

## Future expansion

Reintroduce persistence when surviving restarts or storing history becomes a requirement; add a durable queue/shared admission controls for simultaneous rooms; move media to object storage for multiple hosts or longer retention. Explore five-to-eight-player groups only after cost, quota, capture, and screening tests. Display pairing, automated output review, dynamic hosts, and broader recovery tests follow demonstrated product needs.
