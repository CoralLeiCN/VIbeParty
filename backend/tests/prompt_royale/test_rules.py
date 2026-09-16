import asyncio
import json

import pytest

from backend.games.prompt_royale.config import TOPICS
from backend.games.prompt_royale.engine import uid
from backend.games.prompt_royale.providers import ProviderFailure
from backend.games.prompt_royale.validation import PromptValidator
from backend.shared.errors import AppError


async def host_action(e, tokens, action, **data):
    return await e.mutate(
        tokens[0],
        action,
        {
            "command_id": uid(),
            "expected_version": e.room.version,
            "round_id": e.room.round.id if e.room.round else None,
            **data,
        },
    )


async def start(e, tokens):
    await host_action(e, tokens, "topic", mode="bundled", topic=TOPICS[0])
    await host_action(e, tokens, "start")
    return e.room.round


async def screen(e, tokens):
    r = await start(e, tokens)
    for index, token in enumerate(tokens):
        await e.mutate(token, "submission", {"round_id": r.id, "prompt": f"Private scene {index}"})
    await asyncio.gather(*list(e.generation_tasks))
    assert r.phase == "screening"
    return r


async def test_full_round_privacy_stable_arena_refresh_replay(game):
    e, tokens, _ = game
    code = e.room.code
    assert len(code) == 4 and code.isascii() and code.isdecimal()
    r = await start(e, tokens)
    await e.mutate(tokens[0], "submission", {"round_id": r.id, "prompt": "The secret moon penguin"})
    guest = await e.state(tokens[1])
    assert "secret moon" not in json.dumps(guest) and "arena" not in guest
    for index, token in enumerate(tokens[1:]):
        await e.mutate(token, "submission", {"round_id": r.id, "prompt": f"Guest secret {index}"})
    entry = next(iter(r.entries.values()))
    with pytest.raises(AppError):
        await e.media(tokens[0], entry.id)
    await asyncio.gather(*list(e.generation_tasks))
    views = [await e.state(token) for token in tokens]
    assert all(view["code"] == code for view in views)
    assert views[0]["arena"] == views[1]["arena"] == views[2]["arena"]
    assert views[0]["arena"][3]["status"] == "empty"
    assert all(
        "author" not in tile and "prompt" not in tile and "own" not in tile
        for tile in views[0]["arena"]
    )
    with pytest.raises(AppError):
        await e.media(None, entry.id)
    assert (await e.media(tokens[1], entry.id)).exists()
    arena = list(r.arena)
    await host_action(e, tokens, "open-voting", watched=True)
    for token in tokens:
        state = await e.state(token)
        target = next(tile["id"] for tile in state["arena"] if tile.get("id") and not tile["own"])
        await e.mutate(token, "vote", {"round_id": r.id, "entry_id": target})
    assert r.phase == "results" and sum(r.scores.values()) == 3
    assert r.arena == arena
    state = await e.state(tokens[0])
    assert "author" in state["arena"][0]
    assert "votes" not in state and "ballots" not in state
    folder = e.root / r.id
    await e.again(tokens[0], {"round_id": r.id, "expected_version": e.room.version})
    assert not folder.exists() and not e.room.round and not e.room.topic
    assert not e.room.confirmed_id and len(e.room.players) == 3
    assert e.room.code == code
    assert await e.context.parties.resolve(code) == "prompt-royale"


async def test_cap_identity_normalization_and_concurrent_join(game):
    e, tokens, _ = game
    await host_action(e, tokens, "player-count", player_count=4)
    responses = await asyncio.gather(
        e.join(None, "Host", e.room.code, "new1"),
        e.join(None, "Other", e.room.code, "new2"),
        return_exceptions=True,
    )
    assert sum(isinstance(r, AppError) for r in responses) == 1
    assert len(e.room.players) == 4
    duplicate, _ = await e.join(tokens[1], "Imposter", e.room.code, "known")
    assert duplicate == tokens[1] and len(e.room.players) == 4
    with pytest.raises(AppError) as error:
        await e.join(None, "Fifth", e.room.code, "fifth")
    assert error.value.code == "room_full"
    await start(e, tokens)
    with pytest.raises(AppError):
        await e.join(None, "Late", e.room.code, "late")


