import time

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.games.prompt_royale import integration
from backend.games.prompt_royale.config import TOPICS
from backend.games.prompt_royale.engine import uid
from backend.shared.config import Settings

API = "/api/games/prompt-royale"


def test_http_cookie_origin_role_private_range_and_session_discovery(tmp_path):
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
        origin = {"Origin": "http://testserver"}
        assert (
            client.post(API + "/room", json={"name": "Host", "passcode": "test-code"}).status_code
            == 403
        )
        assert (
            client.post(
                API + "/room", json={"name": "Host", "passcode": "错误密码"}, headers=origin
            ).status_code
            == 403
        )
        assert (
            client.post(
                API + "/room",
                content=b'{"name":"Host","passcode":"\\ud800"}',
                headers={**origin, "Content-Type": "application/json"},
            ).status_code
            == 422
        )
        response = client.post(
            API + "/room", json={"name": "Host", "passcode": "test-code"}, headers=origin
        )
        assert response.status_code == 200
        assert (
            "HttpOnly" in response.headers["set-cookie"]
            and "SameSite=lax" in response.headers["set-cookie"]
        )
        assert "Secure" not in response.headers["set-cookie"]
        state = response.json()
        code = state["code"]
        cookie = integration.GAME_COOKIE
        tokens = [client.cookies.get(cookie)]
        for name in ["Guest one", "Guest two"]:
            client.cookies.clear()
            response = client.post(
                API + "/room/join", json={"name": name, "code": code}, headers=origin
            )
            assert response.status_code == 200
            tokens.append(client.cookies.get(cookie))
        client.cookies.clear()

        def headers(token):
            return {**origin, "Cookie": f"{cookie}={token}"}

        def host(action, **extra):
            engine = integration.engine
            return client.post(
                API + action,
                headers=headers(tokens[0]),
                json={
                    "command_id": uid(),
                    "expected_version": engine.room.version,
                    "round_id": engine.room.round.id if engine.room.round else None,
                    **extra,
                },
            )

        assert client.get(API + "/room").status_code == 401
        assert client.post("/api/party/resolve", json={"code": code}, headers=origin).json() == {
            "game_id": "prompt-royale",
            "join_url": f"/games/prompt-royale/join?code={code}",
        }
        host("/room/topic", mode="bundled", topic=TOPICS[0])
        assert host("/room/start").status_code == 200
        r = integration.engine.room.round
        for index, token in enumerate(tokens):
            response = client.post(
                API + "/round/submission",
                headers=headers(token),
                json={"round_id": r.id, "prompt": f"Private text {index}"},
            )
            assert response.status_code == 200
        asset = next(iter(r.entries))
        assert (
            client.get(
                API + "/media/" + asset, headers={**headers(tokens[0]), "Range": "bytes=0-99"}
            ).status_code
            == 404
        )
        for _ in range(30):
            state = client.get(API + "/room", headers=headers(tokens[0])).json()
            if state["phase"] == "screening":
                break
            time.sleep(0.05)
        assert state["phase"] == "screening"
        response = client.get(
            API + "/media/" + asset, headers={**headers(tokens[1]), "Range": "bytes=0-99"}
        )
        assert response.status_code == 206 and len(response.content) == 100
        assert "no-store" in response.headers["cache-control"]
        assert client.get(API + "/media/" + asset).status_code == 401
        assert (
            client.get(
                API + "/media/" + asset, headers={"Cookie": "vp_reverse_prompt=pretend"}
            ).status_code
            == 401
        )
        before = integration.engine.room.players[integration.engine.room.host].seen
        summary = client.get("/api/session", headers=headers(tokens[0])).json()
        assert integration.engine.room.players[integration.engine.room.host].seen == before
        assert summary["session"]["role"] == "host" and "players" not in summary
        assert "Private text" not in str(summary)
        assert (
            client.post("/api/party/close", json={}, headers=headers(tokens[1])).status_code == 403
        )
        assert (
            client.post("/api/party/close", json={}, headers=headers(tokens[0])).json()["status"]
            == "closed"
        )
        assert client.get(API + "/media/" + asset, headers=headers(tokens[0])).status_code == 401
