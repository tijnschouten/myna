from __future__ import annotations

import json

import pytest


def test_json_mode_uses_structured_tool_schema(client):
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o",
            "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": "Return structured json"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "make_user",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "age": {"type": "integer"},
                                "score": {"type": "number"},
                                "active": {"type": "boolean"},
                                "tags": {"type": "array", "items": {"type": "string"}},
                            },
                        },
                    },
                }
            ],
        },
    )

    assert response.status_code == 200
    content = response.json()["choices"][0]["message"]["content"]
    body = json.loads(content)
    assert isinstance(body["name"], str)
    assert isinstance(body["age"], int)
    assert isinstance(body["score"], float)
    assert isinstance(body["active"], bool)
    assert isinstance(body["tags"], list)


def test_json_mode_uses_response_json_schema(client):
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o",
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "city_schema",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "city": {"type": "string", "enum": ["Amsterdam", "Utrecht"]},
                            "count": {"type": "integer"},
                        },
                    },
                },
            },
            "messages": [{"role": "user", "content": "Return structured json"}],
        },
    )

    assert response.status_code == 200
    content = response.json()["choices"][0]["message"]["content"]
    body = json.loads(content)
    assert body["city"] == "Amsterdam"
    assert body["count"] == 42


def test_json_mode_without_schema_returns_default_object(client):
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o",
            "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": "Return json"}],
        },
    )

    assert response.status_code == 200
    content = response.json()["choices"][0]["message"]["content"]
    body = json.loads(content)
    assert body == {"message": "lorem ipsum"}


def test_json_invalid_scenario_breaks_json(client):
    response = client.post(
        "/v1/chat/completions",
        headers={"X-Mock-Scenario": "json_invalid"},
        json={
            "model": "gpt-4o",
            "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": "Return json"}],
        },
    )

    assert response.status_code == 200
    content = response.json()["choices"][0]["message"]["content"]
    with pytest.raises(json.JSONDecodeError):
        json.loads(content)
