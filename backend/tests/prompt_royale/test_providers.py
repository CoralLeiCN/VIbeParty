import asyncio
import shutil
from pathlib import Path

import httpx
import pytest

from backend.games.prompt_royale.config import RoyaleSettings
from backend.games.prompt_royale.helios import (
    OwnedSession,
    SavedRecording,
    confirm_closed,
    download_recording,
)
from backend.games.prompt_royale.providers import FIXTURES, ProviderFailure, Topics
from backend.tests.prompt_royale.test_rules import start


class ScriptedVideo:
    live = True
    uncertain = False

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    async def generate(self, prompt, seed, target, index, status, source=None):
        self.calls.append((prompt, seed, source))
        await status("generating")
        outcome = self.outcomes.pop(0) if self.outcomes else "success"
        if outcome == "transient":
            raise ProviderFailure("temporary", transient=True)
        if outcome == "source":
            source = target.with_suffix(".source.mp4")
            shutil.copyfile(FIXTURES / "0.mp4", source)
            raise ProviderFailure("preparation temporary", transient=True, source=source)
        if outcome == "unknown":
            self.uncertain = True
            raise ProviderFailure("unknown", transient=True, uncertain=True)
        if outcome == "rejected":
            raise ProviderFailure("rejected")
        shutil.copyfile(source or FIXTURES / "0.mp4", target)
        return target

    async def close(self):
        return not self.uncertain


async def one_entry(e, tokens, clock):
    r = await start(e, tokens)
    await e.mutate(tokens[0], "submission", {"round_id": r.id, "prompt": "A precise scene"})
    clock.now = r.deadline
    e.room.players[e.room.host].seen = clock.now
    await e.tick()
    e.start_interval = 0
    await asyncio.gather(*list(e.generation_tasks))
    return r, next(iter(r.entries.values()))


@pytest.mark.parametrize(
    "outcomes,attempts,ready",
    [
        (["transient", "success"], 2, True),
        (["transient", "transient"], 2, False),
        (["rejected"], 1, False),
        (["unknown"], 1, False),
        (["source", "success"], 1, True),
    ],
)
async def test_single_recovery_unchanged_input_source_reuse_no_third(
    game, outcomes, attempts, ready
):
    e, tokens, clock = game
    e.video = ScriptedVideo(outcomes)
    r, entry = await one_entry(e, tokens, clock)
    assert e.starts == entry.attempts == attempts
    assert len(e.video.calls) <= 2
    assert bool(entry.path) == ready
    if len(e.video.calls) == 2:
        assert e.video.calls[0][:2] == e.video.calls[1][:2]
    assert not list((e.root / r.id).glob("*.source.mp4"))
    if outcomes[0] == "source":
        assert isinstance(e.video.calls[1][2], Path)
    if outcomes[0] == "unknown":
        assert e.blocked and e.context.parties.blockers
        assert not await e.close(tokens[0])
        assert (await e.context.parties.public_state())["status"] == "closing"


async def test_no_retry_without_allowance_or_runway(game):
    e, tokens, clock = game
    e.video = ScriptedVideo(["transient"])
    e.settings.prompt_royale_live_session_starts = 1
    _, entry = await one_entry(e, tokens, clock)
    assert e.starts == entry.attempts == 1 and not entry.path


async def test_generation_deadline_excludes_late_file_and_missing_prompt(game):
    e, tokens, clock = game
    writing = asyncio.Event()
    release = asyncio.Event()

    class LateVideo:
        live = False
        uncertain = False
        calls = 0

        async def generate(self, prompt, seed, target, index, status, source=None):
            self.calls += 1
            writing.set()
            try:
                await release.wait()
            except asyncio.CancelledError:
                # Simulate a provider completion racing the cancellation boundary.
                shutil.copyfile(FIXTURES / "0.mp4", target)

        async def close(self):
            return True

    e.video = LateVideo()
    r = await start(e, tokens)
    await e.mutate(tokens[1], "submission", {"round_id": r.id, "prompt": "Late scene"})
    clock.now = r.deadline
    e.room.players[e.room.host].seen = clock.now
    await e.tick()
    await writing.wait()
    tasks = list(e.generation_tasks)
    clock.now = r.deadline
    e.room.players[e.room.host].seen = clock.now
    await e.tick()
    await asyncio.gather(*tasks)
    assert r.phase == "results" and not r.arena and e.video.calls == 1
    assert not list((e.root / r.id).glob("*.mp4"))


