from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from myna.config import Settings, get_settings
from myna.routers.utils import apply_scenario_or_error

router = APIRouter(prefix="/v1", tags=["models"])


@router.get("/models")
async def list_models(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    _, early_response = await apply_scenario_or_error(request, settings)
    if early_response is not None:
        return early_response

    model_ids = [
        settings.mock_default_model,
        "mock-chat-lite-v1",
        "mock-embedding-v1",
        "mock-image-v1",
        "mock-tts-v1",
        "mock-asr-v1",
    ]

    unique_model_ids = list(dict.fromkeys(model_ids))
    data = [
        {"id": model_id, "object": "model", "created": 0, "owned_by": "myna"}
        for model_id in unique_model_ids
    ]
    return JSONResponse({"object": "list", "data": data})
