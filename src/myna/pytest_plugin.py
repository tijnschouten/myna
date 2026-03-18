from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass
from urllib.parse import quote

import httpx
import pytest


@dataclass(slots=True)
class CapturedRequest:
    method: str
    path: str
    query: dict[str, str]
    headers: dict[str, str]
    content_type: str
    body_text: str
    body_base64: str
    json: object | None
    form: dict[str, object]
    files: dict[str, object]



def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@dataclass(slots=True)
class MynaFixture:
    base_url: str
    default_scenario: str | None = None

    def url(self, path: str) -> str:
        normalized_path = path if path.startswith("/") else f"/{path}"
        return f"{self.base_url}{normalized_path}"

    def path_with_scenario(self, path: str, scenario: str | None = None) -> str:
        scenario_value = scenario if scenario is not None else self.default_scenario
        normalized_path = path if path.startswith("/") else f"/{path}"
        if not scenario_value:
            return normalized_path
        separator = "&" if "?" in normalized_path else "?"
        return f"{normalized_path}{separator}scenario={quote(scenario_value)}"

    def url_with_scenario(self, path: str, scenario: str | None = None) -> str:
        return f"{self.base_url}{self.path_with_scenario(path, scenario)}"

    def headers(self, scenario: str | None = None) -> dict[str, str]:
        scenario_value = scenario if scenario is not None else self.default_scenario
        if not scenario_value:
            return {}
        return {"X-Mock-Scenario": scenario_value}

    @property
    def requests(self) -> list[CapturedRequest]:
        response = httpx.get(f"{self._root_url}/__myna/requests", timeout=2)
        response.raise_for_status()
        records = response.json().get("requests", [])
        return [CapturedRequest(**record) for record in records]

    @property
    def last_request(self) -> CapturedRequest | None:
        response = httpx.get(f"{self._root_url}/__myna/requests/last", timeout=2)
        response.raise_for_status()
        payload = response.json().get("request")
        if payload is None:
            return None
        return CapturedRequest(**payload)

    def clear_requests(self) -> int:
        response = httpx.delete(f"{self._root_url}/__myna/requests", timeout=2)
        response.raise_for_status()
        return int(response.json().get("cleared", 0))

    @property
    def _root_url(self) -> str:
        return self.base_url.removesuffix("/v1")


@pytest.fixture(scope="session")
def myna_base_url() -> Iterator[str]:
    port = _free_port()
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH")
    if pythonpath:
        env["PYTHONPATH"] = f"src:{pythonpath}"
    else:
        env["PYTHONPATH"] = "src"

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "myna.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        env=env,
    )

    health_url = f"http://127.0.0.1:{port}/healthz"
    base_url = f"http://127.0.0.1:{port}/v1"

    for _ in range(50):
        try:
            if httpx.get(health_url, timeout=0.2).status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.1)
    else:
        proc.terminate()
        raise RuntimeError("Myna fixture could not start server in time.")

    try:
        yield base_url
    finally:
        proc.terminate()
        proc.wait(timeout=5)


@pytest.fixture
def myna_scenario(request: pytest.FixtureRequest) -> str | None:
    # Supports: @pytest.mark.parametrize("myna_scenario", ["error=rate_limit"], indirect=True)
    return getattr(request, "param", None)


@pytest.fixture
def myna(myna_base_url: str, myna_scenario: str | None) -> MynaFixture:
    fixture = MynaFixture(base_url=myna_base_url, default_scenario=myna_scenario)
    fixture.clear_requests()
    return fixture


@pytest.fixture
def myna_url(myna: MynaFixture) -> str:
    return myna.base_url
