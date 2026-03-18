from __future__ import annotations


def test_models_happy_path(client):
    response = client.get("/v1/models")
    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "list"
    assert any(model["id"] == "mock-chat-v1" for model in payload["data"])
    assert all(model["owned_by"] == "myna" for model in payload["data"])


def test_chat_completion_happy_path(client):
    response = client.post(
        "/v1/chat/completions",
        json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hello world"}]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "chat.completion"
    assert payload["choices"][0]["message"]["role"] == "assistant"
    assert "Mock response to: hello world" in payload["choices"][0]["message"]["content"]


def test_legacy_completion_happy_path(client):
    response = client.post(
        "/v1/completions",
        json={"model": "gpt-4o", "prompt": "write a line"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "text_completion"
    assert payload["choices"][0]["finish_reason"] == "stop"
    assert "Mock response to: write a line" in payload["choices"][0]["text"]


def test_empty_choices_scenario(client):
    response = client.post(
        "/v1/chat/completions",
        headers={"X-Mock-Scenario": "empty_choices"},
        json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hello"}]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["choices"] == []
