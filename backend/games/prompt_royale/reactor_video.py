"""Bounded Reactor sessions, diagnostics, preparation and independently verified closure."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from uuid import uuid4

import httpx

from backend.games.prompt_royale.config import RoyaleSettings
from backend.games.prompt_royale.media import prepare
from backend.games.prompt_royale.providers import ProviderFailure

API = "https://api.reactor.inc"
VERSION_HEADERS = {"Reactor-API-Version": "1", "Reactor-API-Accept-Version": "1"}
log = logging.getLogger(__name__)


def error_details(error: BaseException) -> list[dict]:
    """Retain useful error identities without provider payloads, URLs or credentials."""
    details = []
    seen = set()
    while error is not None and id(error) not in seen and len(details) < 5:
        seen.add(id(error))
        detail = {"type": type(error).__name__}
        if isinstance(error, httpx.HTTPStatusError):
            detail["http_status"] = error.response.status_code
        else:
            # SDK errors include structured fields that do not contain request data.
            code = getattr(error, "code", None)
            if isinstance(code, str) and re.fullmatch(r"[A-Z_]{1,64}", code):
                detail["code"] = code
            status = getattr(error, "status", None)
            if isinstance(status, int) and 100 <= status <= 599:
                detail["http_status"] = status
            delay = getattr(error, "retry_after_ms", None)
            if isinstance(delay, (int, float)) and 0 <= delay <= 3_600_000:
                detail["retry_after_ms"] = delay
        details.append(detail)
        error = error.__cause__ or error.__context__
    return details


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


class ReactorVideo:
    model_name: str
    preset: dict = {}
    live = True

    def __init__(
        self,
        settings: RoyaleSettings,
        journal: Path,
        transport=None,
        *,
        startup_timeout: int | None = None,
        startup_mode: str = "sdk",
        connection_observer=None,
    ):
        # Standalone startup experiments may wait longer than a game's 180-second
        # round. The game uses the default, bounded 60-second capture lifecycle.
        if startup_timeout is not None and not 1 <= startup_timeout <= 600:
            raise ValueError("Startup timeout must be between 1 and 600 seconds")
        if startup_mode not in {"sdk", "rest"}:
            raise ValueError("Startup mode must be sdk or rest")
        self.settings = settings
        self.journal = journal
        self.transport = transport
        self.startup_timeout = startup_timeout
        self.startup_mode = startup_mode
        self.connection_observer = connection_observer
        self.session_cap = (startup_timeout or 0) + 60
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

    async def _create_and_wait(self, client, session, evidence):
        """Standalone experiment: avoid the SDK's fixed 20-poll startup limit."""
        from reactor_sdk import __version__

        headers = {**VERSION_HEADERS, "Authorization": f"Bearer {session.jwt}"}
        evidence["stage"] = "create_session"
        response = await client.post(
            API + "/sessions",
            headers=headers,
            json={
                "model": {"name": self.model_name},
                "client_info": {"sdk_version": __version__, "sdk_type": "python"},
                "supported_transports": [{"protocol": "webrtc", "version": "1.0"}],
            },
        )
        if response.status_code in {400, 401, 403, 404, 409, 422, 429}:
            session.confirmed_closed = True  # Explicit rejected creation.
        response.raise_for_status()
        session.id = response.json()["session_id"]
        self._persist()
        evidence["stage"] = "wait_for_runtime"
        delay = 0.2
        while True:
            response = await client.get(API + f"/sessions/{session.id}", headers=headers)
            response.raise_for_status()
            descriptor = response.json()
            state = descriptor.get("state")
            if state in {
                "CREATED",
                "PENDING",
                "SUSPENDED",
                "WAITING",
                "ACTIVE",
                "INACTIVE",
                "CLOSED",
            }:
                evidence["provider_state"] = state
            evidence["readiness_polls"] = evidence.get("readiness_polls", 0) + 1
            if state in {"INACTIVE", "CLOSED"}:
                session.confirmed_closed = True
                raise ProviderFailure("Session ended before runtime readiness")
            if (
                descriptor.get("capabilities") is not None
                and descriptor.get("selected_transport") is not None
            ):
                return
            await asyncio.sleep(delay)
            delay = min(10, delay * 2)

    async def generate(self, prompt, seed, target, index, status, source=None):
        evidence = {
            "attempt_id": uuid4().hex,
            "started_at": time.time(),
            "round_id": target.parent.name,
            "entry_id": target.stem,
            "model": self.model_name,
            "seed": seed,
            **self.preset,
            "cap": self.session_cap,
            "startup_timeout": self.startup_timeout,
            "startup_mode": self.startup_mode,
            "stage": "initializing",
            "received_frames": 0,
            "zero_timestamp_frames": 0,
            "timestamped_frames": 0,
            "model_events": {},
            "outcome": "failed",
        }
        self.last_evidence = evidence
        started = time.monotonic()
        try:
            result = await self._generate(prompt, seed, target, index, status, source, evidence)
            evidence.update(stage="complete", outcome="ready")
            return result
        except BaseException as error:
            evidence["errors"] = error_details(error)
            if isinstance(error, asyncio.CancelledError):
                evidence["outcome"] = "cancelled"
            raise
        finally:
            evidence["elapsed_seconds"] = round(time.monotonic() - started, 3)
            self.last_evidence = evidence
            directory = self.journal.parent / "diagnostics"
            try:
                directory.mkdir(parents=True, exist_ok=True, mode=0o700)
                path = directory / f"{evidence['attempt_id']}.json"
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "w") as output:
                    json.dump(evidence, output, indent=2)
                    output.write("\n")
            except OSError:
                log.error("Could not save Reactor capture diagnostics")
            level = logging.INFO if evidence["outcome"] == "ready" else logging.WARNING
            log.log(level, "Reactor capture evidence %s", evidence)

    def record_frame(self, evidence, timestamp_us, started):
        received_seconds = time.monotonic() - started
        evidence["received_frames"] += 1
        evidence.setdefault("first_frame_seconds", received_seconds)
        evidence["last_frame_seconds"] = received_seconds
        key = "timestamped_frames" if timestamp_us else "zero_timestamp_frames"
        evidence[key] += 1
        return received_seconds

    async def _capture(self, reactor, client, session, path, prompt, seed, evidence, started):
        raise NotImplementedError

    async def _generate(self, prompt, seed, target, index, status, source, evidence):
        source_path = target.with_suffix(".source.mp4")
        recording = source if isinstance(source, SavedRecording) else None
        if isinstance(source, Path):
            source_path = source
        elif recording:
            evidence["stage"] = "download_recording"
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
            started = time.monotonic()
            async with httpx.AsyncClient(
                timeout=5, transport=self.transport, follow_redirects=True
            ) as client:
                try:
                    async with asyncio.timeout(self.session_cap) as lifecycle:
                        evidence["stage"] = "token"
                        response = await client.post(
                            API + "/tokens",
                            headers={"Reactor-API-Key": self.settings.reactor_api_key},
                            json={
                                "expires_after": max(300, self.session_cap + 120),
                                "authorization_details": [
                                    {
                                        "type": "session",
                                        "resources": {"models": {"match": [self.model_name]}},
                                        "constraints": {
                                            "max_sessions": 1,
                                            "max_session_duration_seconds": self.session_cap,
                                        },
                                    }
                                ],
                            },
                        )
                        response.raise_for_status()
                        token = response.json()
                        if float(token["expires_at"]) < time.time() + self.session_cap + 20:
                            raise ProviderFailure(
                                "Token expires before the bounded capture can finish"
                            )
                        session = OwnedSession(token["jwt"])
                        self.sessions.append(session)
                        self._persist()  # Before any potentially paid creation.
                        reactor = Reactor(model_name=self.model_name, jwt=session.jwt)

                        def known_id(value):
                            if value:
                                session.id = value
                                self._persist()

                        reactor.on("session_id_changed", known_id)

                        def message(value):
                            # Model event names identify command rejection without saving payloads.
                            kind = value.get("type") if isinstance(value, dict) else None
                            if isinstance(kind, str) and re.fullmatch(r"[a-z_]{1,64}", kind):
                                events = evidence["model_events"]
                                if kind in events or len(events) < 32:
                                    events[kind] = events.get(kind, 0) + 1

                        def sdk_error(error):
                            evidence["sdk_errors"] = error_details(error)

                        def connection_status(value):
                            if isinstance(value, str) and re.fullmatch(r"[a-z_]{1,64}", value):
                                changes = evidence.setdefault("connection_states", [])
                                if len(changes) < 32:
                                    changes.append(
                                        {
                                            "state": value,
                                            "seconds": round(time.monotonic() - started, 3),
                                        }
                                    )
                                if self.connection_observer:
                                    self.connection_observer(value)

                        reactor.on("message", message)
                        reactor.on("error", sdk_error)
                        reactor.on("status_changed", connection_status)

                        evidence["stage"] = "connect"
                        if self.startup_timeout is None:
                            await reactor.connect()
                        else:
                            async with asyncio.timeout(self.startup_timeout):
                                if self.startup_mode == "rest":
                                    await self._create_and_wait(client, session, evidence)
                                    evidence["runtime_ready_seconds"] = round(
                                        time.monotonic() - started, 3
                                    )
                                    evidence["stage"] = "connect"
                                    # Same token and session; SDK adoption creates no replacement.
                                    # confirm_closed() owns termination of the adopted session.
                                    await reactor.connect(session_id=session.id)
                                else:
                                    await reactor.connect()
                            lifecycle.reschedule(asyncio.get_running_loop().time() + 60)
                        known_id(reactor.session_id)
                        evidence["ready_seconds"] = round(time.monotonic() - started, 3)
                        recording = await self._capture(
                            reactor, client, session, source_path, prompt, seed, evidence, started
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
        evidence["stage"] = "prepare_mp4"
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
