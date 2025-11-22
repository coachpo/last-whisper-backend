from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import reset_rate_limiter_state


def test_missing_api_key_is_rejected(test_client: TestClient):
    api_header = settings.api_key_header_name
    token = test_client.headers.pop(api_header, None)

    response = test_client.get("/v1/items")

    assert response.status_code == 401

    if token:
        test_client.headers[api_header] = token


def test_rate_limit_blocks_excess_requests(test_client: TestClient):
    prev_limit = settings.api_rate_limit_per_minute
    prev_window = settings.api_rate_limit_window_seconds
    settings.api_rate_limit_per_minute = 1
    settings.api_rate_limit_window_seconds = 60
    reset_rate_limiter_state()

    try:
        first = test_client.get("/v1/items")
        assert first.status_code == 200

        second = test_client.get("/v1/items")
        assert second.status_code == 429
    finally:
        settings.api_rate_limit_per_minute = prev_limit
        settings.api_rate_limit_window_seconds = prev_window
        reset_rate_limiter_state()
