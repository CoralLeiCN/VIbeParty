"""LingBot World 2: one session, four cumulative prompts, one continuous stream."""

import asyncio
import base64
import contextlib
import json
import time
from pathlib import Path
from urllib.parse import quote

import httpx
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.shared.config import ROOT

from .domain import Clip
from .providers import Update, scene_prompt
from .stream import StreamCapture

API = "https://api.reactor.inc"
MODEL = "reactor/lingbot-world-2"
SESSION_HEADERS = {"Reactor-API-Version": "1", "Reactor-API-Accept-Version": "1"}


class LiveSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    reactor_api_key: SecretStr = SecretStr("")
    openai_api_key: SecretStr = SecretStr("")
    word_by_word_live_enabled: bool = False
    word_by_word_image_model: str = "gpt-image-2.5-flare"
    word_by_word_seed_image: Path | None = None
    word_by_word_category_seconds: float = Field(default=6, ge=3, le=15)

    def seed_path(self) -> Path | None:
        path = self.word_by_word_seed_image
        return (ROOT / path).resolve() if path and not path.is_absolute() else path

    def unavailable_reason(self) -> str | None:
        if not self.word_by_word_live_enabled:
            return "The presenter has not enabled live LingBot World 2 generation."
        if not self.reactor_api_key.get_secret_value().startswith("rk_"):
            return "The presenter must configure the Reactor credential before live play."
        if self.seed_path():
            if not self.seed_path().is_file():
                return "The configured starting image could not be found."
        elif not self.openai_api_key.get_secret_value():
            return "Configure OPENAI_API_KEY to create the starting scene, or a local seed image."
        return None


