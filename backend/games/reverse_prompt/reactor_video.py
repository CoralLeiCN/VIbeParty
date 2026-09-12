"""One fresh Helios session per prompt, with independently proven closure."""

import asyncio
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx

from .frame_capture import FrameCapture
from .media import MAX_SOURCE, validate
from .quota import Quota

API = "https://api.reactor.inc"
INSTRUCTION = (
    "A single continuous shot depicting the described scene. No captions or on-screen text."
)
HEADERS = {"Reactor-API-Version": "1", "Reactor-API-Accept-Version": "1"}


class GenerationError(RuntimeError):
    pass


async def download_recording(client, clip, jwt: str, destination: Path):
    """Ordered init + media fragments, bounded memory/disk and cancellable I/O."""
    base = clip.playlist_url
    origin = urlsplit(API).netloc

    def headers(url):
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.username or parsed.password:
            raise GenerationError("Invalid recording URL")
        return {"Authorization": f"Bearer {jwt}"} if parsed.netloc == origin else {}

    async def fetch(url, limit):
        # Never forward the token to a signed CDN or follow an unchecked redirect.
        async with client.stream("GET", url, headers=headers(url)) as response:
            if response.status_code == 202:
                return None
            response.raise_for_status()
            chunks = bytearray()
            async for chunk in response.aiter_bytes(65536):
                if len(chunks) + len(chunk) > limit:
                    raise GenerationError("Recording exceeds the media limit")
                chunks.extend(chunk)
            return bytes(chunks)

    while True:
        body = await fetch(base, 1024 * 1024)
        if body is not None:
            break
        await asyncio.sleep(0.5)
    text = body.decode()
    if not text.startswith("#EXTM3U") or "#EXT-X-KEY" in text or "#EXT-X-STREAM-INF" in text:
        raise GenerationError("Unsupported recording playlist")
    segments = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#EXT-X-MAP:"):
            match = re.search(r'URI="([^"]+)"', line)
            if not match:
                raise GenerationError("Missing recording init")
            segments.append(urljoin(base, match[1]))
        elif line and not line.startswith("#"):
            segments.append(urljoin(base, line))
    if not 1 <= len(segments) <= 100:
        raise GenerationError("Invalid recording segments")
    size = 0
    with destination.open("wb") as handle:
        for segment in segments:
            data = await fetch(segment, MAX_SOURCE - size)
            if data is None:
                raise GenerationError("Recording segment is not ready")
            handle.write(data)
            size += len(data)


async def terminal(client, jwt: str, session_id: str) -> bool:
    response = await client.get(
        f"{API}/sessions/{session_id}", headers={**HEADERS, "Authorization": f"Bearer {jwt}"}
    )
    if response.status_code == 404:
        return True
    response.raise_for_status()
    return response.json().get("state") in {"CLOSED", "INACTIVE"}


