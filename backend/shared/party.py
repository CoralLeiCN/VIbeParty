import asyncio
import secrets
from contextlib import asynccontextmanager
from dataclasses import dataclass

from backend.shared.errors import AppError
from backend.shared.room_codes import UNAVAILABLE_MESSAGE, generate_room_code, normalize_room_code


@dataclass
class Party:
    game_id: str
    token: str
    status: str = "starting"
    code: str | None = None


class Reservation:
    def __init__(self, coordinator: "PartyCoordinator", party: Party):
        self.coordinator = coordinator
        self.party = party

    @property
    def code(self) -> str:
        assert self.party.code is not None
        return self.party.code

    async def activate(self) -> None:
        async with self.coordinator.lock:
            if self.coordinator.party is not self.party or self.party.status != "starting":
                raise AppError(409, "party_changed", "The party changed. Please try again.")
            self.party.status = "active"


class PartyCoordinator:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.party: Party | None = None
        self.blockers: dict[str, str] = {}

    @asynccontextmanager
    async def reserve(self, game_id: str):
        async with self.lock:
            if self.blockers:
                raise AppError(409, "cleanup_pending", next(iter(self.blockers.values())))
            if self.party:
                code = (
                    "cleanup_pending" if self.party.status == "closing" else "another_game_active"
                )
                raise AppError(409, code, "Close the current party before starting a new one.")
            party = Party(
                game_id=game_id, token=secrets.token_urlsafe(16), code=generate_room_code()
            )
            self.party = party
        try:
            yield Reservation(self, party)
        finally:
            async with self.lock:
                if self.party is party and party.status == "starting":
                    self.party = None

    async def public_state(self) -> dict | None:
        async with self.lock:
            return (
                {"game_id": self.party.game_id, "status": self.party.status} if self.party else None
            )

    async def resolve(self, code: str) -> str:
        code = normalize_room_code(code)
        async with self.lock:
            if not self.party or self.party.status != "active" or self.party.code != code:
                raise AppError(
                    404,
                    "party_unavailable",
                    UNAVAILABLE_MESSAGE,
                    "code",
                )
            return self.party.game_id

    async def begin_close(self, game_id: str) -> None:
        async with self.lock:
            if not self.party or self.party.game_id != game_id:
                raise AppError(409, "party_changed", "This party has ended.")
            self.party.status = "closing"

    async def finish_close(self, game_id: str) -> None:
        async with self.lock:
            if self.party and self.party.game_id == game_id and self.party.status == "closing":
                self.party = None

    async def set_blocker(self, key: str, message: str | None) -> None:
        async with self.lock:
            if message is None:
                self.blockers.pop(key, None)
            else:
                self.blockers[key] = message

    async def rotate_code(self, game_id: str) -> str:
        async with self.lock:
            if not self.party or self.party.game_id != game_id or self.party.status != "active":
                raise AppError(409, "party_changed", "The party is no longer active.")
            self.party.code = generate_room_code([normalize_room_code(self.party.code)])
            return self.party.code
