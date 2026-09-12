import pytest
from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from backend.app import create_app
from backend.shared.config import Settings
from backend.shared.errors import AppError
from backend.shared.party import PartyCoordinator
from backend.shared.room_codes import FORMAT_MESSAGE, RoomCode, normalize_room_code


@pytest.mark.parametrize("value", ["0042", "0000", "9999", " 0042 "])
def test_code_strings_preserve_leading_zeros(value):
    assert TypeAdapter(RoomCode).validate_python(value) == value.strip()


@pytest.mark.parametrize("value", [42, None, [], "42", "12345", "12 34", "ABCD", "１２３４"])
def test_bad_code_values_are_rejected_without_coercion(value):
    with pytest.raises(AppError) as error:
        TypeAdapter(RoomCode).validate_python(value)
    assert error.value.message == FORMAT_MESSAGE


async def test_atomic_reservation_and_rotation_retry_collisions(monkeypatch):
    candidates = iter([42, 42, 67])
    monkeypatch.setattr("backend.shared.room_codes.secrets.randbelow", lambda _: next(candidates))
    parties = PartyCoordinator()
    async with parties.reserve("word-by-word") as reservation:
        assert reservation.code == "0042"
        await reservation.activate()
    with pytest.raises(AppError):
        async with parties.reserve("prompt-royale"):
            pass
    assert await parties.resolve(" 0042 ") == "word-by-word"
    assert await parties.rotate_code("word-by-word") == "0067"
    with pytest.raises(AppError):
        await parties.resolve("0042")
    assert await parties.resolve("0067") == "word-by-word"
    assert normalize_room_code(parties.party.code) == "0067"
    await parties.begin_close("word-by-word")
    await parties.finish_close("word-by-word")
    with pytest.raises(AppError):
        await parties.resolve("0067")


def test_resolver_enforces_format_before_lookup_and_counts_invalid_attempts():
    with TestClient(create_app(Settings(_env_file=None), [])) as client:
        client.headers["Origin"] = "http://localhost:8000"
        for value in [42, None, [], "42", "12345", "12 34", "ABCD", "１２３４", ""]:
            response = client.post("/api/party/resolve", json={"code": value})
            assert response.status_code == 422
            assert response.json() == {
                "code": "invalid_room_code",
                "message": FORMAT_MESSAGE,
                "field": "code",
            }
        missing = client.post("/api/party/resolve", json={})
        assert missing.json()["message"] == FORMAT_MESSAGE
        for _ in range(10):
            response = client.post("/api/party/resolve", json={"code": " 0042 "})
            assert response.status_code == 404
            assert (
                response.json()["message"]
                == "That party isn't available. Check the code with your host."
            )
        assert client.post("/api/party/resolve", json={"code": "0042"}).status_code == 429