class LingBotProvider:
    def __init__(
        self,
        settings: LiveSettings,
        *,
        client_factory=None,
        reactor_factory=None,
        capture_factory=StreamCapture,
        evidence_path: Path | None = None,
    ):
        self.settings = settings
        self.client_factory = client_factory or (lambda: httpx.AsyncClient(timeout=10))
        self.reactor_factory = reactor_factory
        self.capture_factory = capture_factory
        self.evidence_path = evidence_path
        self.reactor = None
        self.capture = None
        self.recording: Clip | None = None
        self.jwt = None
        self.session_id = None
        self.connect_started = False
        self.closed = False
        self.failure = None
        self.events: dict[str, int] = {}
        self.changed = asyncio.Event()
        self.evidence = {"model": MODEL, "steps": [], "closed": False}

    async def starting_image(self, place: str, directory: Path) -> Path:
        configured = self.settings.seed_path()
        if configured:
            if not 0 < configured.stat().st_size <= 20 * 1024 * 1024:
                raise ValueError("invalid_seed_image_size")
            self.evidence["seed_source"] = "configured"
            return configured
        # Only Place enters image generation. No character, action or consequence leaks.
        prompt = (
            "Create a starting scene for an illustrated party story. Wide establishing shot, "
            "playful illustration, room for a character to enter later. No text or captions. "
            "Depict only this setting, without adding a main character or story event. "
            f"Place: {place}"
        )
        async with self.client_factory() as client:
            async with client.stream(
                "POST",
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {self.settings.openai_api_key.get_secret_value()}"
                },
                json={
                    "model": self.settings.word_by_word_image_model,
                    "prompt": prompt,
                    "size": "1536x1024",
                    "quality": "low",
                    "output_format": "png",
                    "n": 1,
                },
                timeout=60,
            ) as response:
                response.raise_for_status()
                payload = bytearray()
                async for block in response.aiter_bytes():
                    payload.extend(block)
                    if len(payload) > 28 * 1024 * 1024:
                        raise ValueError("seed_response_too_large")
        data = base64.b64decode(json.loads(payload)["data"][0]["b64_json"], validate=True)
        if not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data) > 20 * 1024 * 1024:
            raise ValueError("invalid_seed_image")
        destination = directory / "seed.png"
        await asyncio.to_thread(destination.write_bytes, data)
        self.evidence["seed_source"] = "place_generated"
        return destination

    def session_changed(self, value):
        if value:
            self.session_id = value
            self.evidence["session_id"] = value

    def message(self, message):
        kind = message.get("type")
        if kind in {"command_error", "error"}:
            self.failure = "provider_rejected_command"
        if isinstance(kind, str):
            self.events[kind] = self.events.get(kind, 0) + 1
        self.changed.set()

    def on_error(self, *_):
        self.failure = "provider_session_failed"
        self.changed.set()

    def check(self):
        if self.failure:
            raise RuntimeError(self.failure)
        if self.capture:
            self.capture.check()

    async def command(self, name, data, acknowledgment=None):
        self.evidence["stage"] = name
        self.check()
        before = self.events.get(acknowledgment, 0)
        async with asyncio.timeout(15):
            reply = await self.reactor.send_command(name, data)
            if acknowledgment and (not reply or reply.get("type") != acknowledgment):
                while self.events.get(acknowledgment, 0) <= before:
                    self.changed.clear()
                    self.check()
                    await self.changed.wait()
            self.check()
        return reply

    async def open(self):
        self.evidence["stage"] = "connect"
        if self.connect_started:
            raise RuntimeError("session_already_attempted")
        async with self.client_factory() as client:
            response = await client.post(
                API + "/tokens",
                headers={"Reactor-API-Key": self.settings.reactor_api_key.get_secret_value()},
                json={
                    "expires_after": 900,
                    "authorization_details": [
                        {
                            "type": "session",
                            "resources": {"models": {"match": [MODEL]}},
                            "constraints": {"max_sessions": 1, "max_session_duration_seconds": 180},
                        }
                    ],
                },
            )
            response.raise_for_status()
            self.jwt = response.json()["jwt"]
        factory = self.reactor_factory
        if factory is None:
            from reactor_sdk import Reactor

            factory = Reactor
        self.reactor = factory(model_name=MODEL, jwt=self.jwt)
        self.reactor.on("session_id_changed", self.session_changed)
        self.reactor.on("message", self.message)
        self.reactor.on("error", self.on_error)
        self.reactor.track("main_video").on_raw_frame(self.capture.accept)
        self.connect_started = True
        await self.reactor.connect()
        self.session_changed(self.reactor.session_id)
        if not self.session_id:
            raise RuntimeError("session_identity_unknown")

    async def wait_until(self, seconds):
        while self.capture.seconds < seconds:
            self.check()
            await asyncio.sleep(0.02)

    async def run(self, texts: list[str], directory: Path, update: Update) -> Clip:
        directory.mkdir(parents=True, exist_ok=True)
        image = await self.starting_image(texts[0], directory)
        self.capture = self.capture_factory(directory)
        try:
            await self.open()
            self.evidence["stage"] = "upload_image"
            reference = await self.reactor.upload_file(image)
            await self.command("set_image", {"image": reference}, "image_accepted")
            await self.command("set_prompt", {"prompt": scene_prompt(texts, 0)}, "prompt_accepted")
            # Navigation stays idle. The players direct scene content with text.
            self.capture.start()
            await self.command("start", {}, "generation_started")
            async with asyncio.timeout(30):
                await self.capture.ready()
            await update(0, 0)
            self.evidence["steps"].append({"index": 0, "at_seconds": 0})
            last = 0.0
            for index in range(1, 4):
                await self.wait_until(last + self.settings.word_by_word_category_seconds)
                await self.command(
                    "set_prompt", {"prompt": scene_prompt(texts, index)}, "prompt_accepted"
                )
                last = self.capture.seconds
                self.evidence["steps"].append({"index": index, "at_seconds": last})
                await update(index, last)
            await self.wait_until(last + self.settings.word_by_word_category_seconds)
            await self.command("pause", {}, "generation_paused")
            self.evidence["stage"] = "generation_completed"
        finally:
            # Preserve received video even if a later command fails. This is media
            # processing, with no model-quality judgment or regeneration.
            if self.capture:
                if self.capture.frames:
                    with contextlib.suppress(Exception):
                        self.recording = await self.capture.finish()
                else:
                    await self.capture.stop()
        if self.recording is None:
            raise RuntimeError("recording_unavailable")
        return self.recording

    async def terminal(self, client):
        response = await client.get(
            f"{API}/sessions/{quote(self.session_id, safe='')}",
            headers={**SESSION_HEADERS, "Authorization": f"Bearer {self.jwt}"},
        )
        if response.status_code == 404:
            return True
        response.raise_for_status()
        data = response.json()
        return data.get("session_id", self.session_id) == self.session_id and data.get("state") in {
            "CLOSED",
            "INACTIVE",
        }

    async def close(self) -> bool:
        if self.closed:
            return True
        if self.capture:
            await self.capture.stop()
        if self.reactor:
            with contextlib.suppress(Exception):
                await asyncio.wait_for(self.reactor.disconnect(), 5)
        try:
            if not self.connect_started:
                self.closed = True
            elif self.session_id and self.jwt:
                async with self.client_factory() as client:
                    if not await self.terminal(client):
                        response = await client.delete(
                            f"{API}/sessions/{quote(self.session_id, safe='')}",
                            headers={**SESSION_HEADERS, "Authorization": f"Bearer {self.jwt}"},
                        )
                        if response.status_code != 404:
                            response.raise_for_status()
                        self.closed = await self.terminal(client)
                    else:
                        self.closed = True
            if self.closed and self.reactor:
                self.reactor.close()
            return self.closed
        finally:
            self.evidence["closed"] = self.closed
            self.evidence["finished_at"] = time.time()
            if self.evidence_path:
                self.evidence_path.parent.mkdir(parents=True, exist_ok=True)
                self.evidence_path.write_text(json.dumps(self.evidence, indent=2) + "\n")
                self.evidence_path.chmod(0o600)
