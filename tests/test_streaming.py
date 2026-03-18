from __future__ import annotations

import json


def test_chat_streaming_includes_done(client):
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o",
            "stream": True,
            "messages": [{"role": "user", "content": "hello streaming world"}],
        },
    )

    assert response.status_code == 200
    data_lines = _extract_data_lines(response.text)
    assert data_lines[-1] == "[DONE]"

    first_chunk = json.loads(data_lines[0])
    assert first_chunk["object"] == "chat.completion.chunk"
    assert first_chunk["choices"][0]["delta"]["role"] == "assistant"


def test_chat_stream_truncate_omits_done(client):
    response = client.post(
        "/v1/chat/completions",
        headers={"X-Mock-Scenario": "stream_truncate"},
        json={
            "model": "gpt-4o",
            "stream": True,
            "messages": [{"role": "user", "content": "truncate this stream please"}],
        },
    )

    assert response.status_code == 200
    data_lines = _extract_data_lines(response.text)
    assert data_lines[-1] != "[DONE]"
    assert len(data_lines) >= 4


def _extract_data_lines(stream_text: str) -> list[str]:
    result: list[str] = []
    for line in stream_text.splitlines():
        if line.startswith("data: "):
            result.append(line.removeprefix("data: "))
    return result
