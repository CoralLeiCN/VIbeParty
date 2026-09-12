import asyncio
import re
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from backend.app import create_app
from backend.games.reverse_prompt import integration
from backend.games.reverse_prompt.config import GameSettings
from backend.games.reverse_prompt.game import Game
from backend.games.reverse_prompt.rehearsal import FIXTURES, PROMPTS
from backend.shared.config import Settings
from backend.shared.contracts import GameContext
from backend.shared.errors import AppError

BASE = "/api/games/reverse-prompt"


class TestScorer:
    ready = True
    token_limit = 256

    def validate(self, value):
        if not value or len(value) > 300:
            raise ValueError("Use 1–300 characters.")
        return value

    def score(self, original, guesses):
        return [100, 100]


class Provider:
    def __init__(self):
        self.calls = []
        self.wait = None
        self.fail = False
        self.stopped = False

    async def generate(self, prompt, directory, step):
        self.calls.append((prompt, step))
        try:
            if self.wait:
                await self.wait.wait()
            if self.fail:
                raise RuntimeError("private provider details must not leak")
            return FIXTURES / f"scene-{step}.mp4"
        finally:
            self.stopped = True


@pytest.fixture
async def clients(tmp_path):
    settings = Settings(
        _env_file=None,
        public_origin="http://test",
        browser_origin="http://test",
        media_root=tmp_path / "media",
        reverse_prompt_quota_file=tmp_path / "quota.json",
        embedding_model_path=tmp_path / "model",
    )
    app = create_app(settings, [integration])
    provider = Provider()
    game = Game(
        GameContext(settings, app.state.parties),
        GameSettings(_env_file=None, reverse_prompt_live_enabled=True, reactor_api_key="test"),
        TestScorer(),
        provider,
    )
    game.quota.initialize()
    await game.startup()
    integration.game = game
    integration.limiter.attempts.clear()
    sessions = [
        AsyncClient(
            transport=ASGITransport(app), base_url="http://test", headers={"origin": "http://test"}
        )
        for _ in range(4)
    ]
    yield game, provider, sessions
    await game.shutdown()
    for session in sessions:
        await session.aclose()


async def party(clients, mode="live"):
    game, _, users = clients
    response = await users[0].post(
        BASE + "/room", json={"organizer_code": "WMHACK", "name": "Ada", "mode": mode}
    )
    assert response.status_code == 200, response.text
    code = game.room.code
    for client in users[1:3]:
        assert (
            await client.post(BASE + "/join", json={"code": code, "name": "Guest"})
        ).status_code == 200
    return users


async def snapshot(client):
    response = await client.get(BASE + "/state")
    assert response.status_code == 200
    return response.json()


async def advance(game):
    if game.work:
        await game.work


async def send(client, state, text, submission_id=None):
    return await client.post(
        BASE + "/submit",
        json={
            "round_id": state["round_id"],
            "phase": state["phase"],
            "step": state["step"],
            "text": text,
            "submission_id": submission_id or str(uuid4()),
        },
    )


@pytest.mark.parametrize("source", ["host", "override"])
@pytest.mark.parametrize("configured", ["", "   ", "ChAnGe-Me", "changeme", "your-passcode"])
async def test_unconfigured_organizer_cannot_admit_a_host(clients, source, configured):
    game, _, users = clients
    if source == "override":
        game.config.organizer_code = SecretStr(configured)
    else:
        game.context.settings.host_passcode = configured
    for submitted in (configured, "WMHACK"):
        response = await users[0].post(
            BASE + "/room",
            json={"organizer_code": submitted, "name": "Ada", "mode": "rehearsal"},
        )
        assert response.status_code == 503
        assert response.json()["code"] == "host_not_configured"
        assert "set-cookie" not in response.headers
        assert game.room is None


