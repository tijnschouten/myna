from __future__ import annotations

import httpx

from myna.pytest_plugin import MynaFixture


def test_next_response_overrides_once(myna: MynaFixture):
    seeded_payload = {
        "id": "chatcmpl-seeded",
        "object": "chat.completion",
        "created": 0,
        "model": "mock-chat-v1",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": ""}}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }
    myna.next_response(seeded_payload, path="/chat/completions")

    first = httpx.post(
        myna.url("/chat/completions"),
        json={"model": "mock-chat-v1", "messages": [{"role": "user", "content": "hello"}]},
        timeout=2,
    )
    assert first.status_code == 200
    assert first.json() == seeded_payload

    second = httpx.post(
        myna.url("/chat/completions"),
        json={"model": "mock-chat-v1", "messages": [{"role": "user", "content": "hello"}]},
        timeout=2,
    )
    assert second.status_code == 200
    assert second.json()["id"] != "chatcmpl-seeded"


def test_next_response_can_seed_malformed_shape(myna: MynaFixture):
    myna.next_response({"choices": [{"message": {"content": None}}]})

    response = httpx.post(
        myna.url("/chat/completions"),
        json={"model": "mock-chat-v1", "messages": [{"role": "user", "content": "hello"}]},
        timeout=2,
    )
    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] is None


def test_next_response_accepts_full_path_for_compat(myna: MynaFixture):
    myna.next_response({"compat": True}, path="/v1/chat/completions")

    response = httpx.post(
        myna.url("/chat/completions"),
        json={"model": "mock-chat-v1", "messages": [{"role": "user", "content": "hello"}]},
        timeout=2,
    )
    assert response.status_code == 200
    assert response.json()["compat"] is True
