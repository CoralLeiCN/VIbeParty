import asyncio
import sys

import pytest

from backend.games.prompt_royale.media import command as royale_command
from backend.games.reverse_prompt.media import command as reverse_command


@pytest.mark.parametrize(
    "command,message",
    [(royale_command, "Media preparation failed"), (reverse_command, "Video preparation failed")],
)
async def test_media_commands_preserve_output_and_failure_messages(command, message):
    assert await command(sys.executable, "-c", "print('video')") == b"video\n"
    with pytest.raises(ValueError, match=message):
        await command(sys.executable, "-c", "raise SystemExit(1)")


@pytest.mark.parametrize("mode", ["royale_timeout", "royale_cancel", "reverse_cancel"])
async def test_interrupted_media_commands_reap_the_child(monkeypatch, mode):
    create_process = asyncio.create_subprocess_exec
    started = asyncio.Event()
    children = []

    async def track_process(*args, **kwargs):
        child = await create_process(*args, **kwargs)
        children.append(child)
        started.set()
        return child

    monkeypatch.setattr(asyncio, "create_subprocess_exec", track_process)
    command = reverse_command if mode == "reverse_cancel" else royale_command
    options = {"timeout": 0.1} if mode == "royale_timeout" else {}
    task = asyncio.create_task(
        command(sys.executable, "-c", "import time; time.sleep(60)", **options)
    )
    try:
        await asyncio.wait_for(started.wait(), 5)
        if mode != "royale_timeout":
            task.cancel()
        error = TimeoutError if mode == "royale_timeout" else asyncio.CancelledError
        with pytest.raises(error):
            await asyncio.wait_for(task, 5)
        assert children[0].returncode is not None
    finally:
        for child in children:
            if child.returncode is None:
                child.kill()
            await child.wait()
