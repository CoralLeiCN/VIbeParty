from typing import Literal

from fastapi import APIRouter, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from backend.games.prompt_royale.engine import GAME_ID, Engine
from backend.shared.contracts import CloseResult, GameContext, SessionSummary, cookie_name

GAME_COOKIE = cookie_name(GAME_ID)
game_id = GAME_ID
available = True  # Fixture acceptance passed; live capacity defaults to zero.
router = APIRouter()
engine: Engine | None = None


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Create(Input):
    name: str = Field(max_length=100)
    passcode: str = Field(max_length=200)
    player_count: int = Field(default=3, ge=1, le=4, strict=True)


class Join(Input):
    name: str = Field(max_length=100)
    # Validate inside Engine.join, after its admission rate limiter.
    code: object = None


class HostCommand(Input):
    command_id: str = Field(min_length=1, max_length=80)
    expected_version: int
    round_id: str | None = None


class Topic(HostCommand):
    mode: str
    topic: str | None = None


class PlayerCount(HostCommand):
    player_count: int = Field(ge=1, le=4, strict=True)


class GenerationMode(HostCommand):
    mode: Literal["fixture", "live"]


class Confirm(HostCommand):
    suggestion_id: str


class Submission(Input):
    round_id: str
    prompt: str = Field(max_length=2000)


class Exclude(HostCommand):
    entry_id: str
    reason: str = Field(max_length=200)


class OpenVoting(HostCommand):
    watched: bool


class Vote(Input):
    round_id: str
    entry_id: str | None  # Explicit null means abstention, never an omitted field.


def token(request):
    return request.cookies.get(GAME_COOKIE)


def session_cookie(response, value):
    response.set_cookie(
        GAME_COOKIE, value, httponly=True, secure=False, samesite="lax", path="/", max_age=86400
    )


async def startup(context: GameContext) -> None:
    global engine
    engine = Engine(context)
    await engine.startup()


async def shutdown() -> None:
    if engine:
        await engine.shutdown()


async def session_summary(request: Request) -> SessionSummary | None:
    role = engine.summary(token(request)) if engine else None
    if not role:
        return None
    return SessionSummary(
        game_id=game_id,
        role=role,
        can_close=role == "host",
        continuation_url=f"/games/{game_id}/{'host' if role == 'host' else 'join'}",
    )


async def close_party(request: Request) -> CloseResult:
    closed = await engine.close(token(request))
    return CloseResult(
        status="closed" if closed else "closing",
        message="Party closed. Everyone will need to rejoin."
        if closed
        else "Provider closure needs operator verification. Switching is blocked.",
    )


@router.post("/room")
async def create_room(data: Create, request: Request, response: Response):
    value, state = await engine.create(
        token(request),
        data.name,
        data.passcode,
        request.client.host if request.client else "local",
        data.player_count,
    )
    session_cookie(response, value)
    return state


@router.post("/room/join")
async def join_room(data: Join, request: Request, response: Response):
    value, state = await engine.join(
        token(request), data.name, data.code, request.client.host if request.client else "local"
    )
    session_cookie(response, value)
    return state


@router.get("/room")
async def room_state(request: Request):
    return await engine.state(token(request))


@router.delete("/room")
async def delete_room(request: Request):
    return await close_party(request)


@router.post("/room/topic")
async def topic(data: Topic, request: Request):
    return await engine.mutate(token(request), "topic", data.model_dump())


@router.post("/room/player-count")
async def player_count(data: PlayerCount, request: Request):
    return await engine.mutate(token(request), "player-count", data.model_dump())


@router.post("/room/generation-mode")
async def generation_mode(data: GenerationMode, request: Request):
    return await engine.mutate(token(request), "generation-mode", data.model_dump())


@router.post("/room/topic/generate")
async def generate_topic(data: HostCommand, request: Request):
    return await engine.mutate(token(request), "generate-topic", data.model_dump())


@router.post("/room/topic/confirm")
async def confirm_topic(data: Confirm, request: Request):
    return await engine.mutate(token(request), "confirm-topic", data.model_dump())


@router.post("/room/start")
async def start(data: HostCommand, request: Request):
    return await engine.mutate(token(request), "start", data.model_dump())


@router.post("/round/submission")
async def submit(data: Submission, request: Request):
    return await engine.mutate(token(request), "submission", data.model_dump())


@router.post("/round/exclude")
async def exclude(data: Exclude, request: Request):
    return await engine.mutate(token(request), "exclude", data.model_dump())


@router.post("/round/open-voting")
async def open_voting(data: OpenVoting, request: Request):
    return await engine.mutate(token(request), "open-voting", data.model_dump())


@router.post("/round/vote")
async def vote(data: Vote, request: Request):
    return await engine.mutate(token(request), "vote", data.model_dump())


@router.post("/round/abort")
async def abort(data: HostCommand, request: Request):
    return await engine.mutate(token(request), "abort", data.model_dump())


@router.post("/round/again")
async def again(data: HostCommand, request: Request):
    return await engine.again(token(request), data.model_dump())


@router.get("/media/{opaque_id}")
async def media(opaque_id: str, request: Request):
    path = await engine.media(token(request), opaque_id)
    return FileResponse(
        path, media_type="video/mp4", headers={"Cache-Control": "private, no-store"}
    )
