import asyncio
import json

import pytest

from backend.games.word_by_word.domain import FIXTURE_TEXT, Clip, validate_text
from backend.games.word_by_word.providers import FixtureProvider, scene_prompt
from backend.games.word_by_word.service import Game
from backend.shared.config import Settings
from backend.shared.contracts import GameContext
from backend.shared.errors import AppError
from backend.shared.party import PartyCoordinator


class FakeProvider:
    def __init__(self, fail_at=None, closed=True, hold_at=None):
        self.opens = 0
        self.calls = []
        self.closes = 0
        self.fail_at = fail_at
        self.closed = closed
        self.hold_at = hold_at
        self.entered = asyncio.Event()

    async def open(self):
        self.opens += 1

    async def segment(self, texts, index, destination):
        self.calls.append(scene_prompt(texts, index))
        self.entered.set()
        if index == self.hold_at:
            await asyncio.sleep(60)
        if index == self.fail_at:
            raise TimeoutError
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"saved-private-clip")
        return Clip(destination, 6, 640, 360)

    async def close(self):
        self.closes += 1
        return self.closed


@pytest.fixture
async def setup_game(tmp_path):
    provider = FakeProvider()
    settings = Settings(_env_file=None, media_root=tmp_path, host_passcode="test-passcode")
    game = Game(GameContext(settings, PartyCoordinator()), provider_factory=lambda mode: provider)
    await game.startup()
    host, state = await game.host("test-passcode", None)
    players = []
    for name in ["Ada", "Bo", "Cy"]:
        player, _ = await game.join(state["code"], name, None)
        players.append(player)
    yield game, provider, host, players
    provider.closed = True
    await game.shutdown()


async def start_and_submit(game, host, players, texts=FIXTURE_TEXT, mode="fixture"):
    rid = game.room.round.id
    await game.start(host, rid, mode)
    for i, text in enumerate(texts):
        await game.contribute(players[i % len(players)], rid, i, text)
    await game.task
    await game.cleanup_task
    return rid


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("  They start breakdancing.  ", "They start breakdancing."),
        ("\u3000月の森！\u00a0", "月の森！"),
        ("🦊" * 120, "🦊" * 120),
        ("e\u0301", "e\u0301"),
        ("forest", "forest"),
    ],
)
def test_exact_unicode_text(raw, expected):
    assert validate_text(raw) == expected


@pytest.mark.parametrize("text", ["", " \n\u3000 ", "🦊" * 121, "\ud800", "Some forbidden text"])
def test_invalid_text_is_correctable(text):
    with pytest.raises(AppError) as error:
        validate_text(text, ("forbidden",))
    assert error.value.status == 422
    assert validate_text("Now a valid sentence.") == "Now a valid sentence."


async def test_assignments_ownership_duplicates_and_privacy(setup_game):
    game, provider, host, players = setup_game
    rid = game.room.round.id
    starts = await asyncio.gather(
        game.start(host, rid, "fixture"), game.start(host, rid, "fixture"), return_exceptions=True
    )
    assert sum(isinstance(value, AppError) for value in starts) == 1
    assert [slot.owner for slot in game.room.round.slots] == [*players, players[0]]
    with pytest.raises(AppError) as error:
        await game.contribute(players[1], rid, 0, FIXTURE_TEXT[0])
    assert error.value.status == 403
    await game.contribute(players[0], rid, 0, "  " + FIXTURE_TEXT[0] + "  ")
    await game.contribute(players[0], rid, 0, FIXTURE_TEXT[0])
    with pytest.raises(AppError) as error:
        await game.contribute(players[0], rid, 0, "different")
    assert error.value.code == "contribution_locked"
    assert FIXTURE_TEXT[0] not in json.dumps(game.snapshot(host))
    assert FIXTURE_TEXT[0] not in json.dumps(game.snapshot(players[1]))
    for i in range(1, 4):
        await game.contribute(players[i % 3], rid, i, FIXTURE_TEXT[i])
    await game.task
    await game.cleanup_task
    assert provider.opens == 1
    assert game.snapshot(host)["cards"] == []
    assert game.snapshot(host)["clips"] == []
    assert len(provider.calls) == 4
    for index, prompt in enumerate(provider.calls):
        assert all(text not in prompt for text in FIXTURE_TEXT[index + 1 :])
    with pytest.raises(AppError):
        await game.clip_path(host, rid, 0)
    with pytest.raises(AppError):
        await game.start(players[0], rid, "fixture")
    first = await game.reveal(host, rid, -1)
    assert first["cards"][0]["text"] == FIXTURE_TEXT[0]
    with pytest.raises(AppError):
        await game.reveal(host, rid, -1)
    assert game.room.round.disclosed == 0
    assert await game.clip_path(host, rid, 0)
    with pytest.raises(AppError):
        await game.clip_path(host, rid, 1)
    with pytest.raises(AppError):
        await game.clip_path(players[0], rid, 0)


