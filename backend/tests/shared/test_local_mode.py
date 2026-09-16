from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.games.prompt_royale import integration as royale
from backend.games.reverse_prompt import integration as reverse
from backend.games.word_by_word import integration as word
from backend.shared.config import Settings

ORIGIN = "http://testserver"


@pytest.mark.parametrize("local_mode", [True, False])
@pytest.mark.parametrize(
    "game,create_path,state_path,join_path,credential",
    [
        (word, "/host", "/state", "/join", "passcode"),
        (royale, "/room", "/room", "/room/join", "passcode"),
        (reverse, "/room", "/state", "/join", "organizer_code"),
    ],
    ids=["word-by-word", "prompt-royale", "reverse-prompt"],
)
def test_host_access_shared_link_and_ownership(
    tmp_path, monkeypatch, local_mode, game, create_path, state_path, join_path, credential
):
    # Local admission also works when no host/organizer code has been configured.
    host_code = "" if local_mode else "test-host-code"
    monkeypatch.setenv("ORGANIZER_CODE", host_code)
    settings = Settings(
        _env_file=None,
        local_mode=local_mode,
        host_passcode=host_code,
        public_origin=ORIGIN,
        browser_origin=ORIGIN,
        generation_mode="fixture",
        media_root=tmp_path / "media",
        reverse_prompt_quota_file=tmp_path / "quota.json",
        embedding_model_path=tmp_path / "model",
    )
    api = f"/api/games/{game.game_id}"
    body = {} if game is word else {"name": "Host"}
    with TestClient(create_app(settings, [game])) as client:
        config = client.get("/api/config")
        assert config.json() == {"local_mode": local_mode}
        assert config.headers["Cache-Control"] == "no-store"
        assert client.post(api + create_path, json=body).status_code == 403
        client.headers["Origin"] = ORIGIN
        if not local_mode:
            for fields in ({}, {credential: "wrong"}):
                denied = client.post(api + create_path, json={**body, **fields})
                assert denied.status_code == 403
                assert "set-cookie" not in denied.headers
                assert client.get("/api/session").json()["party"] is None
            body[credential] = host_code
        created = client.post(api + create_path, json=body)
        assert created.status_code == 200, created.text
        assert "HttpOnly" in created.headers["set-cookie"]
        host_cookies = dict(client.cookies)
        state = client.get(api + state_path).json()
        link = urlsplit(state["join_url"])
        assert f"{link.scheme}://{link.netloc}" == ORIGIN
        assert link.path == f"/games/{game.game_id}/join"
        query = parse_qs(link.query)
        assert set(query) == {"code"}
        code = query["code"][0]
        assert len(code) == 4 and code.isascii() and code.isdigit()

        # A second browser cannot take ownership simply by creating another room.
        client.cookies.clear()
        assert client.post(api + create_path, json=body).status_code == 409
        assert client.post("/api/party/close", json={}).status_code in {401, 403}
        resolved = client.post("/api/party/resolve", json={"code": code}).json()
        assert resolved["join_url"] == f"{link.path}?{link.query}"
        joined = client.post(api + join_path, json={"code": code, "name": "Guest"})
        assert joined.status_code == 200, joined.text
        session = client.get("/api/session").json()["session"]
        assert session["role"] == "player" and not session["can_close"]
        assert client.post("/api/party/close", json={}).status_code == 403

        client.cookies.clear()
        client.cookies.update(host_cookies)
        assert client.post(api + create_path, json=body).status_code == 200
        assert client.get(api + state_path).json()["join_url"] == state["join_url"]
        assert client.get("/api/session").json()["session"]["can_close"]
        assert client.post("/api/party/close", json={}).json()["status"] == "closed"
