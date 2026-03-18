from __future__ import annotations

from myna.pytest_plugin import MynaFixture


def test_myna_fixture_helpers():
    fixture = MynaFixture(base_url="http://127.0.0.1:9999/v1", default_scenario="error=rate_limit")
    assert fixture.url("/chat/completions") == "http://127.0.0.1:9999/v1/chat/completions"
    assert fixture.headers() == {"X-Mock-Scenario": "error=rate_limit"}
    assert fixture.url_with_scenario("/models").endswith("scenario=error%3Drate_limit")
    assert fixture.headers("delay=500,error=server") == {
        "X-Mock-Scenario": "delay=500,error=server"
    }