async def test_topic_confirmation_regeneration_deduplication_and_failure(game):
    e, tokens, _ = game
    await host_action(e, tokens, "generate-topic")
    await asyncio.gather(*list(e.tasks))
    first = e.room.suggestion_id
    with pytest.raises(AppError):
        await host_action(e, tokens, "start")
    await host_action(e, tokens, "confirm-topic", suggestion_id=first)
    assert e.room.confirmed_id == first
    request = {"command_id": uid(), "expected_version": e.room.version}
    await e.mutate(tokens[0], "generate-topic", request)
    await e.mutate(tokens[0], "generate-topic", request)
    assert not e.room.confirmed_id
    await asyncio.gather(*list(e.tasks))
    assert e.room.suggestion_id != first and e.topics.fixture_index == 2
    with pytest.raises(AppError):
        await host_action(e, tokens, "confirm-topic", suggestion_id=first)
    await host_action(e, tokens, "confirm-topic", suggestion_id=e.room.suggestion_id)
    await host_action(e, tokens, "start")
    assert e.room.round.topic_mode == "llm"


async def test_stale_topic_completion_cannot_replace_bundled_choice(game):
    e, tokens, _ = game
    release = asyncio.Event()

    class SlowTopics:
        calls = 0

        async def suggest(self):
            await release.wait()
            return "A stale topic"

    e.topics = SlowTopics()
    await host_action(e, tokens, "generate-topic")
    await host_action(e, tokens, "topic", mode="bundled", topic=TOPICS[2])
    release.set()
    await asyncio.gather(*list(e.tasks))
    assert e.room.topic == TOPICS[2] and not e.room.suggestion_id

    class BrokenTopics:
        calls = 0

        async def suggest(self):
            raise ProviderFailure("failure")

    e.topics = BrokenTopics()
    await host_action(e, tokens, "generate-topic")
    await asyncio.gather(*list(e.tasks))
    assert e.room.topic_error and not e.room.topic_pending
    await host_action(e, tokens, "topic", mode="bundled", topic=TOPICS[1])
    await host_action(e, tokens, "start")


async def test_locked_submission_and_character_rejection(game):
    e, tokens, _ = game
    r = await start(e, tokens)
    with pytest.raises(AppError) as error:
        await e.mutate(tokens[0], "submission", {"round_id": r.id, "prompt": "é" * 501})
    assert error.value.code == "invalid_length"
    data = {"round_id": r.id, "prompt": "  Cafe\u0301 penguin  "}
    await e.mutate(tokens[0], "submission", data)
    await e.mutate(tokens[0], "submission", data)
    assert r.submissions[e.room.host] == "Café penguin"
    with pytest.raises(AppError):
        await e.mutate(tokens[0], "submission", {"round_id": r.id, "prompt": "Changed"})


async def test_exclusion_vote_race_self_vote_and_frozen_deadline(game):
    e, tokens, clock = game
    r = await screen(e, tokens)
    target = r.arena[0]
    old_version = e.room.version
    await host_action(e, tokens, "exclude", entry_id=target, reason="Playback failed")
    with pytest.raises(AppError):
        await e.media(tokens[1], target)
    with pytest.raises(AppError):
        await e.mutate(
            tokens[0],
            "open-voting",
            {
                "command_id": uid(),
                "expected_version": old_version,
                "round_id": r.id,
                "watched": True,
            },
        )
    opening = {
        "command_id": uid(),
        "expected_version": e.room.version,
        "round_id": r.id,
        "watched": True,
    }
    await e.mutate(tokens[0], "open-voting", opening)
    deadline = r.deadline
    clock.now += 1
    await e.mutate(tokens[0], "open-voting", opening)
    assert r.deadline == deadline
    with pytest.raises(AppError):
        await host_action(e, tokens, "exclude", entry_id=r.ballot[0], reason="Too late")
    for token in tokens:
        pid = e.room.sessions[token]
        own = next((eid for eid in r.ballot if r.entries[eid].player == pid), None)
        if own:
            with pytest.raises(AppError) as error:
                await e.mutate(token, "vote", {"round_id": r.id, "entry_id": own})
            assert error.value.code == "self_vote"
    with pytest.raises(AppError):
        await e.mutate(tokens[1], "vote", {"round_id": r.id, "entry_id": target})
    clock.now = deadline
    with pytest.raises(AppError):
        await e.mutate(tokens[1], "vote", {"round_id": r.id, "entry_id": r.ballot[0]})
    assert r.phase == "results" and not r.votes and not r.winners
    excluded = next(t for t in (await e.state(tokens[0]))["arena"] if t.get("id") == target)
    assert (
        excluded["status"] == "excluded" and "author" not in excluded and "prompt" not in excluded
    )


