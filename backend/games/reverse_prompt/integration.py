from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.shared.api import AttemptLimiter
from backend.shared.contracts import CloseResult, GameContext, SessionSummary, cookie_name
from backend.shared.errors import AppError
from backend.shared.room_codes import RoomCode

from .game import GAME, Game

game_id = GAME
available = True
router = APIRouter()
game: Game | None = None
limiter = AttemptLimiter()
COOKIE = cookie_name(GAME)


class CreateBody(BaseModel):
    organizer_code: str = Field(max_length=200)
    name: str = Field(max_length=100)
    mode: Literal["rehearsal", "live"] = "rehearsal"


class JoinBody(BaseModel):
    code: RoomCode = Field(default="", validate_default=True)
    name: str = Field(max_length=100)


class RoundBody(BaseModel):
    round_id: str


class SubmissionBody(RoundBody):
    phase: Literal["author_input", "relay_input", "guessing"]
    step: int = Field(ge=0, le=2)
    submission_id: UUID
    text: str = Field(max_length=2000)


def token(request):
    return request.cookies.get(COOKIE)


def issue(response, player):
    response.set_cookie(
        COOKIE, player.token, httponly=True, secure=False, samesite="strict", path="/"
    )
    return {"role": player.role}


async def limit_admission(request: Request):
    limiter.check(request.client.host if request.client else "local")


@router.post("/room", dependencies=[Depends(limit_admission)])
async def create(body: CreateBody, request: Request, response: Response):
    player = await game.create(token(request), body.organizer_code, body.name, body.mode)
    return issue(response, player)


@router.post("/join", dependencies=[Depends(limit_admission)])
async def join(body: JoinBody, request: Request, response: Response):
    player = await game.join(token(request), body.code, body.name)
    return issue(response, player)


@router.get("/state")
async def state(request: Request):
    if not token(request):
        raise AppError(401, "session_required", "Join a party to begin.")
    return await game.snapshot(token(request))


@router.post("/start")
async def start(body: RoundBody, request: Request):
    return await game.start(token(request), body.round_id)


@router.post("/submit")
async def submit(body: SubmissionBody, request: Request):
    return await game.submit(token(request), body)


@router.post("/reset")
async def reset(body: RoundBody, request: Request):
    return await game.reset(token(request), body.round_id)


@router.api_route("/media/{media_id}", methods=["GET", "HEAD"])
async def media(media_id: str, request: Request):
    async with game.lock:
        player = game.member(token(request))
        allowed = game.allowed_media(player, game.room.round)
        descriptor = next((m for m in allowed if m["id"] == media_id), None)
        if descriptor is None:
            raise AppError(404, "media_unavailable", "This clip is not available on your turn.")
        path = descriptor["path"]
    return FileResponse(
        path, media_type="video/mp4", headers={"Cache-Control": "private, no-store"}
    )


async def startup(context: GameContext) -> None:
    global game, limiter
    limiter = AttemptLimiter()
    game = Game(context)
    await game.startup()


async def shutdown() -> None:
    if game:
        await game.shutdown()


async def session_summary(request: Request) -> SessionSummary | None:
    if not game:
        return None
    async with game.lock:
        try:
            player = game.member(token(request))
        except AppError:
            return None
        host = player.role == "A"
        return SessionSummary(
            game_id=GAME,
            role="host" if host else "player",
            continuation_url=f"/games/{GAME}/{'host' if host else 'join'}",
            can_close=host,
        )


async def close_party(request: Request) -> CloseResult:
    async with game.lock:
        game.host(token(request))
        round_id = game.room.round.id
    await game.reset(token(request), round_id, close=True)
    # Give ordinary fixture cleanup one scheduling turn, while preserving bounded requests.
    if game.cleanup:
        await asyncio_wait_cleanup()
    return CloseResult(
        status="closing" if game.room else "closed",
        message="Finishing the previous session."
        if game.room
        else "Party closed. Everyone will need to rejoin.",
    )


async def asyncio_wait_cleanup():
    import asyncio

    await asyncio.wait({game.cleanup}, timeout=0.05)