async def test_valid_unicode_organizer_override_admits_only_the_configured_code(clients):
    game, _, users = clients
    game.context.settings.host_passcode = ""
    game.config.organizer_code = SecretStr("soirée-秘密")
    for submitted, status in (("", 403), ("soirée-秘密", 200)):
        response = await users[0].post(
            BASE + "/room",
            json={"organizer_code": submitted, "name": "Ada", "mode": "rehearsal"},
        )
        assert response.status_code == status
    assert game.room.players[0].role == "A"


@pytest.mark.parametrize("invalid", ["42", "12345", "12 34", "ABCD", "１２３４", 42, None])
async def test_join_rejects_non_four_digit_codes_before_admission(clients, invalid):
    game, _, users = clients
    response = await users[1].post(BASE + "/join", json={"code": invalid, "name": "Ben"})
    assert response.status_code == 422
    assert response.json()["message"] == "Enter a 4-digit room code."
    assert game.room is None


async def test_leading_zero_code_resolve_join_reset_and_retirement(clients, monkeypatch):
    game, _, users = clients
    # Controlled shared generator proves admission reserves the complete string.
    monkeypatch.setattr("backend.shared.party.generate_room_code", lambda: "0042")
    host = await users[0].post(
        BASE + "/room", json={"organizer_code": "WMHACK", "name": "Ada", "mode": "rehearsal"}
    )
    assert host.status_code == 200
    assert re.fullmatch(r"[0-9]{4}", game.room.code)
    resolved = await users[1].post("/api/party/resolve", json={"code": " 0042 "})
    assert resolved.status_code == 200
    assert resolved.json()["join_url"].endswith("?code=0042")
    wrong = await users[1].post(BASE + "/join", json={"code": "0043", "name": "Ben"})
    assert wrong.status_code == 404
    assert wrong.json()["message"] == "That party isn't available. Check the code with your host."
    joined = await users[1].post(BASE + "/join", json={"code": " 0042 ", "name": "Ben"})
    assert joined.status_code == 200
    wrong_existing = await users[1].post(BASE + "/join", json={"code": "0043", "name": "Ben"})
    assert wrong_existing.status_code == 404
    resumed = await users[1].post(BASE + "/join", json={"code": "0042", "name": "Ben"})
    assert resumed.status_code == 200 and len(game.room.players) == 2
    before = await snapshot(users[0])
    assert before["code"] == "0042" and before["join_url"].endswith("?code=0042")
    assert (
        await users[0].post(BASE + "/reset", json={"round_id": before["round_id"]})
    ).status_code == 200
    await game.cleanup
    after = await snapshot(users[1])
    assert after["code"] == "0042" and len(after["players"]) == 2
    assert after["round_id"] != before["round_id"]
    closed = await users[0].post("/api/party/close", json={"game_id": "reverse-prompt"})
    assert closed.status_code == 200
    await game.cleanup
    assert (await users[1].post("/api/party/resolve", json={"code": "0042"})).status_code == 404
    assert (await users[1].get(BASE + "/state")).status_code == 401


async def test_direct_join_rate_limit_also_counts_invalid_formats(clients):
    _, _, users = clients
    for _ in range(20):
        response = await users[1].post(BASE + "/join", json={"code": "bad", "name": "Ben"})
        assert response.status_code == 422
    response = await users[1].post(BASE + "/join", json={"code": "0042", "name": "Ben"})
    assert response.status_code == 429


async def test_missing_room_code_uses_the_shared_format_message(clients):
    _, _, users = clients
    response = await users[1].post(BASE + "/join", json={"name": "Ben"})
    assert response.status_code == 422
    assert response.json()["message"] == "Enter a 4-digit room code."


