from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.shared.config import ROOT


class RoyaleSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    reactor_api_key: str = ""
    openai_api_key: str = ""
    prompt_royale_live_enabled: bool = False
    prompt_royale_rehearsed_capacity: int = Field(default=0, ge=0, le=4)
    prompt_royale_live_session_starts: int = Field(default=16, ge=0, le=16)
    prompt_royale_live_slot: str = ""
    prompt_royale_topic_mode: Literal["fixture", "live"] = "fixture"
    prompt_royale_topic_calls: int = Field(default=16, ge=0, le=16)
    prompt_royale_tokenizer: Path = ROOT / ".local/vibeparty/prompt-royale/tokenizer/tokenizer.json"
    prompt_royale_ffmpeg: str = "ffmpeg"
    prompt_royale_ffprobe: str = "ffprobe"

    @field_validator("prompt_royale_tokenizer")
    @classmethod
    def tokenizer_path(cls, value: Path) -> Path:
        return (ROOT / value).resolve() if not value.is_absolute() else value.resolve()


TOPICS = [
    "The worst possible first day at a new job.",
    "A hotel with one very unusual rule.",
    "The world's least useful superhero.",
    "A restaurant that takes its name too literally.",
    "A completely unnecessary invention.",
    "An unexpected guest at a royal banquet.",
]
FIXTURE_TOPICS = [
    "A space station with a very unusual pet.",
    "A robot trying its first human hobby.",
    "A museum where every exhibit has stage fright.",
]
TOKENIZER_SHA = "af904105ce1071b1202bba0059a841f4a7b85b48b6ec179c4948e3483476e0dd"
TOKENIZER_REVISION = "66cb9e7e85526fe440a945569e42c72fb6cbc0ad"
