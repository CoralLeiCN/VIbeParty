"""INTERNAL TEST FAKE: production UI/rules, arbitrary input, unrelated fixture video.

Use the built frontend directly at port 8011. Never use this server for live/demo
acceptance. It cannot construct a Reactor provider, regardless of environment.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import uvicorn  # noqa: E402
from fastapi.responses import HTMLResponse  # noqa: E402

from backend.app import create_app  # noqa: E402
from backend.games.word_by_word import integration  # noqa: E402
from backend.games.word_by_word.domain import FIXTURE_TEXT  # noqa: E402
from backend.games.word_by_word.providers import FixtureProvider  # noqa: E402
from backend.games.word_by_word.service import Game  # noqa: E402
from backend.shared import party  # noqa: E402
from backend.shared.config import ROOT, Settings  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=["full", "partial"], default="partial")
    parser.add_argument(
        "--code-0042", action="store_true", help="Controlled leading-zero code check"
    )
    args = parser.parse_args()
    if args.code_0042:
        original_generate = party.generate_room_code
        party.generate_room_code = lambda exclude=(): (
            "0042" if not exclude else original_generate(exclude)
        )

    class TestProvider(FixtureProvider):
        close_calls = 0

        async def segment(self, texts, index, destination):
            if args.scenario == "partial" and index == 2:
                raise TimeoutError("internal fake timeout")
            return await super().segment(list(FIXTURE_TEXT), index, destination)

        async def close(self):
            self.close_calls += 1
            return args.scenario == "full" or self.close_calls > 1

    class RehearsalGame(Game):
        def __init__(self, context):
            super().__init__(context, provider_factory=lambda _: TestProvider())
            self.live_reason = None

        async def start(self, token, round_id, mode):
            # Exercise arbitrary input through the real live validation path using
            # a hardcoded fake factory. No provider or gate override in the app.
            return await super().start(token, round_id, "live")

        def snapshot(self, token):
            state = super().snapshot(token)
            state["mode"] = "fixture"
            state["live_unavailable_reason"] = "INTERNAL TEST FAKE: live generation is impossible."
            return state

    integration.Game = RehearsalGame
    settings = Settings(
        public_origin="http://localhost:8011",
        browser_origin="http://localhost:8011",
        additional_browser_origins=(
            "http://127.0.0.1:8011",
            "http://a.localhost:8011",
            "http://b.localhost:8011",
        ),
        media_root=ROOT / ".local/word-by-word-internal-fake",
    )
    app = create_app(settings, integrations=[integration])
    page = (
        (ROOT / "frontend/dist/index.html")
        .read_text()
        .replace(
            "<body>",
            '<body><aside style="position:sticky;top:0;z-index:999;background:#fff0a0;'
            'color:#221a00;padding:12px;text-align:center;font:700 16px sans-serif">'
            "INTERNAL TEST FAKE — arbitrary input and synthetic failure. "
            "Videos are unrelated prerecorded fixtures. No AI or provider calls.</aside>",
        )
    )

    @app.middleware("http")
    async def labelled_test_page(request, call_next):
        if request.method == "GET" and request.url.path.startswith("/games/word-by-word/"):
            return HTMLResponse(page, headers={"Cache-Control": "no-store"})
        return await call_next(request)

    print("INTERNAL TEST FAKE at http://localhost:8011 — no provider requests possible.")
    uvicorn.run(app, host="127.0.0.1", port=8011, workers=1, access_log=False)


if __name__ == "__main__":
    main()
