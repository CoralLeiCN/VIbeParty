# Shared application contract — foundation v1

Session A owns this contract, all shared code/configuration and dependencies. Game owners replace their stubs after the foundation commit. Scope: one Python 3.13/FastAPI process, one React 19 build, local HTTP, one active party, in-memory game state. No live provider is imported or contacted by shell startup.

## Backend exports

Each `backend/games/<underscore_id>/integration.py` exports:

```python
game_id: str                    # word-by-word | prompt-royale | reverse-prompt
available: bool                 # True only after integrated playable fixture checks
router: fastapi.APIRouter       # unprefixed suffixes; shell adds game namespace
async def startup(context: GameContext) -> None: ...
async def shutdown() -> None: ...
async def session_summary(request: Request) -> SessionSummary | None: ...
async def close_party(request: Request) -> CloseResult: ...
```

`backend.shared.contracts` exports GameContext(settings: Settings, parties: PartyCoordinator), SessionSummary(game_id, role: host|player, continuation_url, can_close=False), CloseResult(status: closed|closing, message), cookie_name(game_id). Playing hosts use role=host/can_close=True; the game owns their player identity. The game stores context at startup, owns all background tasks, and closes them at shutdown. Discovery authenticates without updating presence/inactivity, serializing game state, or clearing cookies. Games validate role on every action and media/range request.

Cookie names are `vp_word_by_word`, `vp_prompt_royale`, `vp_reverse_prompt`. Set Path=/ so discovery can read them, HttpOnly=True, Secure=False on trusted HTTP; SameSite=Lax for Word/ Royale, Strict for Reverse. Tokens are opaque; names/codes never grant a role. Per-worktree browser profiles isolate same-host cookies (ports do not).

`backend.shared.errors.AppError(status, code, message, field=None)` emits `{code,message,field?}`. Statuses: 401 missing session, 403 forbidden/origin, 404 expired/wrong code, 409 phase/admission/cleanup conflict, 415 JSON required, 422 validation, 429 attempts, 503 unavailable. Never put secret input in errors. Games own domain reasons. All API responses are no-store. Same-origin JSON mutations require Origin matching configured browser/public origins, with a 64KiB shared body bound. For DELETE send an empty JSON body.

## Party admission and lifecycle

`context.parties` exposes async `reserve(game_id)` context manager, `public_state()`, `resolve(code)`, `rotate_code(game_id)`, `begin_close(game_id)`, `finish_close(game_id)`, `set_blocker(key, message_or_none)`.

Authenticate and handle same-game repeat entry first. Then `async with parties.reserve(game_id) as reservation:` creates an exclusive starting claim. Construct the game room under its own lock; release that lock and `await reservation.activate()` using `reservation.code` in the new room. Failed/unactivated creation releases the claim. If activation itself fails, roll back the game room. The coordinator lock is held only inside its methods, never across caller work. Do not hold the coordinator lock yourself or hold both locks at once. No provider/file I/O while holding a room lock. The game must reject actions while its own closing state is true; no action can race cleanup.

`rotate_code` returns a different four-digit code and retires the old lookup without releasing admission; call during a game reset while own admission is blocked. No resolution authorizes game entry: the game validates the final code again. For close: authenticate host, mark game closing under own lock, release lock, begin_close, cancel/await owned work, independently confirm provider closure, clear private round files/roster/sessions, then finish_close. Return closed only after release; otherwise return closing and retain the host's ability to retry closure. Repeated close must be safe. Never release on unconfirmed cancellation. Expiry uses the same guarded cleanup. Discovery/public state do not extend timers. Back to games is navigation only.

Persistent unresolved provider state found at startup must call `set_blocker(game_id, explanation)`; clear only with proven resolution. It blocks new party admission across games even after a restart. Game attempt counters survive party close; Reverse Prompt campaign quota is persistent and never replenished by reset/worktree creation.

## Shared APIs and examples

