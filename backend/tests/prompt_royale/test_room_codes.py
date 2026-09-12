import secrets

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.games.prompt_royale import integration
from backend.shared.config import Settings

API = "/api/games/prompt-royale"
ORIGIN = {"Origin": "http://testserver", "Content-Type": "application/json"}
FORMAT_ERROR = "Enter a 4-digit room code."
UNAVAILABLE = "That party isn't available. Check the code with your host."


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Controlled fixture exercises zero preservation through the real shared generator.
    monkeypatch.setattr(secrets, "randbelow", lambda _: 42)
    app = create_app(
        Settings(
            _env_file=None,
            media_root=tmp_path,
            host_passcode="test-code",
            public_origin="http://testserver",
            browser_origin="http://testserver",
            generation_mode="fixture",
        ),
        integrations=[integration],
    )
    with TestClient(app) as client:
        yield client


def create(client):
    response = client.post(
        API + "/room", json={"name": "Host", "passcode": "test-code"}, headers=ORIGIN
    )
    assert response.status_code == 200
    assert response.json()["code"] == "0042"
    assert response.json()["join_url"].endswith("?code=0042")
    return client.cookies.get(integration.GAME_COOKIE)


def test_leading_zero_resolve_join_validation_resume_and_retirement(client):
    host = create(client)
    client.cookies.clear()
    for code in ["42", "12345", "12 34", "ABCD", "１２３４", "12.3", "", 42, None]:
        response = client.post(
            API + "/room/join", json={"name": "Guest", "code": code}, headers=ORIGIN
        )
        assert response.status_code == 422
        assert response.json()["message"] == FORMAT_ERROR
    resolved = client.post("/api/party/resolve", json={"code": " 0042 "}, headers=ORIGIN)
    assert resolved.json() == {
        "game_id": "prompt-royale",
        "join_url": "/games/prompt-royale/join?code=0042",
    }
    unknown = client.post(
        API + "/room/join", json={"name": "Guest", "code": "9999"}, headers=ORIGIN
    )
    assert unknown.status_code == 404 and unknown.json()["message"] == UNAVAILABLE
    assert client.get(API + "/room?code=0042").status_code == 401
    joined = client.post(
        API + "/room/join", json={"name": "Guest", "code": " 0042 "}, headers=ORIGIN
    )
    assert joined.status_code == 200 and joined.json()["code"] == "0042"
    repeated = client.post(
        API + "/room/join", json={"name": "Different", "code": "0042"}, headers=ORIGIN
    )
    assert repeated.json()["me"] == joined.json()["me"]
    assert len(repeated.json()["players"]) == 2
    denied = client.delete(API + "/room", headers=ORIGIN)
    assert denied.status_code == 403
    client.cookies.clear()
    closed = client.delete(
        API + "/room", headers={**ORIGIN, "Cookie": f"{integration.GAME_COOKIE}={host}"}
    )
    assert closed.json()["status"] == "closed"
    retired = client.post("/api/party/resolve", json={"code": "0042"}, headers=ORIGIN)
    assert retired.status_code == 404
    # Retired codes may be reused, but the old membership must never be restored.
    new_host = create(client)
    assert new_host != host
    assert client.get(API + "/room").json()["players"] == [
        {"id": integration.engine.room.host, "name": "Host", "host": True, "present": True}
    ]
    client.cookies.clear()
    assert (
        client.get(
            API + "/room", headers={"Cookie": f"{integration.GAME_COOKIE}={host}"}
        ).status_code
        == 401
    )


@pytest.mark.parametrize("attempt", ["9999", "12 34", 42, None])
def test_direct_join_rate_limit_applies_before_lookup(client, attempt):
    create(client)
    client.cookies.clear()
    integration.engine.admission.clear()
    for _ in range(20):
        response = client.post(
            API + "/room/join", json={"name": "Guest", "code": attempt}, headers=ORIGIN
        )
        assert response.status_code == (404 if attempt == "9999" else 422)
    assert (
        client.post(
            API + "/room/join", json={"name": "Guest", "code": "0042"}, headers=ORIGIN
        ).status_code
        == 429
    )


@pytest.mark.parametrize("player_count", [0, 5, -1, 1.5, True, "2", None])
def test_invalid_player_count_does_not_create_a_party(client, player_count):
    response = client.post(
        API + "/room",
        json={"name": "Host", "passcode": "test-code", "player_count": player_count},
        headers=ORIGIN,
    )
    assert response.status_code == 422
    assert integration.engine.room is None


def test_player_count_create_and_update_api(client):
    response = client.post(
        API + "/room",
        json={"name": "Host", "passcode": "test-code", "player_count": 1},
        headers=ORIGIN,
    )
    assert response.status_code == 200 and response.json()["player_count"] == 1
    state = response.json()
    command = {
        "command_id": "change-player-count",
        "expected_version": state["version"],
        "player_count": 2,
    }
    response = client.post(API + "/room/player-count", json=command, headers=ORIGIN)
    assert response.status_code == 200 and response.json()["player_count"] == 2
    repeated = client.post(API + "/room/player-count", json=command, headers=ORIGIN)
    assert repeated.status_code == 200 and repeated.json()["version"] == response.json()["version"]
    invalid = client.post(
        API + "/room/player-count", json={**command, "player_count": 5}, headers=ORIGIN
    )
    assert invalid.status_code == 422
    assert client.get(API + "/room").json()["player_count"] == 2
