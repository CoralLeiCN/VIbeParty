import asyncio

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.shared.config import Settings
from backend.shared.errors import AppError
from backend.shared.party import PartyCoordinator


async def test_concurrent_games_cannot_create_two_parties(monkeypatch):
    monkeypatch.setattr("backend.shared.party.generate_room_code", lambda: "0042")
    parties = PartyCoordinator()

    async def create(game):
        try:
            async with parties.reserve(game) as reservation:
                await asyncio.sleep(0)
                await reservation.activate()
            return game
        except AppError as error:
            return error.code

    outcomes = await asyncio.gather(create("word-by-word"), create("prompt-royale"))
    assert outcomes.count("another_game_active") == 1
    assert await parties.resolve(" 0042 ") in outcomes


async def test_failed_creation_rolls_back_and_cleanup_blocks_switching():
    parties = PartyCoordinator()
    with pytest.raises(RuntimeError):
        async with parties.reserve("word-by-word"):
            raise RuntimeError("Creation failed")
    assert await parties.public_state() is None
    async with parties.reserve("prompt-royale") as reservation:
        original = reservation.code
        await reservation.activate()
    rotated = await parties.rotate_code("prompt-royale")
    assert rotated != original
    with pytest.raises(AppError):
        await parties.resolve(original)
    assert await parties.resolve(rotated) == "prompt-royale"
    await parties.begin_close("prompt-royale")
    with pytest.raises(AppError, match="Close the current"):
        async with parties.reserve("reverse-prompt"):
            pass
    await parties.finish_close("prompt-royale")
    async with parties.reserve("reverse-prompt") as reservation:
        await reservation.activate()


def test_shell_privacy_errors_and_direct_routes(tmp_path):
    settings = Settings(
        _env_file=None,
        media_root=tmp_path / "media",
        reverse_prompt_quota_file=tmp_path / "quota.json",
        embedding_model_path=tmp_path / "model",
    )
    with TestClient(create_app(settings)) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/api/session").json() == {
            "status": "anonymous",
            "reason": "no_session",
            "party": None,
        }
        client.cookies.set("vp_word_by_word", "invalid")
        assert client.get("/api/session").json()["reason"] == "expired"
        assert client.post("/api/party/resolve", json={"code": "0042"}).status_code == 403
        headers = {"Origin": "http://localhost:8000"}
        response = client.post("/api/party/resolve", json={"code": "0042"}, headers=headers)
        assert response.status_code == 404
        assert set(response.json()) == {"code", "message", "field"}
        assert client.get("/api/nonexistent").status_code == 404
        assert client.get("/media/private.mp4").status_code == 404
        for path in ["/", "/join?code=0042", "/games/reverse-prompt/host"]:
            response = client.get(path)
            assert response.status_code == 200
            assert '<div id="root">' in response.text
