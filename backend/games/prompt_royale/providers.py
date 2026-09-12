import asyncio
import shutil
from pathlib import Path

import httpx

from backend.games.prompt_royale.config import FIXTURE_TOPICS, RoyaleSettings
from backend.games.prompt_royale.validation import normalized

FIXTURES = Path(__file__).parent / "fixtures"
TOPIC_MODEL = "gpt-4.1-mini-2025-04-14"
TOPIC_INSTRUCTION = (
    "Suggest exactly one playful topic for friends to interpret as a five-second silent scene. "
    "Use one sentence, at most 20 words. Keep it suitable for a general audience. "
    "No personal names, brands, politics, explanations, markdown, or quotation marks. "
    "Return only the topic; do not write the scene itself."
)


class ProviderFailure(Exception):
    def __init__(
        self,
        reason: str,
        *,
        transient: bool = False,
        uncertain: bool = False,
        source: object | None = None,
        retry_after: float = 2,
    ):
        super().__init__(reason)
        self.transient = transient
        self.uncertain = uncertain
        self.source = source
        self.retry_after = max(2, retry_after)


class FixtureVideo:
    live = False
    uncertain = False

    async def generate(
        self, prompt: str, seed: int, target: Path, index: int, status, source: Path | None = None
    ) -> Path:
        await status("generating")
        await asyncio.sleep(0.35)
        await status("preparing")
        shutil.copyfile(FIXTURES / f"{index % 4}.mp4", target)
        return target

    async def close(self) -> bool:
        return True


class Topics:
    def __init__(self, settings: RoyaleSettings, transport=None):
        self.settings = settings
        self.calls = 0
        self.fixture_index = 0
        self.transport = transport

    async def suggest(self) -> str:
        if self.settings.prompt_royale_topic_mode == "fixture":
            topic = FIXTURE_TOPICS[self.fixture_index % len(FIXTURE_TOPICS)]
            self.fixture_index += 1
            await asyncio.sleep(0.15)
            return topic
        if not self.settings.openai_api_key:
            raise ProviderFailure("Topic provider key is not configured. Choose a bundled topic.")
        if self.calls >= self.settings.prompt_royale_topic_calls:
            raise ProviderFailure(
                "Topic suggestion allowance is exhausted. Choose a bundled topic."
            )
        self.calls += 1  # No refunds, including timeouts; never retry HTTP automatically.
        try:
            async with asyncio.timeout(10):
                async with httpx.AsyncClient(timeout=10, transport=self.transport) as client:
                    response = await client.post(
                        "https://api.openai.com/v1/responses",
                        headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
                        json={
                            "model": TOPIC_MODEL,
                            "input": TOPIC_INSTRUCTION,
                            "max_output_tokens": 64,
                            "store": False,
                        },
                    )
                    response.raise_for_status()
                    if len(response.content) > 16384:
                        raise ValueError("Oversized topic response")
                    data = response.json()
                    if data.get("status") != "completed":
                        raise ValueError("Incomplete topic")
                    values = [
                        c["text"]
                        for item in data.get("output", [])
                        if item.get("type") == "message"
                        for c in item.get("content", [])
                        if c.get("type") == "output_text"
                    ]
                    if len(values) != 1 or "\n" in values[0].strip():
                        raise ValueError("Expected one topic")
                    return normalized(values[0], 160, "topic")
        except asyncio.CancelledError:
            raise
        except Exception as error:
            raise ProviderFailure(
                "Topic suggestion failed. Try again or choose a bundled topic."
            ) from error
