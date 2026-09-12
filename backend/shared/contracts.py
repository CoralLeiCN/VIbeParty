from dataclasses import dataclass
from typing import Literal, Protocol

from fastapi import APIRouter, Request
from pydantic import BaseModel

from backend.shared.config import Settings
from backend.shared.party import PartyCoordinator

GameId = Literal["word-by-word", "prompt-royale", "reverse-prompt"]


class SessionSummary(BaseModel):
    game_id: GameId
    role: Literal["host", "player"]
    continuation_url: str
    can_close: bool = False


class CloseResult(BaseModel):
    status: Literal["closed", "closing"]
    message: str = "Party closed. Everyone will need to rejoin."


@dataclass
class GameContext:
    settings: Settings
    parties: PartyCoordinator


class GameIntegration(Protocol):
    game_id: str
    available: bool
    router: APIRouter

    async def startup(self, context: GameContext) -> None: ...
    async def shutdown(self) -> None: ...
    async def session_summary(self, request: Request) -> SessionSummary | None: ...
    async def close_party(self, request: Request) -> CloseResult: ...


def cookie_name(game_id: str) -> str:
    return "vp_" + game_id.replace("-", "_")
