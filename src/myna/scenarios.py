from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from typing import Final

from fastapi.responses import JSONResponse

DEFAULT_TIMEOUT_DELAY_MS: Final[int] = 1000
VALID_ERRORS: Final[set[str]] = {"rate_limit", "auth", "context_length", "server", "timeout"}
CHAOS_ERRORS: Final[tuple[str, ...]] = ("rate_limit", "auth", "context_length", "server")


@dataclass(slots=True, frozen=True)
class MockError:
    status_code: int
    error_type: str
    message: str
    code: str | None = None


ERROR_DEFINITIONS: Final[dict[str, MockError]] = {
    "rate_limit": MockError(
        status_code=429,
        error_type="rate_limit_exceeded",
        message="Rate limit exceeded for mock request.",
        code="rate_limit_exceeded",
    ),
    "auth": MockError(
        status_code=401,
        error_type="invalid_api_key",
        message="Invalid API key provided.",
        code="invalid_api_key",
    ),
    "context_length": MockError(
        status_code=400,
        error_type="context_length_exceeded",
        message="Maximum context length exceeded.",
        code="context_length_exceeded",
    ),
    "server": MockError(
        status_code=500,
        error_type="server_error",
        message="The server had an error while processing your request.",
        code="server_error",
    ),
    "timeout": MockError(
        status_code=504,
        error_type="timeout",
        message="Upstream model request timed out.",
        code="gateway_timeout",
    ),
}


@dataclass(slots=True)
class ScenarioSpec:
    raw: str = ""
    delay_ms: int = 0
    stream_truncate: bool = False
    json_invalid: bool = False
    empty_choices: bool = False
    explicit_errors: list[str] = field(default_factory=list)
    chaos_rate: float | None = None

    @property
    def first_error(self) -> str | None:
        for error_key in self.explicit_errors:
            if error_key in VALID_ERRORS:
                return error_key
        return None


def parse_scenario(raw_scenario: str | None) -> ScenarioSpec:
    spec = ScenarioSpec(raw=(raw_scenario or "").strip())
    if not raw_scenario:
        return spec

    for directive in raw_scenario.split(","):
        token = directive.strip()
        if not token:
            continue

        if token.startswith("delay="):
            parsed_delay = _parse_non_negative_int(token.split("=", maxsplit=1)[1])
            if parsed_delay is not None:
                spec.delay_ms = parsed_delay
            continue

        if token.startswith("error="):
            error_key = token.split("=", maxsplit=1)[1].strip()
            if error_key in VALID_ERRORS:
                spec.explicit_errors.append(error_key)
            continue

        if token.startswith("chaos="):
            parsed_rate = _parse_rate(token.split("=", maxsplit=1)[1])
            if parsed_rate is not None:
                spec.chaos_rate = parsed_rate
            continue

        if token == "stream_truncate":
            spec.stream_truncate = True
            continue

        if token == "json_invalid":
            spec.json_invalid = True
            continue

        if token == "empty_choices":
            spec.empty_choices = True

    return spec


def resolve_error(spec: ScenarioSpec, global_chaos_rate: float) -> str | None:
    explicit_error = spec.first_error
    if explicit_error is not None:
        return explicit_error

    effective_chaos_rate = spec.chaos_rate if spec.chaos_rate is not None else global_chaos_rate
    if effective_chaos_rate <= 0:
        return None

    if random.random() < effective_chaos_rate:
        return random.choice(CHAOS_ERRORS)
    return None


def error_response(error_key: str) -> JSONResponse:
    error = ERROR_DEFINITIONS[error_key]
    payload = {
        "error": {
            "message": error.message,
            "type": error.error_type,
            "param": None,
            "code": error.code,
        }
    }
    return JSONResponse(status_code=error.status_code, content=payload)


async def apply_delay_ms(delay_ms: int) -> None:
    if delay_ms > 0:
        await asyncio.sleep(delay_ms / 1000)


def timeout_delay_ms(spec: ScenarioSpec) -> int:
    return spec.delay_ms if spec.delay_ms > 0 else DEFAULT_TIMEOUT_DELAY_MS


def _parse_non_negative_int(value: str) -> int | None:
    try:
        parsed = int(value)
    except ValueError:
        return None
    if parsed < 0:
        return None
    return parsed


def _parse_rate(value: str) -> float | None:
    try:
        parsed = float(value)
    except ValueError:
        return None
    if not 0 <= parsed <= 1:
        return None
    return parsed
