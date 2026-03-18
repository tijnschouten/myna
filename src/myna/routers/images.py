from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from myna.config import Settings, get_settings
from myna.generators import generate_image_stub
from myna.routers.utils import apply_scenario_or_error, parse_json_body

router = APIRouter(prefix="/v1", tags=["images"])


@router.post("/images/generations")
async def create_image(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    payload = await parse_json_body(request)
    _, early_response = await apply_scenario_or_error(request, settings)
    if early_response is not None:
        return early_response

    response_format = str(payload.get("response_format") or "url")
    requested_count = _to_positive_int(payload.get("n"), default=1)
    n = min(requested_count, 10)
    data = [generate_image_stub(response_format=response_format, index=index) for index in range(n)]
    return JSONResponse({"created": int(time.time()), "data": data})


def _to_positive_int(raw_value: object, default: int) -> int:
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return default
    if parsed <= 0:
        return default
    return parsed
