from fastapi import APIRouter, Request
from fastapi.responses import Response
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.shared.config import Settings
from backend.shared.contracts import CloseResult, SessionSummary, cookie_name
from backend.shared.errors import AppError


class ContractGame:
    """Test-only consumer: checks shell auth/lifecycle boundaries without a provider."""

    available = True

    def __init__(self, game_id):
        self.game_id = game_id
        self.router = APIRouter()
        self.unresolved = True
        self.presence_updates = 0
        self.closed = False

        @self.router.post("/host")
        async def host():
            async with self.context.parties.reserve(self.game_id) as reservation:
                await reservation.activate()
            return {"created": True}

        @self.router.get("/media/private")
        async def media(request: Request):
            if not await self.session_summary(request):
                raise AppError(401, "session_required", "Join the party first.")
            return Response(b"private clip", headers={"Cache-Control": "private, no-store"})

    async def startup(self, context):
        self.context = context

    async def shutdown(self):
        pass

    async def session_summary(self, request):
        role = request.cookies.get(cookie_name(self.game_id))
        if self.closed or role not in {"host", "player"}:
            return None
        return SessionSummary(
            game_id=self.game_id,
            role=role,
            continuation_url=f"/games/{self.game_id}/{'host' if role == 'host' else 'join'}",
            can_close=role == "host",
        )

    async def close_party(self, request):
        summary = await self.session_summary(request)
        if not summary or not summary.can_close:
            raise AppError(403, "host_required", "Only the host can close this party.")
        await self.context.parties.begin_close(self.game_id)
        if self.unresolved:
            return CloseResult(status="closing", message="Finishing the previous session.")
        self.closed = True
        await self.context.parties.finish_close(self.game_id)
        return CloseResult(status="closed")


def test_role_isolation_continuation_and_confirmed_cleanup(monkeypatch):
    monkeypatch.setattr("backend.shared.party.generate_room_code", lambda: "0042")
    first = ContractGame("word-by-word")
    second = ContractGame("reverse-prompt")
    settings = Settings(_env_file=None)
    with TestClient(create_app(settings, [first, second])) as client:
        client.headers["Origin"] = "http://localhost:8000"
        client.post("/api/games/word-by-word/host", json={}).raise_for_status()
        resolved = client.post("/api/party/resolve", json={"code": " 0042 "}).json()
        assert resolved == {
            "game_id": "word-by-word",
            "join_url": "/games/word-by-word/join?code=0042",
        }
        client.cookies.set(cookie_name("reverse-prompt"), "host")
        assert client.get("/api/session").json()["status"] == "anonymous"
        assert client.post("/api/party/close", json={}).status_code == 403
        assert client.get("/api/games/word-by-word/media/private").status_code == 401
        client.cookies.set(cookie_name("word-by-word"), "player")
        discovery = client.get("/api/session").json()
        assert discovery["session"]["role"] == "player"
        assert discovery["session"]["continuation_url"] == "/games/word-by-word/join"
        assert first.presence_updates == 0
        assert client.post("/api/party/close", json={}).status_code == 403
        client.cookies.set(cookie_name("word-by-word"), "host")
        assert client.get("/api/session").json()["session"]["can_close"]
        stale = client.post("/api/party/close", json={"game_id": "reverse-prompt"})
        assert stale.status_code == 409
        assert client.post("/api/party/close", json={}).json()["status"] == "closing"
        assert client.post("/api/games/reverse-prompt/host", json={}).status_code == 409
        assert client.post("/api/party/resolve", json={"code": "0042"}).status_code == 404
        media = client.get("/api/games/word-by-word/media/private")
        assert media.headers["Cache-Control"] == "private, no-store"
        first.unresolved = False
        assert client.post("/api/party/close", json={}).json()["status"] == "closed"
        assert client.get("/api/session").json()["reason"] == "expired"
        assert client.post("/api/games/reverse-prompt/host", json={}).status_code == 200


def test_json_origin_limits_and_resolver_throttle():
    with TestClient(create_app(Settings(_env_file=None), [])) as client:
        url = "/api/party/resolve"
        assert client.post(url, json={"code": "0042"}).status_code == 403
        client.headers["Origin"] = "http://localhost:8000"
        assert client.post(url, content="code=0042").status_code == 415
        assert client.post(url, json={"code": "X" * 70000}).status_code == 413
        for _ in range(20):
            assert client.post(url, json={"code": "9999"}).status_code == 404
        assert client.post(url, json={"code": "9999"}).status_code == 429


async def test_persistent_blocker_survives_party_release():
    from backend.shared.party import PartyCoordinator

    parties = PartyCoordinator()
    await parties.set_blocker("reverse-prompt", "Provider closure needs operator verification.")
    import pytest

    with pytest.raises(AppError, match="operator verification"):
        async with parties.reserve("word-by-word"):
            pass
    await parties.set_blocker("reverse-prompt", None)
    async with parties.reserve("word-by-word") as reservation:
        await reservation.activate()


def test_only_explicit_origin_aliases_are_accepted():
    settings = Settings(_env_file=None, additional_browser_origins=("http://127.0.0.1:5173",))
    with TestClient(create_app(settings, [])) as client:
        allowed = client.post(
            "/api/party/resolve",
            json={"code": "9999"},
            headers={"Origin": "http://127.0.0.1:5173"},
        )
        assert allowed.status_code == 404
        denied = client.post(
            "/api/party/resolve",
            json={"code": "9999"},
            headers={"Origin": "http://127.0.0.1:5174"},
        )
        assert denied.status_code == 403
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(_env_file=None, additional_browser_origins=("http://user@example.com/path",))
