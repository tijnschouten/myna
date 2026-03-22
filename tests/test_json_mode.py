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


def test_json_mode_respects_string_formats(client):
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o",
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "formatted_strings",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "birth_date": {"type": "string", "format": "date"},
                            "created_at": {"type": "string", "format": "date-time"},
                            "email": {"type": "string", "format": "email"},
                            "homepage": {"type": "string", "format": "uri"},
                            "avatar": {"type": "string", "format": "url"},
                            "id": {"type": "string", "format": "uuid"},
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
    assert body == {
        "birth_date": "2026-01-01",
        "created_at": "2026-01-01T00:00:00",
        "email": "mock@example.com",
        "homepage": "https://example.com",
        "avatar": "https://example.com",
        "id": "00000000-0000-0000-0000-000000000000",
    }


@pytest.mark.parametrize("key", ["anyOf", "oneOf"])
def test_json_mode_prefers_non_null_variant(client, key):
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o",
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "nullable_field",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "value": {
                                key: [
                                    {"type": "null"},
                                    {"type": "integer"},
                                ]
                            }
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
    assert body["value"] == 42


def test_json_mode_generates_additional_properties_values(client):
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o",
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "dict_of_arrays",
                    "schema": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "array",
                            "items": {"type": "integer"},
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
    assert body == {
        "mock_key_1": [42, 42],
        "mock_key_2": [42, 42],
    }


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
