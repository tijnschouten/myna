from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from myna.config import get_settings
from myna.main import create_app


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client_factory():
    def _factory() -> TestClient:
        get_settings.cache_clear()
        return TestClient(create_app())

    return _factory


@pytest.fixture
def client(client_factory: Callable[[], TestClient]):
    with client_factory() as test_client:
        yield test_client
