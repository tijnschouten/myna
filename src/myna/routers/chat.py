from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse

from myna.config import Settings, get_settings
from myna.generators import (
    extract_structured_json_schema,
    generate_chat_text,
    generate_json_object,
    is_json_mode,
    split_stream_chunks,
)
from myna.routers.utils import apply_scenario_or_error, parse_json_body

router = APIRouter(prefix="/v1", tags=["chat"])


@router.post("/chat/completions")
async def chat_completions(
    request: Request,
    settings: Settings = Depends(get_settings),
):
    payload = await parse_json_body(request)
    scenario, early_response = await apply_scenario_or_error(request, settings)
    if early_response is not None:
        return early_response

    model = str(payload.get("model") or settings.mock_default_model)
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created = int(time.time())
    content = _render_chat_content(payload, scenario.json_invalid)

    if payload.get("stream") is True:
        stream = _chat_stream(
            completion_id=completion_id,
            created=created,
            model=model,
            content=content,
            chunk_delay_seconds=settings.chunk_delay_seconds,
            stream_truncate=scenario.stream_truncate,
            empty_choices=scenario.empty_choices,
        )
        return StreamingResponse(stream, media_type="text/event-stream")

    usage = _usage(
        prompt_text=json.dumps(payload.get("messages", []), ensure_ascii=True),
        completion_text=content if not scenario.empty_choices else "",
    )
    choices: list[dict[str, Any]]
    if scenario.empty_choices:
        choices = []
    else:
        choices = [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ]

    response_payload = {
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": choices,
        "usage": usage,
    }
    return JSONResponse(response_payload)


@router.post("/completions")
async def completions(
    request: Request,
    settings: Settings = Depends(get_settings),
):
    payload = await parse_json_body(request)
    scenario, early_response = await apply_scenario_or_error(request, settings)
    if early_response is not None:
        return early_response

    model = str(payload.get("model") or settings.mock_default_model)
    completion_id = f"cmpl-{uuid.uuid4().hex[:12]}"
    created = int(time.time())
    text = generate_chat_text(prompt=payload.get("prompt"))

    if payload.get("stream") is True:
        stream = _completion_stream(
            completion_id=completion_id,
            created=created,
            model=model,
            text=text,
            chunk_delay_seconds=settings.chunk_delay_seconds,
            stream_truncate=scenario.stream_truncate,
            empty_choices=scenario.empty_choices,
        )
        return StreamingResponse(stream, media_type="text/event-stream")

    usage = _usage(prompt_text=str(payload.get("prompt", "")), completion_text=text)
    choices: list[dict[str, Any]]
    if scenario.empty_choices:
        choices = []
    else:
        choices = [
            {
                "index": 0,
                "text": text,
                "finish_reason": "stop",
                "logprobs": None,
            }
        ]

    response_payload = {
        "id": completion_id,
        "object": "text_completion",
        "created": created,
        "model": model,
        "choices": choices,
        "usage": usage,
    }
    return JSONResponse(response_payload)


def _render_chat_content(payload: dict[str, Any], force_invalid_json: bool) -> str:
    if is_json_mode(payload):
        if force_invalid_json:
            return '{"malformed_json": true'
        schema = extract_structured_json_schema(payload)
        generated = generate_json_object(schema)
        return json.dumps(generated, ensure_ascii=True)
    return generate_chat_text(messages=payload.get("messages"))


def _usage(prompt_text: str, completion_text: str) -> dict[str, int]:
    prompt_tokens = _rough_token_count(prompt_text)
    completion_tokens = _rough_token_count(completion_text)
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }


def _rough_token_count(text: str) -> int:
    stripped = text.strip()
    if not stripped:
        return 0
    return max(1, len(stripped.split()))


def _to_sse(data: dict[str, Any] | str) -> str:
    if isinstance(data, str):
        return f"data: {data}\n\n"
    encoded = json.dumps(data, ensure_ascii=True, separators=(",", ":"))
    return f"data: {encoded}\n\n"


async def _chat_stream(
    *,
    completion_id: str,
    created: int,
    model: str,
    content: str,
    chunk_delay_seconds: float,
    stream_truncate: bool,
    empty_choices: bool,
):
    if empty_choices:
        yield _to_sse(
            {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [],
            }
        )
        if not stream_truncate:
            yield _to_sse("[DONE]")
        return

    yield _to_sse(
        {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
        }
    )

    for emitted_content_chunks, chunk in enumerate(split_stream_chunks(content), start=1):
        yield _to_sse(
            {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{"index": 0, "delta": {"content": chunk}, "finish_reason": None}],
            }
        )
        if stream_truncate and emitted_content_chunks >= 3:
            return
        await asyncio.sleep(chunk_delay_seconds)

    yield _to_sse(
        {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
    )
    yield _to_sse("[DONE]")


async def _completion_stream(
    *,
    completion_id: str,
    created: int,
    model: str,
    text: str,
    chunk_delay_seconds: float,
    stream_truncate: bool,
    empty_choices: bool,
):
    if empty_choices:
        yield _to_sse(
            {
                "id": completion_id,
                "object": "text_completion",
                "created": created,
                "model": model,
                "choices": [],
            }
        )
        if not stream_truncate:
            yield _to_sse("[DONE]")
        return

    for emitted_content_chunks, chunk in enumerate(split_stream_chunks(text), start=1):
        yield _to_sse(
            {
                "id": completion_id,
                "object": "text_completion",
                "created": created,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "text": chunk,
                        "logprobs": None,
                        "finish_reason": None,
                    }
                ],
            }
        )
        if stream_truncate and emitted_content_chunks >= 3:
            return
        await asyncio.sleep(chunk_delay_seconds)

    yield _to_sse(
        {
            "id": completion_id,
            "object": "text_completion",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "text": "",
                    "logprobs": None,
                    "finish_reason": "stop",
                }
            ],
        }
    )
    yield _to_sse("[DONE]")
