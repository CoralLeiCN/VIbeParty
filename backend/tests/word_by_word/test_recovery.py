"""PORTAL-001: lost host cookies, ownership proof and guarded switching."""

import stat

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.games.prompt_royale import integration as royale
from backend.games.word_by_word import integration as word
from backend.shared.config import Settings

API = "/api/games/word-by-word"
ORIGIN = "http://testserver"


@pytest.fixture(params=[True, False], ids=["local-code", "passcode"])
def recovery_client(request, tmp_path, monkeypatch):
    async def ready(_):
        return None

    monkeypatch.setattr("backend.games.word_by_word.service.codex_unavailable_reason", ready)
    settings = Settings(
        _env_file=None,
        local_mode=request.param,
        host_passcode="test-host-passcode",
        media_root=tmp_path,
        public_origin=ORIGIN,
        browser_origin=ORIGIN,
        additional_browser_origins=("http://alternate-host",),
    )
    with TestClient(create_app(settings, [word, royale])) as client:
        client.headers["Origin"] = ORIGIN
        yield client, settings


def create(client):
    response = client.post(API + "/host", json={"passcode": "test-host-passcode"})
    assert response.status_code == 200
    assert "Max-Age=604800" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]
    return response.json(), dict(client.cookies)


def credentials(client, settings):
    options = client.get(API + "/host/recovery")
    assert options.headers["cache-control"] == "no-store"
    assert set(options.json()) == {"available", "party_id", "method"}
    code = (
        word.game.recovery_file.read_text().strip()
        if settings.local_mode
        else settings.host_passcode
    )
    assert code not in options.text
    return {"party_id": options.json()["party_id"], "credential": code}


def test_recovery_requires_proof_revokes_old_host_and_preserves_party(recovery_client):
    client, settings = recovery_client
    lobby, old_host = create(client)
    proof = credentials(client, settings)
    if settings.local_mode:
        assert stat.S_IMODE(word.game.recovery_file.stat().st_mode) == 0o600
    else:
        assert not word.game.recovery_file.exists()
    client.cookies.clear()
    lost = client.get("/api/session").json()
    assert lost["status"] == "anonymous" and lost["party"]["game_id"] == "word-by-word"
    assert client.post(API + "/host", json={"passcode": settings.host_passcode}).status_code == 409
    assert client.post("/api/party/close", json={}).status_code == 401

    # Room codes, a different hostname, and an ordinary player session grant no host role.
    for origin in [ORIGIN, "http://alternate-host"]:
        denied = client.post(
            API + "/host/recovery",
            json={**proof, "credential": lobby["code"]},
            headers={"Origin": origin},
        )
        assert denied.status_code == 403 and "set-cookie" not in denied.headers
    assert (
        client.post(API + "/join", json={"code": lobby["code"], "name": "Ada"}).status_code == 200
    )
    player = dict(client.cookies)
    assert client.post(API + "/host/recovery", json={**proof, "credential": ""}).status_code == 403
    assert client.get("/api/session").json()["session"]["role"] == "player"
    assert client.post("/api/party/close", json={}).status_code == 403
    assert (
        client.post(
            API + "/host/recovery", json=proof, headers={"Origin": "http://untrusted"}
        ).status_code
        == 403
    )
    recovered = client.post(API + "/host/recovery", json=proof)
    assert recovered.status_code == 200 and "Max-Age=604800" in recovered.headers["set-cookie"]
    new_host = dict(client.cookies)
    assert new_host != old_host
    state = client.get(API + "/state").json()
    assert state["role"] == "host" and state["round_id"] == lobby["round_id"]
    assert state["code"] == lobby["code"] and state["players"] == ["Ada"]
    assert client.get("/api/session").json()["session"]["can_close"]
    client.cookies.clear()
    client.cookies.update(old_host)
    assert client.get(API + "/state").status_code == 401
    assert client.post("/api/party/close", json={}).status_code == 401
    client.cookies.clear()
    client.cookies.update(player)
    assert client.get(API + "/state").json()["role"] == "player"
    client.cookies.clear()
    client.cookies.update(new_host)
    assert client.post("/api/party/close", json={}).json()["status"] == "closed"
    assert not word.game.recovery_file.exists()
    assert client.get(API + "/host/recovery").json() == {"available": False}


def test_recovery_during_cleanup_cannot_release_party_early(recovery_client):
    client, settings = recovery_client
    create(client)
    proof = credentials(client, settings)
    word.game.provider_closing = True
    try:
        assert client.post("/api/party/close", json={}).json()["status"] == "closing"
        client.cookies.clear()
        assert client.post(API + "/host/recovery", json=proof).status_code == 200
        assert client.get("/api/session").json()["party"]["status"] == "closing"
        assert client.post("/api/party/close", json={}).json()["status"] == "closing"
        assert (
            client.post(
                "/api/games/prompt-royale/room",
                json={
                    "name": "Host",
                    "passcode": settings.host_passcode,
                },
            ).status_code
            == 409
        )
    finally:
        word.game.provider_closing = False
    assert client.post("/api/party/close", json={}).json()["status"] == "closed"
    assert (
        client.post(
            "/api/games/prompt-royale/room",
            json={
                "name": "Host",
                "passcode": settings.host_passcode,
            },
        ).status_code
        == 200
    )
    assert client.post("/api/party/close", json={}).json()["status"] == "closed"


def test_stale_recovery_and_previous_party_code_are_rejected(recovery_client):
    client, settings = recovery_client
    lobby, _ = create(client)
    proof = credentials(client, settings)
    # A reset keeps the recovery code but changes the public join code.
    assert client.post(API + "/room/reset", json={"round_id": lobby["round_id"]}).status_code == 200
    assert credentials(client, settings) == proof
    assert client.post("/api/party/close", json={}).json()["status"] == "closed"
    create(client)
    current = credentials(client, settings)
    client.cookies.clear()
    assert client.post(API + "/host/recovery", json=proof).status_code == 409
    if settings.local_mode:
        assert (
            client.post(
                API + "/host/recovery",
                json={
                    **current,
                    "credential": proof["credential"],
                },
            ).status_code
            == 403
        )
    assert client.post(API + "/host/recovery", json=current).status_code == 200


def test_recovery_attempts_are_bounded(recovery_client):
    client, settings = recovery_client
    create(client)
    proof = credentials(client, settings)
    client.cookies.clear()
    for _ in range(20):
        assert (
            client.post(API + "/host/recovery", json={**proof, "credential": "wrong"}).status_code
            == 403
        )
    assert client.post(API + "/host/recovery", json=proof).status_code == 429
