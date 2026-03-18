from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from fastapi.responses import JSONResponse
from starlette.responses import Response


@dataclass(slots=True)
class SeededResponse:
    method: str
    path: str
    status_code: int
    headers: dict[str, str] = field(default_factory=dict)
    json_body: Any | None = None
    body_text: str | None = None

    def build_response(self) -> Response:
        if self.json_body is not None:
            return JSONResponse(
                status_code=self.status_code,
                content=self.json_body,
                headers=self.headers,
            )

        return Response(
            content=(self.body_text or ""),
            status_code=self.status_code,
            headers=self.headers,
        )


class SeededResponseQueue:
    def __init__(self) -> None:
        self._items: list[SeededResponse] = []
        self._lock = Lock()

    def add(self, seeded: SeededResponse) -> None:
        with self._lock:
            self._items.append(seeded)

    def consume(self, method: str, path: str) -> SeededResponse | None:
        match_method = method.upper()
        with self._lock:
            for index, item in enumerate(self._items):
                if item.method == match_method and item.path == path:
                    return self._items.pop(index)
        return None

    def clear(self) -> int:
        with self._lock:
            count = len(self._items)
            self._items.clear()
            return count


seeded_response_queue = SeededResponseQueue()
