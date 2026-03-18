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

    def url_with_scenario(self, path: str, scenario: str | None = None) -> str:
        scenario_value = scenario if scenario is not None else self.default_scenario
        target = self.url(path)
        if not scenario_value:
            return target
        separator = "&" if "?" in target else "?"
        return f"{target}{separator}scenario={quote(scenario_value)}"

    def headers(self, scenario: str | None = None) -> dict[str, str]:
        scenario_value = scenario if scenario is not None else self.default_scenario
        if not scenario_value:
            return {}
        return {"X-Mock-Scenario": scenario_value}


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
    return MynaFixture(base_url=myna_base_url, default_scenario=myna_scenario)
