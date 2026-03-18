from __future__ import annotations

import pytest

from myna import scenarios


@pytest.mark.parametrize(
    ("scenario_value", "status_code", "error_type"),
    [
        ("error=rate_limit", 429, "rate_limit_exceeded"),
        ("error=auth", 401, "invalid_api_key"),
        ("error=context_length", 400, "context_length_exceeded"),
        ("error=server", 500, "server_error"),
        ("error=timeout,delay=1", 504, "timeout"),
    ],
)
def test_explicit_error_scenarios(client, scenario_value, status_code, error_type):
    response = client.post(
        "/v1/chat/completions",
        headers={"X-Mock-Scenario": scenario_value},
        json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
    )

    assert response.status_code == status_code
    payload = response.json()
    assert payload["error"]["type"] == error_type


def test_header_scenario_precedence_over_query(client):
    response = client.post(
        "/v1/chat/completions?scenario=error=server",
        headers={"X-Mock-Scenario": "error=auth"},
        json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
    )

    assert response.status_code == 401
    assert response.json()["error"]["type"] == "invalid_api_key"


def test_request_chaos_override(client, monkeypatch):
    monkeypatch.setattr(scenarios.random, "random", lambda: 0.0)
    monkeypatch.setattr(scenarios.random, "choice", lambda _: "server")

    response = client.post(
        "/v1/chat/completions",
        headers={"X-Mock-Scenario": "chaos=1"},
        json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
    )

    assert response.status_code == 500
    assert response.json()["error"]["type"] == "server_error"


def test_global_chaos_rate(client_factory, monkeypatch):
    monkeypatch.setenv("MOCK_CHAOS_RATE", "1")
    monkeypatch.setattr(scenarios.random, "random", lambda: 0.0)
    monkeypatch.setattr(scenarios.random, "choice", lambda _: "rate_limit")

    with client_factory() as client:
        response = client.post(
            "/v1/chat/completions",
            json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
        )

    assert response.status_code == 429
    assert response.json()["error"]["type"] == "rate_limit_exceeded"


def test_first_explicit_error_wins(client):
    response = client.post(
        "/v1/chat/completions",
        headers={"X-Mock-Scenario": "error=server,error=auth"},
        json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
    )

    assert response.status_code == 500
    assert response.json()["error"]["type"] == "server_error"
