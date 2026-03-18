from __future__ import annotations

import hashlib
import io
import random
import wave
from collections.abc import Mapping, Sequence
from typing import Any

MOCK_IMAGE_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
)


def generate_chat_text(
    messages: Sequence[Mapping[str, Any]] | None = None,
    prompt: Any = None,
) -> str:
    if prompt is not None:
        source = _flatten_value(prompt).strip()
    else:
        source = _last_user_message(messages).strip()

    if not source:
        return "Mock response."
    return f"Mock response to: {source[:200]}"


def split_stream_chunks(text: str) -> list[str]:
    words = text.split()
    if not words:
        return ["Mock"]

    chunks: list[str] = [words[0]]
    chunks.extend(f" {word}" for word in words[1:])
    return chunks


def is_json_mode(payload: Mapping[str, Any]) -> bool:
    response_format = payload.get("response_format")
    if not isinstance(response_format, Mapping):
        return False

    response_type = response_format.get("type")
    return response_type in {"json_object", "json_schema"}


def extract_structured_json_schema(payload: Mapping[str, Any]) -> dict[str, Any] | None:
    response_format = payload.get("response_format")
    if isinstance(response_format, Mapping):
        response_type = response_format.get("type")
        if response_type == "json_schema":
            json_schema_config = response_format.get("json_schema")
            if isinstance(json_schema_config, Mapping):
                schema = json_schema_config.get("schema")
                if isinstance(schema, Mapping):
                    return dict(schema)

        json_schema_config = response_format.get("json_schema")
        if isinstance(json_schema_config, Mapping):
            schema = json_schema_config.get("schema")
            if isinstance(schema, Mapping):
                return dict(schema)

    tools = payload.get("tools")
    if isinstance(tools, list):
        for tool in tools:
            if not isinstance(tool, Mapping):
                continue
            function_config = tool.get("function")
            if not isinstance(function_config, Mapping):
                continue
            parameters = function_config.get("parameters")
            if isinstance(parameters, Mapping):
                return dict(parameters)

    return None


def generate_json_object(schema: Mapping[str, Any] | None) -> dict[str, Any]:
    if schema is None:
        return {"message": "lorem ipsum"}

    value = _generate_from_schema(schema, depth=0)
    if isinstance(value, dict):
        return value
    return {"value": value}


def generate_embedding_vector(source: Any, dims: int) -> list[float]:
    text = _flatten_value(source)
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    seed = int.from_bytes(digest[:8], byteorder="big", signed=False)
    rng = random.Random(seed)
    return [round(rng.uniform(-1.0, 1.0), 6) for _ in range(dims)]


def generate_image_stub(response_format: str, index: int) -> dict[str, str]:
    if response_format == "b64_json":
        return {"b64_json": MOCK_IMAGE_BASE64}
    return {"url": f"https://example.com/mock-image-{index + 1}.png"}


def generate_wav_stub(duration_ms: int = 300) -> bytes:
    sample_rate = 16000
    sample_count = int(sample_rate * (duration_ms / 1000))
    frames = b"\x00\x00" * sample_count

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(frames)
    return buffer.getvalue()


def generate_mp3_stub() -> bytes:
    # This is a tiny deterministic byte payload suitable for API contract tests.
    return b"ID3\x03\x00\x00\x00\x00\x00\x15TIT2\x00\x00\x00\x05\x00\x00Mock"


def generate_transcription_text() -> str:
    return "This is a mock transcription."


def generate_translation_text() -> str:
    return "This is a mock English translation."


def _last_user_message(messages: Sequence[Mapping[str, Any]] | None) -> str:
    if not messages:
        return ""

    for message in reversed(messages):
        if message.get("role") != "user":
            continue
        return _flatten_value(message.get("content"))
    return ""


def _flatten_value(value: Any) -> str:
    if isinstance(value, str):
        return value

    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, Mapping):
                text = item.get("text") or item.get("input_text")
                if isinstance(text, str):
                    parts.append(text)
        return " ".join(parts).strip()

    if value is None:
        return ""
    return str(value)


def _generate_from_schema(schema: Mapping[str, Any], depth: int) -> Any:
    if depth > 5:
        return "lorem ipsum"

    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and enum_values:
        return enum_values[0]

    if "default" in schema:
        return schema["default"]

    schema_type = _normalize_schema_type(schema.get("type"))

    if schema_type is None:
        for key in ("anyOf", "oneOf", "allOf"):
            variants = schema.get(key)
            if isinstance(variants, list) and variants:
                first = variants[0]
                if isinstance(first, Mapping):
                    return _generate_from_schema(first, depth + 1)

        properties = schema.get("properties")
        if isinstance(properties, Mapping):
            schema_type = "object"

    if schema_type == "string":
        return "lorem ipsum"
    if schema_type == "integer":
        return 42
    if schema_type == "number":
        return 3.14
    if schema_type == "boolean":
        return True
    if schema_type == "array":
        items_schema = schema.get("items")
        if isinstance(items_schema, Mapping):
            return [
                _generate_from_schema(items_schema, depth + 1),
                _generate_from_schema(items_schema, depth + 1),
            ]
        return ["item_1", "item_2"]
    if schema_type == "object":
        properties = schema.get("properties")
        if not isinstance(properties, Mapping):
            return {"key": "lorem ipsum"}
        result: dict[str, Any] = {}
        for key, property_schema in properties.items():
            if isinstance(property_schema, Mapping):
                result[str(key)] = _generate_from_schema(property_schema, depth + 1)
            else:
                result[str(key)] = "lorem ipsum"
        return result

    return "lorem ipsum"


def _normalize_schema_type(schema_type: Any) -> str | None:
    if isinstance(schema_type, str):
        return schema_type
    if isinstance(schema_type, list):
        for entry in schema_type:
            if isinstance(entry, str) and entry != "null":
                return entry
    return None
