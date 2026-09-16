import time
from collections import defaultdict, deque
from urllib.parse import urlencode

from fastapi import APIRouter, Request
from pydantic import BaseModel

from backend.shared.config import GAME_IDS
from backend.shared.contracts import GameId, cookie_name
from backend.shared.errors import AppError
from backend.shared.room_codes import normalize_room_code

router = APIRouter()


class ResolveBody(BaseModel):
    code: object = None


class AttemptLimiter:
    def __init__(self):
        self.attempts: dict[str, deque] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time.monotonic()
        for old_key in list(self.attempts):
            if not self.attempts[old_key] or self.attempts[old_key][-1] <= now - 60:
                del self.attempts[old_key]
        bucket = self.attempts[key]
        while bucket and bucket[0] <= now - 60:
            bucket.popleft()
        if len(bucket) >= 20:
            raise AppError(429, "too_many_attempts", "Too many attempts. Try again in a minute.")
        bucket.append(now)


@router.get("/config")
async def config(request: Request):
    return {"local_mode": request.app.state.settings.local_mode}


@router.get("/session")
async def session(request: Request):
    party = await request.app.state.parties.public_state()
    if party:
        game = request.app.state.games[party["game_id"]]
        summary = await game.session_summary(request)
        if summary:
            return {"status": "authenticated", "session": summary.model_dump(), "party": party}
    expired = any(request.cookies.get(cookie_name(game)) for game in GAME_IDS)
    return {"status": "anonymous", "reason": "expired" if expired else "no_session", "party": party}


@router.get("/games")
async def games(request: Request):
    return {
        "games": [
            {"id": g.game_id, "available": g.available} for g in request.app.state.games.values()
        ]
    }


@router.post("/party/resolve")
async def resolve(body: ResolveBody, request: Request):
    request.app.state.resolve_limiter.check(request.client.host if request.client else "local")
    code = normalize_room_code(body.code)
    game_id = await request.app.state.parties.resolve(code)
    return {
        "game_id": game_id,
        "join_url": f"/games/{game_id}/join?{urlencode({'code': code})}",
    }


class CloseBody(BaseModel):
    game_id: GameId | None = None


@router.post("/party/close")
async def close(body: CloseBody, request: Request):
    party = await request.app.state.parties.public_state()
    if not party:
        raise AppError(404, "party_unavailable", "This party has ended.")
    if body.game_id and body.game_id != party["game_id"]:
        raise AppError(409, "party_changed", "The active party changed. Refresh before closing it.")
    game = request.app.state.games[party["game_id"]]
    result = await game.close_party(request)
    # The game authenticates, performs cleanup, and releases admission only on confirmed closure.
    return result.model_dump()
