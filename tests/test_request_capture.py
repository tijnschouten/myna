from __future__ import annotations


def test_request_capture_json_payload(client):
    client.delete("/__myna/requests")

    response = client.post(
        "/v1/chat/completions",
        json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hello"}]},
    )
    assert response.status_code == 200

    captured = client.get("/__myna/requests/last")
    assert captured.status_code == 200
    payload = captured.json()["request"]

    assert payload["method"] == "POST"
    assert payload["path"] == "/v1/chat/completions"
    assert payload["json"]["model"] == "gpt-4o"
    assert payload["headers"]["content-type"].startswith("application/json")


def test_request_capture_multipart_payload(client):
    client.delete("/__myna/requests")

    response = client.post(
        "/v1/audio/transcriptions",
        files={"file": ("sample.wav", b"abc", "audio/wav")},
        data={"model": "whisper-1", "language": "nl"},
    )
    assert response.status_code == 200

    captured = client.get("/__myna/requests/last")
    payload = captured.json()["request"]

    assert payload["form"]["model"] == "whisper-1"
    assert payload["form"]["language"] == "nl"
    assert payload["files"]["file"]["filename"] == "sample.wav"
    assert payload["files"]["file"]["content_type"] == "audio/wav"


def test_capture_endpoints_are_not_captured(client):
    client.delete("/__myna/requests")

    response = client.get("/__myna/requests")
    assert response.status_code == 200
    assert response.json()["requests"] == []