async def test_tie_abstention_changed_ballot_and_zero_votes(game):
    e, tokens, _ = game
    await host_action(e, tokens, "player-count", player_count=4)
    fourth, _ = await e.join(None, "Fourth", e.room.code, "fourth")
    tokens.append(fourth)
    r = await screen(e, tokens)
    await host_action(e, tokens, "open-voting", watched=True)
    pid_to_entry = {entry.player: entry.id for entry in r.entries.values()}
    choices = [pid_to_entry[e.room.sessions[tokens[1]]], pid_to_entry[e.room.sessions[tokens[0]]]]
    for index, token in enumerate(tokens):
        data = {"round_id": r.id, "entry_id": choices[index % 2]}
        await e.mutate(token, "vote", data)
        await e.mutate(token, "vote", data)
    assert len(r.winners) == 2 and sorted(r.scores.values()) == [0, 0, 2, 2]
    with pytest.raises(AppError):
        await e.mutate(tokens[0], "vote", {"round_id": r.id, "entry_id": None})
    await e.again(tokens[0], {"round_id": r.id, "expected_version": e.room.version})
    r = await screen(e, tokens)
    await host_action(e, tokens, "open-voting", watched=True)
    for token in tokens:
        await e.mutate(token, "vote", {"round_id": r.id, "entry_id": None})
    assert not r.winners and sum(r.scores.values()) == 0


async def test_deadlines_host_absence_missing_entries_and_inactivity(game):
    e, tokens, clock = game
    r = await start(e, tokens)
    e.room.players[e.room.host].seen = clock.now - 30
    await e.tick()
    assert r.phase == "results" and "host connection was lost" in r.reason
    await e.again(tokens[0], {"round_id": r.id, "expected_version": e.room.version})
    r = await start(e, tokens)
    await e.mutate(tokens[0], "submission", {"round_id": r.id, "prompt": "Single scene"})
    clock.now = r.deadline
    e.room.players[e.room.host].seen = clock.now
    await e.tick()
    await asyncio.gather(*list(e.generation_tasks))
    assert len(r.arena) == 1
    clock.now = r.deadline
    e.room.players[e.room.host].seen = clock.now
    await e.tick()
    assert r.phase == "results" and r.reason == "Arena screening was not completed."
    code = e.room.code
    e.room.seen = clock.now - 7200
    await e.tick()
    await asyncio.gather(*list(e.tasks))
    assert e.room is None and await e.context.parties.public_state() is None
    with pytest.raises(AppError) as error:
        await e.context.parties.resolve(code)
    assert error.value.status == 404
    with pytest.raises(AppError) as error:
        await e.state(tokens[0])
    assert error.value.status == 401


async def test_cleanup_blocks_switch_and_counters_survive_close(game):
    e, tokens, _ = game
    r = await screen(e, tokens)
    await host_action(e, tokens, "abort")
    e.starts = 9
    assert await e.close(tokens[0])
    assert not (e.root / r.id).exists() and e.starts == 9
    with pytest.raises(AppError):
        await e.state(tokens[1])


@pytest.mark.parametrize("game", [1, 2, 3, 4], indirect=True)
async def test_selected_player_count_round_and_replay(game):
    e, tokens, _ = game
    size = len(tokens)
    assert (await e.state(tokens[0]))["player_count"] == size
    with pytest.raises(AppError) as error:
        await e.join(None, "Extra", e.room.code, "extra")
    assert error.value.code == "room_full"

    r = await screen(e, tokens)
    assert len(r.arena) == size
    with pytest.raises(AppError) as error:
        await host_action(e, tokens, "player-count", player_count=size)
    assert error.value.code == "wrong_phase"
    await host_action(e, tokens, "open-voting", watched=True)
    if size == 1:
        assert r.phase == "results" and not r.scored and not r.winners
    else:
        assert r.phase == "voting"
        for token in tokens:
            state = await e.state(token)
            target = next(tile["id"] for tile in state["arena"] if tile.get("own") is False)
            await e.mutate(token, "vote", {"round_id": r.id, "entry_id": target})
        assert r.phase == "results" and r.scored and sum(r.scores.values()) == size
    await e.again(tokens[0], {"round_id": r.id, "expected_version": e.room.version})
    assert e.room.player_count == size and len(e.room.players) == size