@pytest.mark.asyncio
async def test_complete_three_player_privacy_ranges_duplicates_and_replay(clients):
    game, provider, _ = clients
    a, b, c, fourth = await party(clients)
    state = await snapshot(a)
    assert (
        await fourth.post(BASE + "/join", json={"code": state["code"], "name": "Fourth"})
    ).status_code == 409
    assert (await b.post(BASE + "/start", json={"round_id": state["round_id"]})).status_code == 403
    assert (await a.post(BASE + "/start", json={"round_id": state["round_id"]})).status_code == 200
    state = await snapshot(a)
    receipt_id = str(uuid4())
    first = await send(a, state, PROMPTS[0], receipt_id)
    assert first.status_code == 200
    await advance(game)
    assert (await send(a, state, PROMPTS[0], receipt_id)).json() == first.json()
    assert (await send(a, state, "replacement", receipt_id)).status_code == 409
    bs = await snapshot(b)
    clue0 = bs["media"][0]["url"]
    assert PROMPTS[0] not in str(bs)
    assert (await snapshot(a))["media"] == []
    for user in (a, c, fourth):
        for method in ("GET", "HEAD"):
            denied = await user.request(method, clue0, headers={"Range": "bytes=0-31"})
            assert denied.status_code in (401, 404)
            assert not denied.headers.get("content-range")
    allowed = await b.get(clue0, headers={"Range": "bytes=0-31"})
    assert allowed.status_code == 206 and len(allowed.content) == 32
    assert "no-store" in allowed.headers["cache-control"]
    assert (await send(b, bs, PROMPTS[1])).status_code == 200
    await advance(game)
    assert (await b.get(clue0, headers={"Range": "bytes=0-31"})).status_code == 404
    cs = await snapshot(c)
    clue1 = cs["media"][0]["url"]
    assert (await a.get(clue1)).status_code == 404
    assert (await b.get(clue1)).status_code == 404
    assert (await send(c, cs, PROMPTS[2])).status_code == 200
    await advance(game)
    gs = await snapshot(a)
    assert gs["phase"] == "guessing"
    assert (await send(a, gs, "author guess")).status_code == 403
    assert (await send(b, gs, "secret B guess")).status_code == 200
    assert "secret B guess" not in str(await snapshot(c))
    assert (await send(c, gs, "secret C guess")).status_code == 200
    await advance(game)
    reveal = await snapshot(a)
    assert reveal["phase"] == "reveal" and len(reveal["chain"]) == 3
    assert [row["prompt"] for row in reveal["chain"]] == PROMPTS
    assert [row["role"] for row in reveal["results"]] == ["B", "C"]
    assert all(row["winner"] for row in reveal["results"])
    for row in reveal["chain"]:
        assert (await a.get(row["media"]["url"])).status_code == 200
    assert provider.calls == list(zip(PROMPTS, range(3)))
    assert (await b.post(BASE + "/reset", json={"round_id": reveal["round_id"]})).status_code == 403
    assert (await a.post(BASE + "/reset", json={"round_id": reveal["round_id"]})).status_code == 200
    await game.cleanup
    lobby = await snapshot(a)
    assert lobby["phase"] == "lobby" and len(lobby["players"]) == 3
    assert lobby["round_id"] != reveal["round_id"]
    assert (await send(a, state, PROMPTS[0], receipt_id)).status_code == 409
    assert (await a.get(clue0)).status_code == 404


@pytest.mark.asyncio
async def test_generation_failure_reset_and_stale_worker(clients):
    game, provider, _ = clients
    a, b, c, _ = await party(clients)
    lobby = await snapshot(a)
    await a.post(BASE + "/start", json={"round_id": lobby["round_id"]})
    state = await snapshot(a)
    provider.wait = asyncio.Event()
    await send(a, state, "a private scene")
    await asyncio.sleep(0)
    await a.post(BASE + "/reset", json={"round_id": state["round_id"]})
    await game.cleanup
    assert provider.stopped
    provider.wait.set()
    assert (await snapshot(a))["phase"] == "lobby"
    provider.wait = None
    provider.fail = True
    await a.post(BASE + "/start", json={"round_id": game.room.round.id})
    await send(a, await snapshot(a), "another private scene")
    await advance(game)
    state = await snapshot(c)
    assert state["phase"] == "error" and state["unscored"]
    assert not state["media"] and "chain" not in state
    assert "private provider" not in str(state)


