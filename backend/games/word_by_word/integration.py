"""The Word by Word boundary consumed by the shared application."""

from fastapi import APIRouter, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.shared.api import AttemptLimiter
from backend.shared.contracts import CloseResult, GameContext, SessionSummary, cookie_name

from .domain import GAME_ID
from .service import Game

game_id = GAME_ID
available = True
router = APIRouter()
game: Game
limiter: AttemptLimiter
COOKIE = cookie_name(GAME_ID)


class HostBody(BaseModel):
    passcode: str = Field(max_length=200)


class JoinBody(BaseModel):
    # Keep the raw value until the endpoint has counted this join attempt.
    code: object = None
    name: str = Field(max_length=200)


class RoundBody(BaseModel):
    round_id: str = Field(min_length=1, max_length=100)


class StartBody(RoundBody):
    mode: str = "fixture"


class PlayerCountBody(RoundBody):
    player_count: int = Field(strict=True, ge=1, le=4)


class ContributionBody(RoundBody):
    slot_index: int = Field(ge=0, le=3)
    text: str = Field(max_length=4096)


class RevealBody(RoundBody):
    expected_reveal_index: int = Field(ge=-1, le=3)


def token(request: Request) -> str | None:
    return request.cookies.get(COOKIE)


def limit(request: Request, action: str) -> None:
    limiter.check(f"{action}:{request.client.host if request.client else 'local'}")


def session_cookie(response: Response, value: str) -> None:
    response.set_cookie(COOKIE, value, httponly=True, samesite="lax", secure=False, path="/")


async def startup(context: GameContext) -> None:
    global game, limiter
    game = Game(context)
    limiter = AttemptLimiter()
    await game.startup()


async def shutdown() -> None:
    await game.shutdown()


async def session_summary(request: Request) -> SessionSummary | None:
    async with game.lock:
        role = game.room.role(token(request)) if game.room else None
        if not role:
            return None
        return SessionSummary(
            game_id=GAME_ID,
            role=role,
            continuation_url=f"/games/{GAME_ID}/{'host' if role == 'host' else 'join'}",
            can_close=role == "host",
        )


async def close_party(request: Request) -> CloseResult:
    # Authorization is required even for a repeated close; public metadata grants nothing.
    async with game.lock:
        game.authenticate(token(request), host=True)
    closed = await game.close(token(request))
    return CloseResult(
        status="closed" if closed else "closing",
        message="Party closed. Everyone will need to rejoin."
        if closed
        else "Finishing the previous session. Saved replay is kept until cleanup completes.",
    )


@router.post("/host")
async def host(body: HostBody, request: Request, response: Response):
    limit(request, "host")
    value, snapshot = await game.host(body.passcode, token(request))
    session_cookie(response, value)
    return snapshot


@router.post("/join")
async def join(body: JoinBody, request: Request, response: Response):
    limit(request, "join")
    value, snapshot = await game.join(body.code, body.name, token(request))
    session_cookie(response, value)
    return snapshot


@router.get("/state")
async def state(request: Request):
    await game.tick()
    async with game.lock:
        return game.snapshot(token(request))


@router.post("/round/start")
async def start(body: StartBody, request: Request):
    return await game.start(token(request), body.round_id, body.mode)


@router.post("/room/settings")
async def room_settings(body: PlayerCountBody, request: Request):
    return await game.set_player_count(token(request), body.round_id, body.player_count)


@router.post("/contribution")
async def contribution(body: ContributionBody, request: Request):
    limit(request, "contribution:" + (token(request) or "anonymous"))
    return await game.contribute(token(request), body.round_id, body.slot_index, body.text)


@router.post("/reveal/next")
async def reveal(body: RevealBody, request: Request):
    return await game.reveal(token(request), body.round_id, body.expected_reveal_index)


@router.post("/round/end")
async def end(body: RoundBody, request: Request):
    return await game.end(token(request), body.round_id)


@router.post("/round/new")
async def new_round(body: RoundBody, request: Request):
    return await game.new_round(token(request), body.round_id)


@router.post("/room/reset")
async def reset(body: RoundBody, request: Request):
    return await game.new_round(token(request), body.round_id, reset=True)


@router.post("/provider/cleanup")
async def cleanup(body: RoundBody, request: Request):
    return await game.retry_cleanup(token(request), body.round_id)


@router.get("/clips/{round_id}/{index}")
async def clip(round_id: str, index: int, request: Request):
    path = await game.clip_path(token(request), round_id, index)
    return FileResponse(path, media_type="video/mp4", headers={"Cache-Control": "no-store"})
