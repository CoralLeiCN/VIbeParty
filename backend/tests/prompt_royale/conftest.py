import pytest

from backend.games.prompt_royale.config import RoyaleSettings
from backend.games.prompt_royale.engine import Engine
from backend.shared.config import Settings
from backend.shared.contracts import GameContext
from backend.shared.party import PartyCoordinator


class Clock:
    now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture
async def game(tmp_path, request):
    clock = Clock()
    context = GameContext(
        Settings(
            _env_file=None,
            media_root=tmp_path,
            host_passcode="test-code",
            generation_mode="fixture",
        ),
        PartyCoordinator(),
    )
    engine = Engine(context, RoyaleSettings(_env_file=None), clock=clock)
    await engine.startup()
    player_count = getattr(request, "param", 3)
    host, _ = await engine.create(None, "Host", "test-code", "host", player_count)
    tokens = [host]
    for index in range(player_count - 1):
        token, _ = await engine.join(None, f"Player {index}", engine.room.code, str(index))
        tokens.append(token)
    yield engine, tokens, clock
    await engine.shutdown()