- GET `/api/games`: `{games:[{id,available}]}`. Unready modules stay routable but unavailable for hosting.
- GET `/api/session`: authorized summary only, no roster/private text/media. Failure is an HTTP/network error, never anonymous success.
- POST `/api/party/resolve` with `{code}`: rate limit 20 attempts/minute/client IP including invalid formats, trim then require exactly four ASCII digits as a string; response `{game_id,join_url}` only. Malformed or missing code returns422 invalid_room_code; a valid but missing/closing room returns404 party_unavailable. No membership granted.
- POST `/api/party/close` with `{game_id?}` (portal sends the expected game to reject stale confirmations) delegates host auth/cleanup to current game; returns CloseResult.

```json
{"status":"anonymous","reason":"no_session","party":null}
{"status":"authenticated","session":{"game_id":"word-by-word","role":"host","continuation_url":"/games/word-by-word/host","can_close":true},"party":{"game_id":"word-by-word","status":"active"}}
{"status":"authenticated","session":{"game_id":"reverse-prompt","role":"player","continuation_url":"/games/reverse-prompt/join","can_close":false},"party":{"game_id":"reverse-prompt","status":"active"}}
{"status":"anonymous","reason":"expired","party":null}
{"status":"anonymous","reason":"no_session","party":{"game_id":"prompt-royale","status":"active"}}
{"code":"another_game_active","message":"Close the current party before starting a new one."}
{"code":"cleanup_pending","message":"Close the current party before starting a new one."}
{"game_id":"prompt-royale","join_url":"/games/prompt-royale/join?code=0042"}
```

A stale known cookie produces expired; no cookie produces no_session. Public party metadata contains game_id/status only. A host must authorize against the game session before close even if this metadata is visible.

## Exact game route mapping

Replace `/api` in the game specs with the following prefixes. Export router suffixes only.

| Game prefix | Exact method + suffixes |
| --- | --- |
| `/api/games/word-by-word` | POST `/host`, POST `/join`, GET `/state`, POST `/round/start`, POST `/contribution`, POST `/reveal/next`, GET `/clips/{round_id}/{index}`, POST `/round/end`, POST `/round/new`, POST `/room/reset` |
| `/api/games/prompt-royale` | POST `/room`, POST `/room/join`, GET `/room`, POST `/room/topic`, POST `/room/topic/generate`, POST `/room/topic/confirm`, POST `/room/start`, POST `/round/submission`, POST `/round/exclude`, POST `/round/open-voting`, POST `/round/vote`, POST `/round/abort`, POST `/round/again`, DELETE `/room`, GET `/media/{opaque_id}` |
| `/api/games/reverse-prompt` | POST `/room`, POST `/join`, GET `/state`, POST `/start`, POST `/submit`, POST `/reset`, GET `/media/{media_id}` |

Additional game routes stay namespaced and are recorded in game API examples. Existing unprefixed game APIs are not global aliases.

## Frontend exports

Each `frontend/src/games/<hyphen-id>/index.tsx` exports `GameRoute({entry}: GameEntryProps)` with `entry: 'host'|'join'`. GameRoute renders its own passcode/name admission, authorized current phase, lobby/replay and game errors. Query code comes from React Router's useSearchParams. Use `GameShell({title,children})` or provide a visible React Router Link to `/` labelled Back to games. No portal visit resets a party or generates media.

Routes: `/`, `/join`, `/games/<id>/host`, `/games/<id>/join?code=…`; `/host` redirects to Word by Word host, `/join?code=…` resolves legacy code-only links. Same frontend shell is served for direct loads/refresh.

`shared/api.ts`: `apiFetch<T>(url, options?: RequestInit): Promise<T>`, `apiPost<T>(url, body={}): Promise<T>`, ApiError(status,code,message,field?). Uses same-origin credentials, JSON bodies, supports AbortSignal, throws typed HTTP errors and native transport errors.

`shared/usePolling.ts`: `usePolling<T>(url: string|null, intervalMs=1000): {data?:T,error?:Error,loading:boolean,retry:()=>void}`. One poll in flight with a 10-second transport timeout; abort/discard obsolete requests on URL/unmount; focus/online wake it; hidden pages pause routine polls; keep last data during reconnect. Do not remount videos on a transient error. The game owns the snapshot and whether its game poll refreshes presence. Portal discovery polls every 5s and never refreshes game presence.

