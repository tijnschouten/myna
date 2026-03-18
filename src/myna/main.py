from __future__ import annotations

import logging

from fastapi import FastAPI, Request

from myna.config import get_settings
from myna.middleware.scenario_middleware import ScenarioMiddleware
from myna.request_capture import build_request_record, request_log
from myna.routers import audio, chat, embeddings, images, models
from myna.scenarios import error_response

logger = logging.getLogger("myna")
_CAPTURE_PATH_PREFIX = "/__myna/requests"


def create_app() -> FastAPI:
    settings = get_settings()
    _configure_logging()

    app = FastAPI(title="myna", version="0.1.0")
    app.add_middleware(ScenarioMiddleware)

    @app.middleware("http")
    async def auth_and_request_logging(request: Request, call_next):
        is_capture_endpoint = request.url.path.startswith(_CAPTURE_PATH_PREFIX)

        if settings.mock_log_requests:
            logger.info("%s %s", request.method, request.url.path)

        if not is_capture_endpoint:
            body = await request.body()
            request_record = await build_request_record(request, body)
            request_log.add(request_record)
            request = Request(request.scope, receive=_clone_receive(body))

        if settings.mock_require_auth and not is_capture_endpoint:
            auth_header = request.headers.get("Authorization", "")
            token = auth_header.removeprefix("Bearer ").strip()
            if not auth_header.startswith("Bearer ") or not token:
                return error_response("auth")

        return await call_next(request)

    @app.get("/healthz")
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/__myna/requests")
    async def get_requests() -> dict[str, list[dict[str, object]]]:
        return {"requests": request_log.all()}

    @app.get("/__myna/requests/last")
    async def get_last_request() -> dict[str, dict[str, object] | None]:
        return {"request": request_log.last()}

    @app.delete("/__myna/requests")
    async def clear_requests() -> dict[str, int]:
        return {"cleared": request_log.clear()}

    app.include_router(models.router)
    app.include_router(chat.router)
    app.include_router(embeddings.router)
    app.include_router(images.router)
    app.include_router(audio.router)
    return app


def _clone_receive(body: bytes):
    sent = False

    async def receive() -> dict[str, object]:
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.request", "body": b"", "more_body": False}

    return receive


def _configure_logging() -> None:
    if logger.handlers:
        return
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


app = create_app()
