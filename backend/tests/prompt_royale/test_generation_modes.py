import asyncio

import pytest

from backend.games.prompt_royale.engine import uid
from backend.games.prompt_royale.helios import HeliosVideo
from backend.shared.errors import AppError
from backend.tests.prompt_royale.test_providers import ScriptedVideo
from backend.tests.prompt_royale.test_rules import host_action, screen, start


def enable_live(engine):
    engine.settings.prompt_royale_live_enabled = True
    engine.settings.prompt_royale_live_slot = "unit-test-no-provider-calls"
    engine.settings.prompt_royale_rehearsed_capacity = 4
    engine.settings.reactor_api_key = "test-only"


@pytest.mark.parametrize("game", [1], indirect=True)
async def test_switch_routes_rounds_to_selected_provider_and_preserves_allowance(game):
    engine, tokens, _ = game
    # Live is available independently of the server's fixture default.
    assert isinstance(engine.live_video, HeliosVideo)
    enable_live(engine)
    live = engine.live_video = ScriptedVideo(["success"])
    engine.settings.prompt_royale_live_session_starts = 2

    selected = await host_action(engine, tokens, "generation-mode", mode="live")
    assert selected["mode"] == "live"
    assert selected["lobby"]["live_unavailable_reason"] is None
    assert engine.context.settings.generation_mode == "fixture"
    r = await start(engine, tokens)
    with pytest.raises(AppError) as error:
        await host_action(engine, tokens, "generation-mode", mode="fixture")
    assert error.value.code == "wrong_phase"
    await engine.mutate(
        tokens[0], "submission", {"round_id": r.id, "prompt": "A penguin opens a hotel."}
    )
    await asyncio.gather(*list(engine.generation_tasks))
    assert r.phase == "screening" and len(live.calls) == engine.starts == 1
    assert "A penguin opens a hotel." in live.calls[0][0]
    await host_action(engine, tokens, "open-voting", watched=True)
    await engine.again(
        tokens[0],
        {"command_id": uid(), "expected_version": engine.room.version, "round_id": r.id},
    )

    await host_action(engine, tokens, "generation-mode", mode="fixture")
    r = await screen(engine, tokens)
    assert engine.video is engine.fixture_video
    assert len(live.calls) == engine.starts == 1
    await host_action(engine, tokens, "open-voting", watched=True)
    await engine.again(
        tokens[0],
        {"command_id": uid(), "expected_version": engine.room.version, "round_id": r.id},
    )
    await host_action(engine, tokens, "generation-mode", mode="live")
    assert engine.video is live
    with pytest.raises(AppError) as error:
        await start(engine, tokens)
    assert error.value.code == "allowance"
    assert len(live.calls) == engine.starts == 1


async def test_mode_switch_enforces_host_readiness_version_and_cleanup(game):
    engine, tokens, _ = game
    before = engine.room.version
    with pytest.raises(AppError) as error:
        await host_action(engine, tokens[1:], "generation-mode", mode="live")
    assert error.value.code == "host_only"
    with pytest.raises(AppError) as error:
        await host_action(engine, tokens, "generation-mode", mode="live")
    assert error.value.code == "live_not_ready"
    assert engine.room.mode == "fixture" and engine.video is engine.fixture_video
    assert engine.room.version == before

    enable_live(engine)
    engine.settings.reactor_api_key = ""
    with pytest.raises(AppError) as error:
        await host_action(engine, tokens, "generation-mode", mode="live")
    assert "API key" in error.value.message
    enable_live(engine)
    command = {"command_id": uid(), "expected_version": before, "mode": "live"}
    selected = await engine.mutate(tokens[0], "generation-mode", command)
    assert (await engine.state(tokens[1]))["mode"] == "live"
    assert "lobby" not in await engine.state(tokens[1])
    replay = await engine.mutate(tokens[0], "generation-mode", command)
    assert replay["version"] == selected["version"]
    with pytest.raises(AppError) as error:
        await engine.mutate(
            tokens[0], "generation-mode", {**command, "command_id": uid(), "mode": "fixture"}
        )
    assert error.value.code == "state_changed"

    engine.blocked = True
    with pytest.raises(AppError) as error:
        await host_action(engine, tokens, "generation-mode", mode="fixture")
    assert error.value.code == "cleanup_pending"
    assert engine.room.mode == "live" and engine.video is engine.live_video
    engine.blocked = False
    await host_action(engine, tokens, "generation-mode", mode="fixture")
    assert (await engine.state(tokens[1]))["mode"] == "fixture"