async def test_four_players_frozen_roster_and_same_roster_rematch(setup_game):
    game, provider, host, players = setup_game
    await game.set_player_count(host, game.room.round.id, 4)
    player, _ = await game.join(game.room.code, "Dee", None)
    players.append(player)
    rid = await start_and_submit(game, host, players)
    assert [slot.owner for slot in game.room.round.slots] == players
    with pytest.raises(AppError):
        await game.join(game.room.code, "Fifth", None)
    restored, _ = await game.join(game.room.code, "Changed name", player)
    assert restored == player
    for expected in range(-1, 4):
        await game.reveal(host, rid, expected)
    assert game.room.round.phase == "RESULTS"
    for i in range(4):
        assert await game.clip_path(host, rid, i)
    assert provider.opens == 1  # replay has no provider path
    state = await game.new_round(host, rid)
    assert state["round_id"] != rid
    assert state["players"] == ["Ada", "Bo", "Cy", "Dee"]
    assert state["player_count"] == 4
    assert list(game.media.iterdir()) == []
    with pytest.raises(AppError):
        await game.contribute(player, rid, 3, FIXTURE_TEXT[3])


@pytest.mark.parametrize("player_count", [1, 2, 3, 4])
async def test_selected_player_count_shares_all_four_contributions(setup_game, player_count):
    game, provider, host, _ = setup_game
    state = await game.new_round(host, game.room.round.id, reset=True)
    rid = state["round_id"]
    await game.set_player_count(host, rid, player_count)
    players = []
    for index in range(player_count):
        with pytest.raises(AppError) as error:
            await game.start(host, rid, "fixture")
        assert error.value.code == "need_players"
        player, state = await game.join(game.room.code, f"Player {index + 1}", None)
        assert state["player_count"] == player_count
        players.append(player)
    with pytest.raises(AppError) as error:
        await game.join(game.room.code, "Extra player", None)
    assert error.value.code == "party_full"
    assert (await game.join(game.room.code, "Refresh", players[0]))[0] == players[0]

    # WW-CAT-01, mapped to the four-slot demo. The provider is an explicit test fake.
    texts = (
        "Enchanted forest",
        "A fox wearing a crown",
        "Dances ballet",
        "Glowing snow begins falling",
    )
    game.live_reason = None
    await game.start(host, rid, "live")
    expected_owners = [players[index % player_count] for index in range(4)]
    assert [slot.owner for slot in game.room.round.slots] == expected_owners
    for index in reversed(range(4)):
        owner = expected_owners[index]
        await game.contribute(owner, rid, index, texts[index])
        assert texts[index] not in json.dumps(game.snapshot(host))
        for player in players:
            if player != owner:
                assert texts[index] not in json.dumps(game.snapshot(player))
    await game.task
    await game.cleanup_task
    assert provider.opens == 1 and len(provider.calls) == 4 and provider.closes == 1
    for expected in range(-1, 4):
        state = await game.reveal(host, rid, expected)
    assert [card["text"] for card in state["cards"]] == list(texts)
    assert [card["contributor"] for card in state["cards"]] == [
        f"Player {index % player_count + 1}" for index in range(4)
    ]
    state = await game.new_round(host, rid)
    assert state["player_count"] == player_count and len(state["players"]) == player_count
    await game.start(host, state["round_id"], "fixture")
    assert [slot.owner for slot in game.room.round.slots] == expected_owners


async def test_input_deadline_rejects_late_final_submission(setup_game):
    game, provider, host, players = setup_game
    now = [1000.0]
    game.clock = lambda: now[0]
    game.room.activity = now[0]
    rid = game.room.round.id
    await game.start(host, rid, "fixture")
    for i in range(3):
        await game.contribute(players[i], rid, i, FIXTURE_TEXT[i])
    now[0] += 45
    with pytest.raises(AppError) as error:
        await game.contribute(players[0], rid, 3, FIXTURE_TEXT[3])
    assert error.value.code == "collection_closed"
    assert game.snapshot(host)["result"] == "incomplete"
    assert game.snapshot(host)["cards"] == []
    assert provider.opens == 0


