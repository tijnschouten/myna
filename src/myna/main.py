from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from pydantic import BaseModel, ConfigDict, Field

from myna.config import get_settings
from myna.middleware.scenario_middleware import ScenarioMiddleware
from myna.request_capture import build_request_record, request_log
from myna.response_seeding import SeededResponse, seeded_response_queue
from myna.routers import audio, chat, embeddings, images, models
from myna.scenarios import error_response

logger = logging.getLogger("myna")
_INTERNAL_PREFIXES = ("/__myna/requests", "/__myna/responses")


class NextResponsePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(default="/v1/chat/completions")
    method: str = Field(default="POST")
    status_code: int = Field(default=200, ge=100, le=599)
    headers: dict[str, str] = Field(default_factory=dict)
    json_body: object | None = None
    body_text: str | None = None


def create_app() -> FastAPI:
    settings = get_settings()
    _configure_logging()

    app = FastAPI(title="myna", version="0.1.0")
    app.add_middleware(ScenarioMiddleware)

    @app.middleware("http")
    async def auth_and_request_logging(request: Request, call_next):
        is_internal_endpoint = request.url.path.startswith(_INTERNAL_PREFIXES)

        if settings.mock_log_requests:
            logger.info("%s %s", request.method, request.url.path)

        if not is_internal_endpoint:
            body = await request.body()
            request_record = await build_request_record(request, body)
            request_log.add(request_record)
            request = Request(request.scope, receive=_clone_receive(body))

        if settings.mock_require_auth and not is_internal_endpoint:
            auth_header = request.headers.get("Authorization", "")
            token = auth_header.removeprefix("Bearer ").strip()
            if not auth_header.startswith("Bearer ") or not token:
                return error_response("auth")

        if not is_internal_endpoint:
            seeded = seeded_response_queue.consume(request.method, request.url.path)
            if seeded is not None:
                return seeded.build_response()

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

    @app.post("/__myna/responses/next")
    async def queue_next_response(payload: NextResponsePayload) -> dict[str, bool]:
        seeded_response_queue.add(
            SeededResponse(
                method=payload.method.upper(),
                path=payload.path,
                status_code=payload.status_code,
                headers=payload.headers,
                json_body=payload.json_body,
                body_text=payload.body_text,
            )
        )
        return {"queued": True}

    @app.delete("/__myna/responses")
    async def clear_seeded_responses() -> dict[str, int]:
        return {"cleared": seeded_response_queue.clear()}

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
