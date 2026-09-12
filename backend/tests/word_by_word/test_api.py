import time

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.games.word_by_word import integration
from backend.games.word_by_word.domain import FIXTURE_TEXT
from backend.shared.config import Settings

API = "/api/games/word-by-word"
ORIGIN = "http://testserver"


def test_cookie_roles_origin_discovery_and_protected_ranges(tmp_path):
    settings = Settings(
        _env_file=None,
        media_root=tmp_path,
        host_passcode="test-pass",
        browser_origin=ORIGIN,
        public_origin=ORIGIN,
    )
    with TestClient(create_app(settings, [integration])) as client:
        assert client.post(API + "/host", json={"passcode": "test-pass"}).status_code == 403
        client.headers["Origin"] = ORIGIN
        assert client.post(API + "/host", json={"passcode": "bad"}).status_code == 403
        response = client.post(API + "/host", json={"passcode": "test-pass"})
        assert response.status_code == 200
        cookie = response.headers["set-cookie"]
        assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Secure" not in cookie
        host_cookie = client.cookies.get(integration.COOKIE)
        state = response.json()
        code, rid = state["code"], state["round_id"]
        activity = integration.game.room.activity
        summary = client.get("/api/session").json()
        assert summary["session"]["role"] == "host"
        assert integration.game.room.activity == activity
        players = []
        for name in ["Ada", "Bo", "Cy"]:
            client.cookies.clear()
            response = client.post(API + "/join", json={"code": code, "name": name})
            assert response.status_code == 200
            players.append(client.cookies.get(integration.COOKIE))
        assert client.post(API + "/round/start", json={"round_id": rid}).status_code == 403
        client.cookies.set(integration.COOKIE, host_cookie)
        assert client.post(API + "/round/start", json={"round_id": rid}).status_code == 200
        for i, text in enumerate(FIXTURE_TEXT):
            client.cookies.clear()
            client.cookies.set(integration.COOKIE, players[i % 3])
            assert (
                client.post(
                    API + "/contribution", json={"round_id": rid, "slot_index": i, "text": text}
                ).status_code
                == 200
            )
        client.cookies.clear()
        client.cookies.set(integration.COOKIE, host_cookie)
        limit = time.monotonic() + 10
        while time.monotonic() < limit:
            snapshot = client.get(API + "/state").json()
            if snapshot["phase"] == "REVEAL":
                break
            time.sleep(0.05)
        assert snapshot["phase"] == "REVEAL"
        assert all(text not in str(snapshot) for text in FIXTURE_TEXT)
        url = f"{API}/clips/{rid}/0"
        assert client.get(url, headers={"Range": "bytes=0-31"}).status_code == 404
        response = client.post(
            API + "/reveal/next", json={"round_id": rid, "expected_reveal_index": -1}
        )
        assert response.status_code == 200
        response = client.get(url, headers={"Range": "bytes=0-31"})
        assert response.status_code == 206 and len(response.content) == 32
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["content-range"].startswith("bytes 0-31/")
        client.cookies.clear()
        assert client.get(url).status_code == 401
        client.cookies.set("vp_prompt_royale", host_cookie)
        assert client.get(url).status_code == 401
        client.cookies.set(integration.COOKIE, players[0])
        assert client.get(url, headers={"Range": "bytes=0-31"}).status_code == 403
        assert client.post("/api/party/close", json={}).status_code == 403
        client.cookies.clear()
        client.cookies.set(integration.COOKIE, host_cookie)
        client.post(API + "/round/end", json={"round_id": rid})
        response = client.post(API + "/room/reset", json={"round_id": rid})
        assert response.status_code == 200
        assert response.json()["players"] == []
        assert response.json()["code"] != code
        assert client.post("/api/party/resolve", json={"code": code}).status_code == 404
        assert client.get(url).status_code == 404
        assert client.post("/api/party/close", json={}).json()["status"] == "closed"
        assert client.get("/api/session").json()["reason"] == "expired"
        assert list(settings.media_dir("word-by-word").iterdir()) == []


