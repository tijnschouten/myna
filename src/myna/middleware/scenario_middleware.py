from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from myna.scenarios import parse_scenario


class ScenarioMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        header_value = request.headers.get("X-Mock-Scenario")
        query_value = request.query_params.get("scenario")
        raw_scenario = header_value if header_value is not None else query_value
        request.state.scenario_spec = parse_scenario(raw_scenario)
        return await call_next(request)
