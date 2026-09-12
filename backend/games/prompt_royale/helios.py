"""Game-owned Helios capture. Session closure is verified independently of the SDK."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx

from backend.games.prompt_royale.config import RoyaleSettings
from backend.games.prompt_royale.media import prepare
from backend.games.prompt_royale.providers import ProviderFailure

API = "https://api.reactor.inc"
VERSION_HEADERS = {"Reactor-API-Version": "1", "Reactor-API-Accept-Version": "1"}
log = logging.getLogger(__name__)


@dataclass
class OwnedSession:
    jwt: str
    id: str | None = None
    confirmed_closed: bool = False


@dataclass
class SavedRecording:
    playlist: str
    jwt: str
    runway: int = 30  # Ten-second download + twenty-second preparation, no new session.


async def confirm_closed(client: httpx.AsyncClient, session: OwnedSession) -> bool:
    if session.confirmed_closed:
        return True
    if not session.id:
        return False  # Ambiguous creation requires an operator, never a replacement.
    headers = {**VERSION_HEADERS, "Authorization": f"Bearer {session.jwt}"}
    url = f"{API}/sessions/{session.id}"
    try:
        async with asyncio.timeout(8):
            response = await client.get(url, headers=headers)
            if response.status_code == 404 or (
                response.status_code == 200
                and response.json().get("state") in {"INACTIVE", "CLOSED"}
            ):
                session.confirmed_closed = True
                return True
            response.raise_for_status()
            response = await client.delete(url, headers=headers)
            if response.status_code == 404:
                session.confirmed_closed = True
                return True
            response.raise_for_status()
            # A DELETE response alone does not establish the final state.
            for _ in range(5):
                response = await client.get(url, headers=headers)
                if response.status_code == 404 or (
                    response.status_code == 200
                    and response.json().get("state") in {"INACTIVE", "CLOSED"}
                ):
                    session.confirmed_closed = True
                    return True
                response.raise_for_status()
                await asyncio.sleep(0.3)
    except Exception:
        return False
    return False


async def download_recording(client, recording: SavedRecording, target: Path):
    origin = urlsplit(recording.playlist)
    if origin.scheme != "https" or not (
        origin.hostname == "reactor.inc" or (origin.hostname or "").endswith(".reactor.inc")
    ):
        raise ProviderFailure("Unexpected recording origin")
    headers = {"Authorization": f"Bearer {recording.jwt}"}
    async with asyncio.timeout(10):
        while True:
            async with client.stream("GET", recording.playlist, headers=headers) as response:
                if response.status_code == 202:
                    delay = float(response.headers.get("retry-after", 1))
                    await asyncio.sleep(min(2, max(0.2, delay)))
                    continue
                response.raise_for_status()
                data = bytearray()
                async for block in response.aiter_bytes():
                    data.extend(block)
                    if len(data) > 65536:
                        raise ProviderFailure("Manifest exceeds size limit")
                break
        segments = []
        init = None
        for line in data.decode().splitlines():
            line = line.strip()
            if line.startswith("#EXT-X-MAP:"):
                match = re.search(r'URI="([^"]+)"', line)
                if match:
                    init = match.group(1)
            elif line and not line.startswith("#"):
                segments.append(line)
        if not segments or len(segments) > 100:
            raise ProviderFailure("Invalid recording manifest")
        if not init and any(urlsplit(s).path.endswith(".m4s") for s in segments):
            raise ProviderFailure("Recording initialization segment is missing")
        if init:
            segments.insert(0, init)
        total = 0
        with target.open("wb") as output:
            for segment in segments:
                url = urljoin(recording.playlist, segment)
                parsed = urlsplit(url)
                if parsed.scheme != "https":
                    raise ProviderFailure("Invalid recording segment URL")
                auth = headers if parsed.netloc == origin.netloc else {}
                async with client.stream("GET", url, headers=auth) as response:
                    response.raise_for_status()
                    async for block in response.aiter_bytes():
                        total += len(block)
                        if total > 100 * 1024 * 1024:
                            raise ProviderFailure("Recording exceeds 100 MiB")
                        output.write(block)
        return total


class HeliosVideo:
    live = True

    def __init__(self, settings: RoyaleSettings, journal: Path, transport=None):
        self.settings = settings
        self.journal = journal
        self.transport = transport
        self.sessions: list[OwnedSession] = []
        self.orphaned = journal.exists()
        self.failed_closure = False
        self.last_evidence: dict = {}

    @property
    def uncertain(self):
        return self.orphaned or self.failed_closure

    def _persist(self):
        pending = [s.id for s in self.sessions if not s.confirmed_closed]
        if self.orphaned:
            return
        if pending:
            self.journal.parent.mkdir(parents=True, exist_ok=True)
            # No tokens or prompts on disk. Unknown IDs still block restart admission.
            self.journal.write_text(json.dumps({"pending_sessions": pending}) + "\n")
            self.journal.chmod(0o600)
        else:
            self.journal.unlink(missing_ok=True)

    async def close(self):
        async with httpx.AsyncClient(timeout=4, transport=self.transport) as client:
            for session in self.sessions:
                if not session.confirmed_closed:
                    await confirm_closed(client, session)
        self.failed_closure = any(not s.confirmed_closed for s in self.sessions)
        self._persist()
        return not self.uncertain

    async def generate(self, prompt, seed, target, index, status, source=None):
        source_path = target.with_suffix(".source.mp4")
        recording = source if isinstance(source, SavedRecording) else None
        if isinstance(source, Path):
            source_path = source
        elif recording:
            try:
                async with httpx.AsyncClient(
                    timeout=5, transport=self.transport, follow_redirects=True
                ) as client:
                    await download_recording(client, recording, source_path)
            except (httpx.HTTPError, TimeoutError) as error:
                raise ProviderFailure(
                    "Recording download failed", transient=True, source=recording
                ) from error
        else:
            if self.uncertain:
                raise ProviderFailure("Provider closure is unresolved", uncertain=True)
            await status("generating")
            from reactor_sdk import Reactor
            from reactor_sdk.errors import (
                BadRequestError,
                NetworkError,
                RateLimitedError,
                RecorderDisabledError,
                RequestTimeoutError,
                ServerError,
                UnauthorizedError,
            )

            session = None
            reactor = None
            failure = None
            cancelled = False
            received = asyncio.Event()
            stamps = []
            started = time.monotonic()
            evidence = {"seed": seed, "model": "reactor/helios", "sr_scale": "2x", "cap": 60}
            async with httpx.AsyncClient(
                timeout=5, transport=self.transport, follow_redirects=True
            ) as client:
                try:
                    async with asyncio.timeout(60):
                        response = await client.post(
                            API + "/tokens",
                            headers={"Reactor-API-Key": self.settings.reactor_api_key},
                            json={
                                "expires_after": 300,
                                "authorization_details": [
                                    {
                                        "type": "session",
                                        "resources": {"models": {"match": ["reactor/helios"]}},
                                        "constraints": {
                                            "max_sessions": 1,
                                            "max_session_duration_seconds": 60,
                                        },
                                    }
                                ],
                            },
                        )
                        response.raise_for_status()
                        token = response.json()
                        if float(token["expires_at"]) < time.time() + 80:
                            raise ProviderFailure(
                                "Token expires before the bounded capture can finish"
                            )
                        session = OwnedSession(token["jwt"])
                        self.sessions.append(session)
                        self._persist()  # Before any potentially paid creation.
                        reactor = Reactor(model_name="reactor/helios", jwt=session.jwt)

                        def known_id(value):
                            if value:
                                session.id = value
                                self._persist()

                        reactor.on("session_id_changed", known_id)

                        def frame(_pixels, _width, _height, _id, timestamp_us, _metadata):
                            if timestamp_us:
                                stamps.append(timestamp_us)
                                if stamps[-1] - stamps[0] >= 6_000_000:
                                    received.set()

                        reactor.track("main_video").on_raw_frame(frame)
                        await reactor.connect()
                        known_id(reactor.session_id)
                        evidence["ready_seconds"] = round(time.monotonic() - started, 3)
                        await reactor.send_command("set_sr_scale", {"sr_scale": "2x"})
                        await reactor.send_command("set_seed", {"seed": seed})
                        await reactor.send_command("set_prompt", {"prompt": prompt})
                        await reactor.send_command("start", {})
                        await received.wait()
                        evidence["received_frames"] = len(stamps)
                        evidence["media_seconds"] = (stamps[-1] - stamps[0]) / 1_000_000
                        clip = await reactor.request_recording()
                        recording = SavedRecording(clip.playlist_url, session.jwt)
                        evidence["source_bytes"] = await download_recording(
                            client, recording, source_path
                        )
                except asyncio.CancelledError:
                    cancelled = True
                except Exception as error:
                    failure = error
                    if (
                        session
                        and not session.id
                        and isinstance(
                            error, (RateLimitedError, UnauthorizedError, BadRequestError)
                        )
                    ):
                        session.confirmed_closed = True  # Explicit rejected creation, no session.
                finally:
                    if reactor:
                        with contextlib.suppress(Exception, asyncio.CancelledError):
                            await asyncio.wait_for(reactor.disconnect(), 3)
                        reactor.close()
                    if session:
                        # Keep the task alive through bounded independent closure, even on cancel.
                        closing = asyncio.create_task(confirm_closed(client, session))
                        with contextlib.suppress(asyncio.CancelledError):
                            await asyncio.shield(closing)
                        if not closing.done():
                            await closing
                        evidence["session_id"] = session.id
                        evidence["confirmed_closed"] = session.confirmed_closed
                    self._persist()
                    evidence["capture_seconds"] = round(time.monotonic() - started, 3)
                    self.last_evidence = evidence
                    log.info("Helios capture evidence %s", evidence)
                if session and not session.confirmed_closed:
                    self.failed_closure = True
                    raise ProviderFailure(
                        "Session closure needs operator verification", uncertain=True
                    )
                if cancelled:
                    raise asyncio.CancelledError
                if failure:
                    if isinstance(failure, ProviderFailure):
                        raise failure
                    if isinstance(
                        failure, (RecorderDisabledError, BadRequestError, UnauthorizedError)
                    ):
                        raise ProviderFailure(
                            "Provider rejected this entry or configuration"
                        ) from failure
                    transient = isinstance(
                        failure,
                        (
                            httpx.TransportError,
                            TimeoutError,
                            NetworkError,
                            RequestTimeoutError,
                            ServerError,
                            RateLimitedError,
                        ),
                    )
                    if isinstance(failure, httpx.HTTPStatusError):
                        transient = failure.response.status_code in {429, 500, 502, 503, 504}
                    delay = (getattr(failure, "retry_after_ms", None) or 2000) / 1000
                    raise ProviderFailure(
                        "Capture failed", transient=transient, source=recording, retry_after=delay
                    ) from failure
        await status("preparing")
        try:
            await prepare(
                source_path,
                target,
                self.settings.prompt_royale_ffmpeg,
                self.settings.prompt_royale_ffprobe,
            )
        except TimeoutError as error:
            raise ProviderFailure(
                "Preparation timed out", transient=True, source=source_path
            ) from error
        source_path.unlink(missing_ok=True)
        return target
