import hashlib
import unicodedata
from pathlib import Path

from backend.games.prompt_royale.config import TOKENIZER_SHA
from backend.shared.errors import AppError


def normalized(value: str, maximum: int, field: str) -> str:
    value = unicodedata.normalize("NFC", value.strip())
    if any(unicodedata.category(character) == "Cs" for character in value):
        raise AppError(422, "invalid_text", "Use valid Unicode text.", field)
    if not 1 <= len(value) <= maximum:
        raise AppError(422, "invalid_length", f"Use 1–{maximum} characters.", field)
    return value


def rendered(topic: str, prompt: str) -> str:
    return f"Topic: {topic}\nScene description: {prompt}\nRender one continuous shot of this scene."


class HeliosPromptValidator:
    def __init__(self, path: Path):
        self.tokenizer = None
        if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == TOKENIZER_SHA:
            from tokenizers import Tokenizer

            self.tokenizer = Tokenizer.from_file(str(path))
            self.tokenizer.no_truncation()

    def validate(self, topic: str, value: str) -> tuple[str, int]:
        prompt = normalized(value, 500, "prompt")
        if self.tokenizer is None:
            raise AppError(503, "tokenizer_missing", "Install the verified Helios tokenizer first.")
        count = len(self.tokenizer.encode(rendered(topic, prompt)).ids)
        if count > 500:
            raise AppError(
                422,
                "prompt_tokens",
                "Scene and topic exceed 500 model tokens. Shorten your scene.",
                "prompt",
            )
        return prompt, count


class PromptValidator:
    """FastH3 limits the full wire prompt to 800 characters."""

    def validate(self, topic: str, value: str) -> tuple[str, int]:
        prompt = normalized(value, 500, "prompt")
        count = len(rendered(topic, prompt))
        if count > 800:
            raise AppError(
                422,
                "prompt_size",
                "Scene and topic exceed FastH3's 800-character limit. Shorten your scene.",
                "prompt",
            )
        return prompt, count
