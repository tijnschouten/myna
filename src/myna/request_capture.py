from __future__ import annotations

import base64
import json
from threading import Lock
from typing import Any

from starlette.datastructures import FormData, UploadFile
from starlette.requests import Request


def _request_from_body(scope: dict[str, Any], body: bytes) -> Request:
    sent = False

    async def receive() -> dict[str, Any]:
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive=receive)


async def build_request_record(request: Request, body: bytes) -> dict[str, Any]:
    headers = {key: value for key, value in request.headers.items()}
    content_type = request.headers.get("content-type", "")

    record: dict[str, Any] = {
        "method": request.method,
        "path": request.url.path,
        "query": {key: value for key, value in request.query_params.items()},
        "headers": headers,
        "content_type": content_type,
        "body_text": body.decode("utf-8", errors="replace"),
        "body_base64": base64.b64encode(body).decode("ascii"),
        "json": None,
        "form": {},
        "files": {},
    }

    probe = _request_from_body(request.scope, body)

    if "application/json" in content_type:
        try:
            record["json"] = await probe.json()
        except json.JSONDecodeError:
            record["json"] = None
    elif (
        "multipart/form-data" in content_type
        or "application/x-www-form-urlencoded" in content_type
    ):
        try:
            form: FormData = await probe.form()
            _extract_form_fields(record, form)
        except Exception:
            # Keep request capture best-effort to avoid breaking test traffic.
            pass

    return record


def _extract_form_fields(record: dict[str, Any], form: FormData) -> None:
    form_fields: dict[str, Any] = {}
    files: dict[str, Any] = {}

    for key, value in form.multi_items():
        if isinstance(value, UploadFile):
            file_entry = {
                "filename": value.filename,
                "content_type": value.content_type,
            }
            content = value.file.read()
            if isinstance(content, bytes):
                file_entry["size"] = len(content)
                file_entry["content_base64"] = base64.b64encode(content).decode("ascii")
                file_entry["content_text"] = content.decode("utf-8", errors="replace")
            _append_multi_value(files, key, file_entry)
            continue

        _append_multi_value(form_fields, key, value)

    record["form"] = form_fields
    record["files"] = files


def _append_multi_value(target: dict[str, Any], key: str, value: Any) -> None:
    if key not in target:
        target[key] = value
        return

    existing = target[key]
    if isinstance(existing, list):
        existing.append(value)
        return

    target[key] = [existing, value]


class RequestLog:
    def __init__(self) -> None:
        self._requests: list[dict[str, Any]] = []
        self._lock = Lock()

    def add(self, request_record: dict[str, Any]) -> None:
        with self._lock:
            self._requests.append(request_record)

    def all(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._requests)

    def last(self) -> dict[str, Any] | None:
        with self._lock:
            if not self._requests:
                return None
            return self._requests[-1]

    def clear(self) -> int:
        with self._lock:
            count = len(self._requests)
            self._requests.clear()
            return count


request_log = RequestLog()
