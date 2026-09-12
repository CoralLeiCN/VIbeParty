from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.shared.config import ROOT


class GameSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    reactor_api_key: SecretStr = SecretStr("")
    organizer_code: SecretStr | None = None
    reverse_prompt_live_enabled: bool = False
