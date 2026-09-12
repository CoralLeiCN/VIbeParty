# Word by Word: hackathon simplification

[All docs](../../README.md) · [Game spec](game-spec.md) · [Technical stack](tech-stack.md) · [Research](../../research/word-by-word/README.md)

Decision: 12 September 2026, following the instruction to prioritize a hackathon demonstration. The earlier specification planned a broader multiplayer MVP. The revised [game spec](game-spec.md) and [technical stack](tech-stack.md) now target one presenter running a short room successfully.

These changes update the design documents only; neither version has been implemented.

## Before and after

| Area | Before: broader MVP | After: hackathon demo |
| --- | --- | --- |
| Players | 3–8, flexible slot templates | 3–4, fixed join-order assignments |
| Contributions | 6–8 words: setting, character, action, prop, companion, consequence, optional adjective/weather | 4 words: place, character, action, consequence |
| Room operation | Multi-room-ready architecture, readiness, late arrivals, host migration | One room; host starts; no late joins or automatic migration |
| Shared viewing | Paired display plus synchronized video on phones | Host laptop is the shared screen; phones show forms/status/words |
| Reveal | Scheduled playback, automatic progression, one recovery window | Host presses Play/Next; native pause/replay |
| State machine | 8 phases with durable deadlines and terminal outcomes | 5 phases with in-process timers and a result label |
| State storage | PostgreSQL, SQLAlchemy, psycopg, Alembic | One in-memory Python room and one lock |
| Room updates | WebSockets and Redis pub/sub/presence | One-second HTTP polling |
| Server execution | API, scheduler/outbox, separate session controller with database leases | One FastAPI process and one async generation task |
| Video files | Private S3-compatible service and boto3 | Temporary files, served through an authorized route |
| Deployment | Docker Compose, Caddy, database, Redis, storage and server processes | One Dockerfile and one Railway service/replica |
| Generation limits | 270-second build phase; 300-second provider cap; budget reservation ledger | 120-second build; 180-second provider cap; one session and at most 3 live attempts per server run |
| Ambiguous provider commands | Stored command intent, reconciliation, lease recovery | Stop without retrying; replay the valid saved prefix |
| Late shutdown confirmation | Can abort a round even when usable video is saved | Saved clips remain playable; cleanup blocks only the next live session |
| Persistence | Reconnect and restart recovery; room/media retention jobs | Browser refresh works while the process lives; server restart loses the room |
| Replay | Saved segments, with optional edited exports later | Current round's saved segments only; clear on another round/reset |
| Validation | Broad unit/integration/contract/browser matrix and five multi-template live stories | Focused server checks and a short manual rehearsal on real phones and the host |
| VEED / Helios | Planned optional integrations/experiments | Deferred entirely from the demo build |

## What stays

The point of the game is unchanged: **private Consequences-style contributions become visible additions to one evolving scene**. Preserve actual player words, cumulative scene facts, ordered disclosure, provider credentials on the backend, and replay without another generation.

Reactor FastH3 and FFmpeg remain because they serve the central video experience. A database and distributed services solve scale/recovery requirements that the one-room demonstration does not need. The shorter four-step chain also reduces generation and capture work, but actual latency and cost still require measurement.

## Accepted limitations

- The demo needs the host screen; phones are not independent synchronized video viewers.
- A process crash or redeploy ends the room and requires rejoining. The presenter must resolve the old provider session before another live run.
- Clip files and the three-attempt counter are temporary. There is no durable spending ledger, gallery, or saved history.
- Fixture mode is labelled and tied to its example words. A failed live round never silently turns into a prerecorded success.
- Additive continuity and capture remain real integration gates. Removing infrastructure does not prove that the model will retain the scene.

## New build priority

First, produce and replay one four-word live chain after closing Reactor. Second, add the host screen and three/four phone inputs. Third, rehearse privacy, duplicate actions, a timeout, and a rematch. Build the larger multiplayer platform only after the demonstration works.
