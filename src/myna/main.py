from __future__ import annotations

import logging

from fastapi import FastAPI, Request

from myna.config import get_settings
from myna.middleware.scenario_middleware import ScenarioMiddleware
from myna.routers import audio, chat, embeddings, images, models
from myna.scenarios import error_response

logger = logging.getLogger("myna")


def create_app() -> FastAPI:
    settings = get_settings()
    _configure_logging()

    app = FastAPI(title="myna", version="0.1.0")
    app.add_middleware(ScenarioMiddleware)

    @app.middleware("http")
    async def auth_and_request_logging(request: Request, call_next):
        if settings.mock_log_requests:
            logger.info("%s %s", request.method, request.url.path)

        if settings.mock_require_auth:
            auth_header = request.headers.get("Authorization", "")
            token = auth_header.removeprefix("Bearer ").strip()
            if not auth_header.startswith("Bearer ") or not token:
                return error_response("auth")

        return await call_next(request)

    @app.get("/healthz")
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(models.router)
    app.include_router(chat.router)
    app.include_router(embeddings.router)
    app.include_router(images.router)
    app.include_router(audio.router)
    return app


def _configure_logging() -> None:
    if logger.handlers:
        return
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


app = create_app()
