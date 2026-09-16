from pathlib import Path
from urllib.parse import urlsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
GAME_IDS = ("word-by-word", "prompt-royale", "reverse-prompt")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    backend_port: int = 8000
    frontend_port: int = 5173
    public_origin: str = "http://localhost:8000"
    browser_origin: str = "http://localhost:8000"
    additional_browser_origins: tuple[str, ...] = ()
    generation_mode: str = "fixture"
    local_mode: bool = True
    host_passcode: str = "WMHACK"
    media_root: Path = Path(".local/vibeparty")
    reverse_prompt_quota_file: Path = Path(".local/vibeparty-persistent/reverse-prompt/quota.json")
    embedding_model_path: Path = Path(".local/vibeparty-persistent/models/all-MiniLM-L6-v2")

    @field_validator("public_origin", "browser_origin")
    @classmethod
    def origin_only(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise ValueError("Use an HTTP origin without a path")
        _ = parsed.port  # Validate the optional numeric port.
        return value.rstrip("/")

    @field_validator("additional_browser_origins")
    @classmethod
    def additional_origins(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(cls.origin_only(value) for value in values)

    @field_validator("media_root", "reverse_prompt_quota_file", "embedding_model_path")
    @classmethod
    def worktree_path(cls, value: Path) -> Path:
        return (ROOT / value).resolve() if not value.is_absolute() else value.resolve()

    def media_dir(self, game_id: str) -> Path:
        if game_id not in GAME_IDS:
            raise ValueError("Unknown game")
        return self.media_root / game_id / "clips"

    @property
    def allowed_origins(self) -> set[str]:
        return {self.public_origin, self.browser_origin, *self.additional_browser_origins}
