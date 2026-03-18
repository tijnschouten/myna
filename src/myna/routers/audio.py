from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, Response

from myna.config import Settings, get_settings
from myna.generators import (
    generate_mp3_stub,
    generate_transcription_text,
    generate_translation_text,
    generate_wav_stub,
)
from myna.routers.utils import apply_scenario_or_error, parse_json_body

router = APIRouter(prefix="/v1", tags=["audio"])


@router.post("/audio/speech")
async def create_speech(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> Response:
    payload = await parse_json_body(request)
    _, early_response = await apply_scenario_or_error(request, settings)
    if early_response is not None:
        return early_response

    response_format = str(payload.get("response_format") or "mp3").lower()
    if response_format == "wav":
        return Response(content=generate_wav_stub(), media_type="audio/wav")
    return Response(content=generate_mp3_stub(), media_type="audio/mpeg")


@router.post("/audio/transcriptions")
async def create_transcription(
    request: Request,
    file: UploadFile | None = File(default=None),
    model: str = Form(default="mock-asr-v1"),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    _, early_response = await apply_scenario_or_error(request, settings)
    if early_response is not None:
        return early_response

    if file is not None:
        await file.read()
    _ = model
    return JSONResponse({"text": generate_transcription_text()})


@router.post("/audio/translations")
async def create_translation(
    request: Request,
    file: UploadFile | None = File(default=None),
    model: str = Form(default="mock-asr-v1"),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    _, early_response = await apply_scenario_or_error(request, settings)
    if early_response is not None:
        return early_response

    if file is not None:
        await file.read()
    _ = model
    return JSONResponse({"text": generate_translation_text()})