async def test_player_count_changes_require_host_and_enough_players(game):
    e, tokens, _ = game
    with pytest.raises(AppError) as error:
        await host_action(e, tokens[1:], "player-count", player_count=4)
    assert error.value.status == 403
    with pytest.raises(AppError) as error:
        await host_action(e, tokens, "player-count", player_count=2)
    assert error.value.code == "player_count" and e.room.player_count == 3
    await host_action(e, tokens, "player-count", player_count=4)
    assert (await e.state(tokens[1]))["player_count"] == 4
    with pytest.raises(AppError) as error:
        await start(e, tokens)
    assert error.value.code == "player_count" and e.room.round is None
    await host_action(e, tokens, "player-count", player_count=3)
    await start(e, tokens)


def test_fast_h3_full_prompt_limit_and_unicode():
    validator = PromptValidator()
    # Characters that consumed multiple Helios tokens are valid within FastH3's limit.
    prompt, count = validator.validate(TOPICS[4], "🤹" * 500)
    assert len(prompt) == 500 and count <= 800
    prompt, count = validator.validate("x" * 231, "y" * 500)
    assert count == 800
    with pytest.raises(AppError) as error:
        validator.validate("x" * 232, "y" * 500)
    assert error.value.code == "prompt_size"


@pytest.mark.parametrize("game", [1, 2, 3], indirect=True)
async def test_live_start_requires_capacity_and_reserved_attempts(game):
    e, tokens, _ = game
    size = len(tokens)
    e.room.mode = "live"
    e.video = e.live_video  # No provider calls; this test stops at Start admission.
    e.settings.prompt_royale_live_enabled = True
    e.settings.prompt_royale_live_slot = "unit-test-no-calls"
    e.settings.reactor_api_key = "fake"
    e.settings.prompt_royale_rehearsed_capacity = size
    e.settings.prompt_royale_live_session_starts = 2 * size - 1
    await host_action(e, tokens, "topic", mode="bundled", topic=TOPICS[0])
    with pytest.raises(AppError) as error:
        await host_action(e, tokens, "start")
    assert error.value.code == "allowance"
    e.settings.prompt_royale_live_session_starts = 16
    await host_action(e, tokens, "player-count", player_count=size + 1)
    await e.join(None, "Extra", e.room.code, "extra")
    with pytest.raises(AppError) as error:
        await host_action(e, tokens, "start")
    assert error.value.code == "live_capacity"


async def test_failed_media_cleanup_preserves_party_admission(game, monkeypatch):
    e, tokens, _ = game
    await screen(e, tokens)

    def fail(_):
        raise PermissionError("test denial")

    monkeypatch.setattr("backend.games.prompt_royale.engine.shutil.rmtree", fail)
    with pytest.raises(AppError) as error:
        await e.close(tokens[0])
    assert error.value.code == "cleanup_pending"
    assert e.room.closing and (await e.context.parties.public_state())["status"] == "closing"
    monkeypatch.undo()
    assert await e.close(tokens[0])


async def test_successful_command_receipts_refresh_host_presence_but_errors_do_not(game):
    e, tokens, clock = game
    await host_action(e, tokens, "topic", mode="bundled", topic=TOPICS[0])
    command = {"command_id": uid(), "expected_version": e.room.version, "round_id": None}
    await e.mutate(tokens[0], "start", command)
    clock.now += 20
    await e.mutate(tokens[0], "start", command)
    acknowledged_at = clock.now
    clock.now += 20
    await e.tick()
    assert e.room.round.phase == "prompting"
    with pytest.raises(AppError):
        await host_action(e, tokens, "start")
    assert e.room.players[e.room.host].seen == acknowledged_at


@pytest.mark.parametrize("configured", ["", "  ", "change-me", "changeme", "your-passcode"])
async def test_missing_or_placeholder_host_configuration_is_unavailable(game, configured):
    e, _, _ = game
    e.context.settings.host_passcode = configured
    with pytest.raises(AppError) as error:
        await e.create(None, "New host", configured, "new-client")
    assert error.value.code == "host_not_configured" and error.value.status == 503