`shared/contracts.ts` exports GameId, GameEntryProps, PartySummary, SessionSummary, SessionDiscovery, GameAvailability. Portal owns local descriptive catalog; backend owns runtime availability. Props added later must be optional until all consumers merge.

## Configuration and commands

See [environment setup](../../environment-setup.md). uv.lock/package-lock.json pin actual resolved versions; provider/scorer optional dependencies are added only after the native spikes pass. `Settings` loads root .env then environment overrides; game-local BaseSettings may load the same file with extra=ignore for domain variables. Secrets never enter frontend config. `media_dir(game_id)` resolves to private per-worktree clips. No private path is mounted statically. Quota/model files remain outside media.

Development A=8000/5173, B=8011/5174, C=8012/5175, D=8013/5176. Combined demo uses `bash scripts/demo.sh`, one worker, no reload, 0.0.0.0:8000 and configured LAN public/browser origin. Remote deployment deferred. FFmpeg + ffprobe must be installed before video trials.

The coordinator records exclusive paid slots in `docs/development/live-provider-slots.md`. Slot transfer requires attempt counts and independently confirmed provider closure; uncertainty blocks transfer. Integrate committed game milestones with normal merges preserving ancestry; owners then merge the latest integration branch before their next milestone.

Optional `ADDITIONAL_BROWSER_ORIGINS` is a JSON array of explicitly trusted HTTP origins (default[]). Use only for local development aliases needing independent cookie stores, e.g. localhost,127.0.0.1 and LAN address with the frontend port. No wildcards, paths, credentials or query components. The normal combined demo needs only its LAN public/browser origin.

`shared/clipboard.ts` exports `copyText(text: string): Promise<boolean>`. Call from a user click; it tries the browser Clipboard API, then the selected-text copy command for trusted local HTTP. A false result requires a visible instruction to select/copy the displayed join address. Do not silently report success or require HTTPS for LAN joining.

## Four-digit room codes (accepted update)

The [shared standard](../../shared/room-code-spec.md) applies to every game. Backend exports from `backend.shared.room_codes`: `RoomCode` is a Pydantic annotated string with a before-validator; `normalize_room_code(value: object) -> str` rejects non-strings and anything other than trimmed `[0-9]{4}` with422 `invalid_room_code`, field `code`, message `Enter a 4-digit room code.` Constants `FORMAT_MESSAGE` and `UNAVAILABLE_MESSAGE` hold the exact shared copy. No integer conversion, uppercase conversion, padding or truncation is permitted.

`async with context.parties.reserve(game_id) as reservation:` now allocates a secure four-digit `reservation.code` while holding the admission lock. Build your local room using that string, then `await reservation.activate()` with no argument. The one-active-party policy ensures cross-game uniqueness. Call `await context.parties.rotate_code(game_id)` only for a party reset that clears its roster; it returns a different code and atomically retires the old lookup, retrying random collisions. Same-roster rounds keep their code. Resolve/close remain coordinator-owned. Game create/join rate limits remain game-owned.

Frontend `frontend/src/shared/RoomCodeInput.tsx` exports `RoomCodeInput`, `normalizeRoomCode(value: string): string | null`, `ROOM_CODE_FORMAT_MESSAGE` and `ROOM_CODE_UNAVAILABLE_MESSAGE`. The component accepts ordinary controlled input props/ref, while fixing text type, numeric keyboard, ASCII pattern, no autocapitalization and0042 placeholder. Keep the game's `Room code` label and layout. Use `noValidate` on the join form and call `normalizeRoomCode` before the request so surrounding whitespace works and invalid input displays the exact shared message; name/other validation remains game-owned. Do not set maxLength, transform the value while typing, or auto-join from a link. Preserve raw invalid input for correction and prefill the query string.

All three consumers are migrated. Explicit code overrides and update_code have been removed: only the coordinator can allocate or rotate an entry code.