async def test_topic_http_payload_failure_allowance_and_output_validation():
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "A dragon learning to bake."}],
                    }
                ],
            },
        )

    topics = Topics(
        RoyaleSettings(
            _env_file=None,
            openai_api_key="test-only",
            prompt_royale_topic_mode="live",
            prompt_royale_topic_calls=2,
        ),
        httpx.MockTransport(respond),
    )
    assert await topics.suggest() == "A dragon learning to bake."
    await topics.suggest()
    with pytest.raises(ProviderFailure):
        await topics.suggest()
    assert len(requests) == 2 and topics.calls == 2
    import json

    data = json.loads(requests[0].content)
    assert data["model"] == "gpt-5.6-luna"
    assert data["reasoning"] == {"effort": "none"}
    assert data["max_output_tokens"] == 64 and data["store"] is False and "tools" not in data

    def timeout(request):
        raise httpx.ReadTimeout("test timeout")

    topics = Topics(
        RoyaleSettings(_env_file=None, openai_api_key="test-only", prompt_royale_topic_mode="live"),
        httpx.MockTransport(timeout),
    )
    with pytest.raises(ProviderFailure):
        await topics.suggest()
    assert topics.calls == 1  # No hidden retries/refunds after an uncertain response.
    for payload in [
        {"status": "incomplete", "output": []},
        {
            "status": "completed",
            "output": [
                {"type": "message", "content": [{"type": "output_text", "text": "x" * 161}]}
            ],
        },
    ]:
        topics.transport = httpx.MockTransport(lambda req: httpx.Response(200, json=payload))
        with pytest.raises(ProviderFailure):
            await topics.suggest()


@pytest.mark.parametrize(
    "state,expected",
    [
        ("CLOSED", True),
        ("INACTIVE", True),
        ("ACTIVE", False),
        ("SUSPENDED", False),
        ("FUTURE_UNKNOWN", False),
    ],
)
async def test_closure_requires_terminal_provider_state(state, expected):
    requests = []

    def respond(request):
        requests.append(request)
        assert request.headers["Reactor-API-Version"] == "1"
        return httpx.Response(200, json={"state": state})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        session = OwnedSession("fake-token", "fake-session")
        assert await confirm_closed(client, session) is expected
        assert session.confirmed_closed is expected
        assert not await confirm_closed(client, OwnedSession("fake-token"))
        assert all(r.method in {"GET", "DELETE"} for r in requests)


async def test_closure_404_and_failed_disconnect_does_not_hide_live_session():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(404))
    ) as client:
        assert await confirm_closed(client, OwnedSession("fake-token", "known-session"))
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(403))
    ) as client:
        assert not await confirm_closed(client, OwnedSession("fake-token", "known-session"))


async def test_hls_init_segment_and_cross_origin_token_privacy(tmp_path):
    def respond(request):
        if request.url.path == "/playlist":
            return httpx.Response(
                200, text='#EXTM3U\n#EXT-X-MAP:URI="init.mp4"\nhttps://cdn.example/part.m4s\n'
            )
        if request.url.host == "api.reactor.inc":
            assert request.headers["Authorization"] == "Bearer fake-token"
            return httpx.Response(200, content=b"INIT")
        assert "Authorization" not in request.headers
        return httpx.Response(200, content=b"FRAGMENT")

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        target = tmp_path / "source.mp4"
        count = await download_recording(
            client, SavedRecording("https://api.reactor.inc/playlist", "fake-token"), target
        )
        assert count == 12 and target.read_bytes() == b"INITFRAGMENT"
        with pytest.raises(ProviderFailure):
            await download_recording(
                client, SavedRecording("http://localhost/private", "fake-token"), target
            )


async def test_replacement_refused_without_eighty_second_runway(game):
    e, tokens, clock = game

    class RunningOut(ScriptedVideo):
        async def generate(self, prompt, seed, target, index, status, source=None):
            self.calls.append((prompt, seed, source))
            clock.now = e.room.round.deadline - 79
            raise ProviderFailure("temporary", transient=True)

    e.video = RunningOut([])
    _, entry = await one_entry(e, tokens, clock)
    assert e.starts == 1 and len(e.video.calls) == 1 and not entry.path