@pytest.mark.asyncio
async def test_generation_timeout_terminates_and_scoring_failure_unscored(clients):
    game, provider, _ = clients
    a, b, c, _ = await party(clients)
    await a.post(BASE + "/start", json={"round_id": game.room.round.id})
    game.generation_timeout = 0.01
    provider.wait = asyncio.Event()
    await send(a, await snapshot(a), "scene")
    await advance(game)
    assert provider.stopped and (await snapshot(a))["phase"] == "error"
    await a.post(BASE + "/reset", json={"round_id": game.room.round.id})
    await game.cleanup
    provider.wait = None
    game.generation_timeout = 90
    await a.post(BASE + "/start", json={"round_id": game.room.round.id})
    for client, prompt in zip((a, b, c), PROMPTS):
        await send(client, await snapshot(client), prompt)
        await advance(game)

    def fail(*args):
        raise ValueError("inference failed")

    game.scorer.score = fail
    await send(b, await snapshot(b), "guess B")
    await send(c, await snapshot(c), "guess C")
    await advance(game)
    state = await snapshot(a)
    assert state["phase"] == "reveal" and state["unscored"]
    assert all(row["points"] is None and not row["winner"] for row in state["results"])


@pytest.mark.asyncio
async def test_unresolved_guard_blocks_reset_close_and_other_game(clients):
    game, _, _ = clients
    a, *_ = await party(clients)
    attempt = game.quota.consume()
    await a.post(BASE + "/reset", json={"round_id": game.room.round.id})
    await game.cleanup
    assert game.room.round.phase == "cleanup"
    response = await a.post("/api/party/close", json={})
    assert response.json()["status"] == "closing"
    assert (await game.context.parties.public_state())["status"] == "closing"
    with pytest.raises(AppError):
        async with game.context.parties.reserve("prompt-royale"):
            pass
    game.quota.confirm_closed(attempt, "operator verified fixture case")
    await game.finish_cleanup()
    assert await game.context.parties.public_state() is None
    assert game.quota.read()["remaining"] == 8


@pytest.mark.asyncio
async def test_scoring_timeout_keeps_worker_owned_until_finish(clients):
    import threading

    game, _, _ = clients
    a, b, c, _ = await party(clients)
    await a.post(BASE + "/start", json={"round_id": game.room.round.id})
    for client, prompt in zip((a, b, c), PROMPTS):
        await send(client, await snapshot(client), prompt)
        await advance(game)
    gate = threading.Event()
    game.scoring_timeout = 0.01

    def slow(*args):
        gate.wait(2)
        return [100, 0]

    game.scorer.score = slow
    await send(b, await snapshot(b), "guess B")
    await send(c, await snapshot(c), "guess C")
    await advance(game)
    state = await snapshot(a)
    assert state["unscored"] and state["phase"] == "reveal"
    assert not game.inference.done()
    await a.post(BASE + "/reset", json={"round_id": state["round_id"]})
    await asyncio.sleep(0.01)
    assert game.room.round.phase == "cleanup"
    gate.set()
    await game.cleanup
    state = await snapshot(a)
    assert state["phase"] == "lobby" and "results" not in state


@pytest.mark.asyncio
async def test_startup_invalidates_sessions_but_preserves_guard(clients):
    game, provider, users = clients
    await party(clients)
    attempt = game.quota.consume()
    game.quota.session(attempt, "unresolved-example")
    await game.shutdown()
    restarted = Game(game.context, game.config, TestScorer(), provider)
    await restarted.startup()
    integration.game = restarted
    assert (await users[0].get(BASE + "/state")).status_code == 401
    assert restarted.guard["remaining"] == 8 and restarted.guard["unresolved"]
    assert GAME_BLOCKED(restarted)
    game.quota.confirm_closed(attempt, "test terminal state")
    await restarted.shutdown()


def GAME_BLOCKED(game):
    return "reverse-prompt" in game.context.parties.blockers
