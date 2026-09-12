"""One room-code contract for portal resolution and game admission."""

import re
import secrets
from collections.abc import Collection
from typing import Annotated

from pydantic import BeforeValidator

from backend.shared.errors import AppError

FORMAT_MESSAGE = "Enter a 4-digit room code."
UNAVAILABLE_MESSAGE = "That party isn't available. Check the code with your host."


def normalize_room_code(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}", value.strip()):
        raise AppError(422, "invalid_room_code", FORMAT_MESSAGE, "code")
    return value.strip()


RoomCode = Annotated[str, BeforeValidator(normalize_room_code)]


def generate_room_code(exclude: Collection[str] = ()) -> str:
    """Caller reserves atomically; exclusions support collision-safe code rotation."""
    excluded = set(exclude)
    for _ in range(1000):
        code = f"{secrets.randbelow(10000):04d}"
        if code not in excluded:
            return code
    raise AppError(503, "code_unavailable", "Couldn't create a room code. Please try again.")
