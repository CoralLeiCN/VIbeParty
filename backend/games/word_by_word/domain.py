"""Word by Word rules. Public snapshots are built explicitly, never from dataclasses."""

import re
import secrets
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from backend.shared.errors import AppError

GAME_ID = "word-by-word"
CATEGORIES = ("Place", "Character", "Action", "Consequence")
QUESTIONS = (
    "Where does the story happen?",
    "Who appears in the story?",
    "What do they do?",
    "What surprising thing happens next?",
)
FIXTURE_TEXT = (
    "a moonlit forest",
    "a fox in a tiny hat",
    "They start breakdancing.",
    "Confetti rains from the sky.",
)
# Unicode White_Space property, shared with the phone's counter (not normalization).
WHITESPACE = (
    "\t\n\v\f\r \x85\xa0\u1680"
    + "".join(map(chr, range(0x2000, 0x200B)))
    + "\u2028\u2029\u202f\u205f\u3000"
)
FILTER_VERSION = "word-by-word-input-v1"
DEFAULT_DISALLOWED = ("nazi", "rape", "pornography")


def identifier() -> str:
    return secrets.token_urlsafe(18)


def validate_text(raw: str, disallowed: tuple[str, ...] = DEFAULT_DISALLOWED) -> str:
    text = raw.strip(WHITESPACE)
    if not 1 <= len(text) <= 120:
        raise AppError(422, "invalid_contribution", "Write between 1 and 120 characters.", "text")
    if any(0xD800 <= ord(char) <= 0xDFFF for char in text):
        raise AppError(422, "invalid_contribution", "Use valid Unicode text.", "text")
    checked = unicodedata.normalize("NFKC", text).casefold()
    if any(
        re.search(r"(?<!\w)" + re.escape(word.casefold()) + r"(?!\w)", checked)
        for word in disallowed
        if word
    ):
        raise AppError(
            422, "filtered_contribution", "Try a different idea for this contribution.", "text"
        )
    return text


@dataclass
class Player:
    token: str
    name: str


@dataclass
class Slot:
    index: int
    owner: str
    text: str | None = None


@dataclass
class Clip:
    path: Path
    duration: float
    width: int
    height: int


@dataclass
class Round:
    id: str = field(default_factory=identifier)
    phase: str = "LOBBY"
    mode: str = "fixture"
    slots: list[Slot] = field(default_factory=list)
    clips: list[Clip] = field(default_factory=list)
    disclosed: int = -1
    input_deadline: float | None = None
    generation_deadline: float | None = None
    result: str | None = None
    message: str = ""


@dataclass
class Room:
    host: str
    code: str
    player_count: int = 3
    players: list[Player] = field(default_factory=list)
    round: Round = field(default_factory=Round)
    activity: float = field(default_factory=time.time)
    closing: bool = False
    maintenance: bool = False
    revision: int = 0

    def touch(self, now: float) -> None:
        self.activity = now
        self.revision += 1

    def role(self, token: str | None) -> str | None:
        if token and secrets.compare_digest(token, self.host):
            return "host"
        if token and any(secrets.compare_digest(token, player.token) for player in self.players):
            return "player"
        return None

    def card(self, slot: Slot) -> dict:
        player = next(player for player in self.players if player.token == slot.owner)
        return {
            "index": slot.index,
            "category": CATEGORIES[slot.index],
            "text": slot.text,
            "contributor": player.name,
        }

    def snapshot(
        self,
        token: str,
        now: float,
        public_origin: str,
        provider_closing: bool,
        attempts_left: int,
        live_reason: str | None,
    ) -> dict:
        role = self.role(token)
        if not role:
            raise AppError(401, "session_expired", "This party has ended. Join again to play.")
        r = self.round
        result = {
            "role": role,
            "code": self.code,
            "round_id": r.id,
            "revision": self.revision,
            "phase": r.phase,
            "mode": r.mode,
            "server_time": now,
            "players": [player.name for player in self.players],
            "player_count": self.player_count,
            "join_url": f"{public_origin}/games/word-by-word/join?code={self.code}",
            "collected": sum(slot.text is not None for slot in r.slots),
            "saved_clips": len(r.clips),
            "disclosed_index": r.disclosed,
            "cards": [self.card(slot) for slot in r.slots[: r.disclosed + 1]],
            "input_deadline": r.input_deadline,
            "generation_deadline": r.generation_deadline,
            "result": r.result,
            "message": r.message,
            "provider_closing": provider_closing,
            "closing": self.closing,
            "busy": self.maintenance,
            "live_attempts_left": attempts_left,
            "live_unavailable_reason": live_reason,
        }
        if role == "host":
            result["clips"] = [
                {
                    "index": index,
                    "url": f"/api/games/{GAME_ID}/clips/{r.id}/{index}",
                    "duration": clip.duration,
                }
                for index, clip in enumerate(r.clips[: r.disclosed + 1])
            ]
        else:
            result["your_name"] = next(
                player.name for player in self.players if player.token == token
            )
            result["assignments"] = [
                {
                    "index": slot.index,
                    "category": CATEGORIES[slot.index],
                    "question": QUESTIONS[slot.index],
                    "example": FIXTURE_TEXT[slot.index],
                    "accepted_text": slot.text,
                    "fixture_text": FIXTURE_TEXT[slot.index] if r.mode == "fixture" else None,
                }
                for slot in r.slots
                if slot.owner == token
            ]
        return result