class HeliosProvider:
    def __init__(self, key: str, quota: Quota):
        self.key = key
        self.quota = quota
        self.last_evidence: dict = {}

    async def generate(self, prompt: str, directory: Path, step: int) -> Path:
        from reactor_sdk import Reactor

        directory.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        attempt = await asyncio.to_thread(self.quota.consume)
        self.last_evidence = {"attempt": attempt, "closed": False, "model": "reactor/helios"}
        reactor = None
        jwt = None
        sid = None
        connected = False
        # sid callback is on the event loop. Persist before resuming provider work.
        sid_tasks = []
        failure = asyncio.get_running_loop().create_future()
        capture = FrameCapture()
        capture_task = None
        chunks = 0

        def on_message(message):
            nonlocal chunks
            kind = message.get("type")
            if kind == "chunk_complete":
                chunks += 1
            if kind in {"command_error", "error"} and not failure.done():
                failure.set_result("Provider rejected generation")

        def on_session(value):
            nonlocal sid
            if value:
                sid = value
                sid_tasks.append(
                    asyncio.create_task(asyncio.to_thread(self.quota.session, attempt, value))
                )

        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
            try:
                async with asyncio.timeout(90):
                    response = await client.post(
                        API + "/tokens",
                        headers={"Reactor-API-Key": self.key},
                        json={
                            "authorization_details": [
                                {
                                    "type": "session",
                                    "resources": {"models": {"match": ["reactor/helios"]}},
                                    "constraints": {
                                        "max_sessions": 1,
                                        "max_session_duration_seconds": 90,
                                    },
                                }
                            ]
                        },
                    )
                    response.raise_for_status()
                    jwt = response.json()["jwt"]
                    reactor = Reactor(model_name="reactor/helios", jwt=jwt)
                    reactor.on("session_id_changed", on_session)
                    reactor.on("message", on_message)
                    reactor.on(
                        "error",
                        lambda _error: (
                            failure.set_result("Provider session failed")
                            if not failure.done()
                            else None
                        ),
                    )
                    reactor.track("main_video").on_raw_frame(capture.on_frame)
                    await reactor.connect()
                    connected = True
                    sid = sid or reactor.session_id
                    if not sid:
                        raise GenerationError("No provider session identity")
                    await asyncio.to_thread(self.quota.session, attempt, sid)
                    if sid_tasks:
                        await asyncio.gather(*sid_tasks)
                    await reactor.send_command("set_sr_scale", {"sr_scale": "off"})
                    await reactor.send_command(
                        "set_prompt", {"prompt": prompt + "\n\n" + INSTRUCTION}
                    )
                    output = directory / "video.mp4"
                    capture_task = asyncio.create_task(capture.record(output))
                    capture.start()
                    try:
                        await reactor.send_command("start", {})
                        done, _ = await asyncio.wait(
                            {capture_task, failure}, return_when=asyncio.FIRST_COMPLETED
                        )
                        if failure in done:
                            raise GenerationError(failure.result())
                        capture_task.result()
                    finally:
                        if not capture_task.done():
                            capture_task.cancel()
                        await asyncio.gather(capture_task, return_exceptions=True)
                    # End GPU use as soon as the first 120 decoded frames are saved.
                    await self._close(reactor, client, jwt, sid, attempt)
                    reactor.close()
                    reactor = None
                    metadata = await validate(output)
                    self.last_evidence.update(
                        metadata,
                        **capture.evidence(),
                        chunks=chunks,
                        total_seconds=round(time.monotonic() - started, 3),
                    )
                    return output
            finally:
                capture.stop()
                if capture_task is not None and not capture_task.done():
                    capture_task.cancel()
                    await asyncio.gather(capture_task, return_exceptions=True)
                if reactor is not None:
                    # Cancellation of generation still awaits owned cleanup.
                    try:
                        await self._close(reactor, client, jwt, sid, attempt)
                    except (Exception, asyncio.CancelledError):
                        pass  # Persistent guard deliberately remains set.
                    reactor.close()
                if sid_tasks:
                    await asyncio.gather(*sid_tasks, return_exceptions=True)
                # If mint/connect was ambiguous with no session identity, no automatic clear.
                self.last_evidence.update(connected=connected, chunks=chunks, **capture.evidence())

    async def _close(self, reactor, client, jwt, sid, attempt):
        async with asyncio.timeout(12):
            try:
                await asyncio.wait_for(reactor.disconnect(), timeout=5)
            except Exception:
                pass
            if not sid or not jwt:
                raise GenerationError("Session closure needs operator verification")
            if not await terminal(client, jwt, sid):
                response = await client.delete(
                    f"{API}/sessions/{sid}", headers={**HEADERS, "Authorization": f"Bearer {jwt}"}
                )
                if response.status_code != 404:
                    response.raise_for_status()
                if not await terminal(client, jwt, sid):
                    raise GenerationError("Session closure needs operator verification")
            await asyncio.to_thread(self.quota.confirm_closed, attempt, "terminal provider GET")
            self.last_evidence["closed"] = True
