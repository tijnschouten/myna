from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from myna.config import Settings, get_settings
from myna.generators import generate_embedding_vector
from myna.routers.utils import apply_scenario_or_error, parse_json_body

router = APIRouter(prefix="/v1", tags=["embeddings"])


@router.post("/embeddings")
async def create_embeddings(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    payload = await parse_json_body(request)
    _, early_response = await apply_scenario_or_error(request, settings)
    if early_response is not None:
        return early_response

    raw_input = payload.get("input", "")
    normalized_input = raw_input if isinstance(raw_input, list) else [raw_input]

    data = []
    for index, item in enumerate(normalized_input):
        data.append(
            {
                "object": "embedding",
                "index": index,
                "embedding": generate_embedding_vector(item, settings.mock_embedding_dims),
            }
        )

    prompt_tokens = sum(
        max(1, len(str(item).split()))
        for item in normalized_input
        if str(item).strip()
    )
    response_payload = {
        "object": "list",
        "data": data,
        "model": str(payload.get("model") or "mock-embedding-v1"),
        "usage": {"prompt_tokens": prompt_tokens, "total_tokens": prompt_tokens},
    }
    return JSONResponse(response_payload)
