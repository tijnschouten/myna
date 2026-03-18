from __future__ import annotations


def test_embeddings_respect_configured_dims(client_factory, monkeypatch):
    monkeypatch.setenv("MOCK_EMBEDDING_DIMS", "8")
    with client_factory() as client:
        response = client.post("/v1/embeddings", json={"input": ["hello", "world"]})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"]) == 2
    assert len(payload["data"][0]["embedding"]) == 8
    assert len(payload["data"][1]["embedding"]) == 8


def test_images_generations_support_url_and_b64(client):
    response_url = client.post("/v1/images/generations", json={"prompt": "cat", "n": 2})
    assert response_url.status_code == 200
    payload_url = response_url.json()
    assert "url" in payload_url["data"][0]
    assert len(payload_url["data"]) == 2

    response_b64 = client.post(
        "/v1/images/generations",
        json={"prompt": "cat", "response_format": "b64_json"},
    )
    assert response_b64.status_code == 200
    payload_b64 = response_b64.json()
    assert "b64_json" in payload_b64["data"][0]


def test_audio_speech_supports_wav_and_mp3(client):
    wav_response = client.post(
        "/v1/audio/speech",
        json={"model": "gpt-4o-mini-tts", "input": "hello", "response_format": "wav"},
    )
    assert wav_response.status_code == 200
    assert wav_response.headers["content-type"].startswith("audio/wav")
    assert wav_response.content.startswith(b"RIFF")

    mp3_response = client.post(
        "/v1/audio/speech",
        json={"model": "gpt-4o-mini-tts", "input": "hello"},
    )
    assert mp3_response.status_code == 200
    assert mp3_response.headers["content-type"].startswith("audio/mpeg")
    assert mp3_response.content.startswith(b"ID3")


def test_audio_transcription_and_translation(client):
    files = {"file": ("sample.wav", b"\x00\x00\x00\x00", "audio/wav")}
    transcribe_response = client.post(
        "/v1/audio/transcriptions",
        files=files,
        data={"model": "whisper-1"},
    )
    assert transcribe_response.status_code == 200
    assert transcribe_response.json()["text"] == "This is a mock transcription."

    translate_response = client.post(
        "/v1/audio/translations",
        files=files,
        data={"model": "whisper-1"},
    )
    assert translate_response.status_code == 200
    assert translate_response.json()["text"] == "This is a mock English translation."


def test_auth_toggle(client_factory, monkeypatch):
    monkeypatch.setenv("MOCK_REQUIRE_AUTH", "true")
    with client_factory() as client:
        unauthenticated = client.get("/v1/models")
        authenticated = client.get("/v1/models", headers={"Authorization": "Bearer test-token"})

    assert unauthenticated.status_code == 401
    assert unauthenticated.json()["error"]["type"] == "invalid_api_key"
    assert authenticated.status_code == 200
