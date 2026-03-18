from __future__ import annotations

import base64

import httpx

from myna.pytest_plugin import MynaFixture


def test_myna_fixture_helpers():
    fixture = MynaFixture(base_url="http://127.0.0.1:9999/v1", default_scenario="error=rate_limit")
    assert fixture.url("/chat/completions") == "http://127.0.0.1:9999/v1/chat/completions"
    assert fixture.headers() == {"X-Mock-Scenario": "error=rate_limit"}
    assert fixture.path_with_scenario("/audio/transcriptions").endswith(
        "scenario=error%3Drate_limit"
    )
    assert fixture.url_with_scenario("/models").endswith("scenario=error%3Drate_limit")
    assert fixture.headers("delay=500,error=server") == {
        "X-Mock-Scenario": "delay=500,error=server"
    }


def test_myna_capture_api(myna: MynaFixture):
    response = httpx.post(
        myna.url("/audio/transcriptions"),
        files={"file": ("sample.wav", b"abc", "audio/wav")},
        data={"model": "whisper-mock", "language": "nl"},
        timeout=2,
    )
    assert response.status_code == 200

    req = myna.last_request
    assert req is not None
    assert req.method == "POST"
    assert req.path == "/v1/audio/transcriptions"
    assert req.form["model"] == "whisper-mock"
    assert req.form["language"] == "nl"

    uploaded_file = req.files["file"]
    assert uploaded_file["content_type"] == "audio/wav"
    assert base64.b64decode(uploaded_file["content_base64"]) == b"abc"

    all_requests = myna.requests
    assert len(all_requests) == 1

    assert myna.clear_requests() == 1
    assert myna.last_request is None
    assert myna.clear_seeded_responses() == 0


def test_myna_url_fixture(myna: MynaFixture, myna_url: str):
    assert myna_url == myna.base_url
