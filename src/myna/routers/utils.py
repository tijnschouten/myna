from __future__ import annotations

from typing import Any

from fastapi import Request
from starlette.responses import Response

from myna.config import Settings
from myna.scenarios import (
    ScenarioSpec,
    apply_delay_ms,
    error_response,
    resolve_error,
    timeout_delay_ms,
)


def get_scenario(request: Request) -> ScenarioSpec:
    scenario = getattr(request.state, "scenario_spec", None)
    if isinstance(scenario, ScenarioSpec):
        return scenario
    return ScenarioSpec()


async def apply_scenario_or_error(
    request: Request,
    settings: Settings,
) -> tuple[ScenarioSpec, Response | None]:
    scenario = get_scenario(request)
    error_key = resolve_error(scenario, settings.mock_chaos_rate)
    if error_key is not None:
        if error_key == "timeout":
            await apply_delay_ms(timeout_delay_ms(scenario))
        else:
            await apply_delay_ms(scenario.delay_ms)
        return scenario, error_response(error_key)

    await apply_delay_ms(scenario.delay_ms)
    return scenario, None


async def parse_json_body(request: Request) -> dict[str, Any]:
    try:
        payload = await request.json()
    except Exception:
        return {}

    if isinstance(payload, dict):
        return payload
    return {}
