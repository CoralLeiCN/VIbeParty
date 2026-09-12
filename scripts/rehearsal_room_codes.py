"""Controlled fixture server for leading-zero browser acceptance; never a live demo."""

import os

import uvicorn

from backend.shared import party
from backend.shared.config import ROOT, Settings


def main():
    # A separate, explicit test process: production startup always uses secure random codes.
    os.environ["GENERATION_MODE"] = "fixture"
    for flag in (
        "WORD_BY_WORD_LIVE_ENABLED",
        "PROMPT_ROYALE_LIVE_ENABLED",
        "REVERSE_PROMPT_LIVE_ENABLED",
    ):
        os.environ[flag] = "false"
    original = party.generate_room_code

    def controlled_code(exclude=()):
        return "0042" if "0042" not in exclude else original(exclude)

    party.generate_room_code = controlled_code
    from backend.app import create_app

    settings = Settings(generation_mode="fixture", media_root=ROOT / ".local/room-code-rehearsal")
    print("Controlled room-code rehearsal: new codes are 0042; live generation is disabled.")
    uvicorn.run(create_app(settings), host="0.0.0.0", port=settings.backend_port, workers=1)


if __name__ == "__main__":
    main()