def test_four_digit_code_validation_and_lifecycle(tmp_path, monkeypatch):
    from backend.shared import room_codes

    # Controlled generation result, preserving real admission/coordinator/cookies.
    draws = iter([42, 42, 9012])  # Reset retries the old code before selecting a different one.
    monkeypatch.setattr(room_codes.secrets, "randbelow", lambda _: next(draws))
    settings = Settings(
        _env_file=None,
        media_root=tmp_path,
        host_passcode="test-pass",
        browser_origin=ORIGIN,
        public_origin=ORIGIN,
    )
    with TestClient(create_app(settings, [integration])) as client:
        client.headers["Origin"] = ORIGIN
        for code in [42, None, ["0042"], "", "42", "12345", "12 34", "ABCD", "１２３４"]:
            response = client.post(API + "/join", json={"code": code, "name": "Ada"})
            assert response.status_code == 422
            assert response.json()["message"] == "Enter a 4-digit room code."
        response = client.post(API + "/host", json={"passcode": "test-pass"})
        assert response.status_code == 200
        state = response.json()
        assert state["code"] == "0042" and state["join_url"].endswith("code=0042")
        host_cookie = client.cookies.get(integration.COOKIE)
        rid = state["round_id"]
        assert client.get(API + "/state").json()["code"] == "0042"
        assert client.post(API + "/host", json={"passcode": "test-pass"}).json()["code"] == "0042"
        resolve = client.post("/api/party/resolve", json={"code": " 0042 "})
        assert resolve.json()["join_url"].endswith("code=0042")
        client.cookies.clear()
        assert client.get(API + "/state").status_code == 401
        missing = client.post(API + "/join", json={"code": "0043", "name": "Ada"})
        assert missing.status_code == 404
        assert (
            missing.json()["message"]
            == "That party isn't available. Check the code with your host."
        )
        for name in ["Ada", "Bo", "Cy"]:
            client.cookies.clear()
            joined = client.post(API + "/join", json={"code": " 0042 ", "name": name})
            assert joined.status_code == 200 and joined.json()["code"] == "0042"
        assert client.post(API + "/round/start", json={"round_id": rid}).status_code == 403
        client.cookies.clear()
        client.cookies.set(integration.COOKIE, host_cookie)
        assert client.post(API + "/round/start", json={"round_id": rid}).status_code == 200
        assert client.post(API + "/round/end", json={"round_id": rid}).status_code == 200
        new = client.post(API + "/round/new", json={"round_id": rid}).json()
        assert new["code"] == "0042" and new["players"] == ["Ada", "Bo", "Cy"]
        reset = client.post(API + "/room/reset", json={"round_id": new["round_id"]}).json()
        assert len(reset["code"]) == 4 and reset["code"].isascii() and reset["code"].isdigit()
        assert reset["code"] != "0042" and reset["players"] == []
        assert client.post("/api/party/resolve", json={"code": "0042"}).status_code == 404
        assert client.post("/api/party/close", json={}).json()["status"] == "closed"
        assert client.post("/api/party/resolve", json={"code": reset["code"]}).status_code == 404
        assert client.get(API + "/state").status_code == 401
        # Direct join requests remain rate limited independently of the portal.
        statuses = [
            client.post(API + "/join", json={"code": "0042", "name": "Ada"}).status_code
            for _ in range(21)
        ]
        assert 429 in statuses


def test_invalid_direct_code_attempts_are_rate_limited(tmp_path):
    settings = Settings(
        _env_file=None, media_root=tmp_path, browser_origin=ORIGIN, public_origin=ORIGIN
    )
    with TestClient(create_app(settings, [integration])) as client:
        client.headers["Origin"] = ORIGIN
        for _ in range(20):
            response = client.post(API + "/join", json={"code": 42, "name": "Ada"})
            assert response.status_code == 422
            assert response.json()["message"] == "Enter a 4-digit room code."
        assert client.post(API + "/join", json={"name": "Ada"}).status_code == 429
