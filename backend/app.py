import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.games.prompt_royale import integration as prompt_royale
from backend.games.reverse_prompt import integration as reverse_prompt
from backend.games.word_by_word import integration as word_by_word
from backend.games.word_by_word.images import MAX_UPLOAD_BYTES
from backend.shared.api import AttemptLimiter, router
from backend.shared.config import ROOT, Settings
from backend.shared.contracts import GameContext
from backend.shared.errors import AppError
from backend.shared.party import PartyCoordinator


def create_app(settings: Settings | None = None, integrations=None) -> FastAPI:
    settings = settings or Settings()
    games = (
        integrations if integrations is not None else [word_by_word, prompt_royale, reverse_prompt]
    )
    parties = PartyCoordinator()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        started = []
        try:
            for game in games:
                await game.startup(GameContext(settings, parties))
                started.append(game)
            yield
        finally:
            for game in reversed(started):
                await game.shutdown()

    app = FastAPI(title="VibeParty", lifespan=lifespan)
    app.state.settings = settings
    app.state.parties = parties
    app.state.games = {game.game_id: game for game in games}
    app.state.resolve_limiter = AttemptLimiter()

    @app.exception_handler(AppError)
    async def app_error(request: Request, error: AppError):
        return JSONResponse(error.payload(), status_code=error.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError):
        return JSONResponse(
            {"code": "invalid_input", "message": "Check the form and try again."}, status_code=422
        )

    @app.middleware("http")
    async def protect_api(request: Request, call_next):
        if request.url.path.startswith("/api/") and request.method not in {
            "GET",
            "HEAD",
            "OPTIONS",
        }:
            if request.headers.get("origin") not in settings.allowed_origins:
                return JSONResponse(
                    {
                        "code": "untrusted_origin",
                        "message": "Open the app at the configured laptop address.",
                    },
                    status_code=403,
                )
            image_upload = request.method == "PUT" and re.fullmatch(
                r"/api/games/word-by-word/round/[A-Za-z0-9_-]{1,100}/starting-image",
                request.url.path,
            )
            content_types = (
                {"image/png", "image/jpeg", "image/webp"} if image_upload else {"application/json"}
            )
            if request.headers.get("content-type", "").split(";")[0] not in content_types:
                return JSONResponse(
                    {
                        "code": "image_type_required" if image_upload else "json_required",
                        "message": "Choose a PNG, JPEG, or WebP image."
                        if image_upload
                        else "Send this request as JSON.",
                    },
                    status_code=415,
                )
            # The single upload route has its own cap; all other commands stay small JSON.
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > (MAX_UPLOAD_BYTES if image_upload else 65536):
                    return JSONResponse(
                        {
                            "code": "request_too_large",
                            "message": "Choose an image smaller than 10 MB."
                            if image_upload
                            else "That request is too large.",
                        },
                        status_code=413,
                    )
            request._body = bytes(body)
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            cache_control = response.headers.get("Cache-Control", "")
            if "no-store" not in cache_control.lower():
                response.headers["Cache-Control"] = ", ".join(
                    filter(None, [cache_control, "no-store"])
                )
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    app.include_router(router, prefix="/api")
    for game in games:
        app.include_router(game.router, prefix=f"/api/games/{game.game_id}")

    @app.get("/health")
    @app.get("/health/live")
    @app.get("/health/ready")
    async def health():
        return {"status": "ok"}

    frontend = ROOT / "frontend/dist"
    if (frontend / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=frontend / "assets"), name="assets")

    @app.get("/{path:path}")
    async def frontend_route(path: str):
        if path.startswith(("api/", "health/", ".", "media/", "assets/")):
            return JSONResponse(
                {"code": "not_found", "message": "Page not found."}, status_code=404
            )
        if (frontend / "index.html").is_file():
            return FileResponse(frontend / "index.html", headers={"Cache-Control": "no-cache"})
        return JSONResponse(
            {
                "code": "frontend_not_built",
                "message": "Build the frontend, or use the Vite development server.",
            },
            status_code=503,
        )

    return app


app = create_app()