async def test_partial_prefix_and_closure_guard(setup_game):
    game, provider, host, players = setup_game
    provider.fail_at = 2
    provider.closed = False
    rid = await start_and_submit(game, host, players)
    state = game.snapshot(host)
    assert state["phase"] == "REVEAL" and state["result"] == "partial"
    assert state["saved_clips"] == 2 and state["provider_closing"]
    await game.reveal(host, rid, -1)
    assert await game.clip_path(host, rid, 0)
    await game.end(host, rid)
    assert len(game.snapshot(host)["cards"]) == 1
    with pytest.raises(AppError):
        await game.new_round(host, rid)
    provider.closed = True
    await game.retry_cleanup(host, rid)
    await game.cleanup_task
    await game.new_round(host, rid)
    assert game.room.round.phase == "LOBBY"


async def test_end_generation_cancels_and_never_discloses(setup_game):
    game, provider, host, players = setup_game
    provider.hold_at = 1
    rid = game.room.round.id
    await game.start(host, rid, "fixture")
    for i in range(4):
        await game.contribute(players[i % 3], rid, i, FIXTURE_TEXT[i])
    while len(provider.calls) < 2:
        await asyncio.sleep(0.001)
    await game.end(host, rid)
    await game.task
    await game.cleanup_task
    assert len(provider.calls) == 2
    assert game.room.round.phase == "RESULTS"
    assert game.snapshot(host)["cards"] == []
    with pytest.raises(AppError):
        await game.clip_path(host, rid, 0)
    await game.new_round(host, rid)
    assert game.room.round.clips == []


async def test_bounded_step_timeout(setup_game):
    game, provider, host, players = setup_game
    game.step_seconds = 0.02
    provider.hold_at = 1
    await asyncio.wait_for(start_and_submit(game, host, players), 1)
    assert game.room.round.result == "partial"
    assert len(game.room.round.clips) == 1
    assert provider.closes == 1


async def test_live_attempts_survive_reset_and_close(setup_game):
    game, provider, host, players = setup_game
    game.live_reason = None  # test fake, no Reactor SDK
    for i in range(3):
        rid = await start_and_submit(game, host, players, mode="live")
        await game.end(host, rid)
        if i < 2:
            await game.new_round(host, rid)
    with pytest.raises(AppError) as error:
        await game.new_round(host, rid)
    assert error.value.code == "attempts_exhausted"
    await game.new_round(host, rid, reset=True)
    assert game.attempts == 3 and provider.opens == 3
    assert await game.close(host)
    assert game.attempts == 3


async def test_polling_does_not_extend_inactivity_and_expiry_clears(setup_game):
    game, provider, host, players = setup_game
    now = [1000.0]
    game.clock = lambda: now[0]
    game.room.activity = now[0]
    for _ in range(10):
        now[0] += 180
        game.snapshot(host)
    await game.tick()
    await game.expiry_task
    assert game.room is None
    assert await game.context.parties.public_state() is None


async def test_closing_unresolved_provider_blocks_other_game(setup_game):
    game, provider, host, players = setup_game
    provider.closed = False
    await start_and_submit(game, host, players)
    assert not await game.close(host)
    with pytest.raises(AppError) as error:
        async with game.context.parties.reserve("prompt-royale"):
            pass
    assert error.value.code == "cleanup_pending"
    provider.closed = True
    assert await game.close(host)
    async with game.context.parties.reserve("prompt-royale") as reservation:
        await reservation.activate()


async def test_fixture_rejects_arbitrary_contribution(setup_game):
    game, provider, host, players = setup_game
    rid = game.room.round.id
    await game.start(host, rid, "fixture")
    with pytest.raises(AppError) as error:
        await game.contribute(players[0], rid, 0, "An arbitrary city.")
    assert error.value.code == "fixture_text_required"
    assert game.room.round.slots[0].text is None


async def test_fixture_files_decode_and_match_fixed_sequence(tmp_path):
    provider = FixtureProvider()
    for i in range(4):
        clip = await provider.segment(list(FIXTURE_TEXT), i, tmp_path / f"{i}.mp4")
        assert clip.duration == 6 and (clip.width, clip.height) == (640, 360)
    with pytest.raises(ValueError):
        await provider.segment(["arbitrary"] * 4, 0, tmp_path / "bad.mp4")
