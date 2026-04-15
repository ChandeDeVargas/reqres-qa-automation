"""
tests/test_smoke.py
───────────────────
Day 1 — Smoke tests.

Purpose: verify the project setup is correct end-to-end.
  - settings load from .env without errors
  - the API client can reach ReqRes
  - status codes, response time, and schema validation all work

These tests run fast and serve as a confidence check before
writing the full CRUD suite starting from Day 2.
"""
import pytest

from utils.assertions import assert_status, assert_response_time, assert_schema
from models.user import UserListResponse

@pytest.mark.smoke
class TestSmoke:
    """Basic connectivity and setup validation"""

    def test_api_is_reachable(self, client):
        """Get /users returns 200 (if auth key provided) or 401 (no key) - confirms API is reachable"""
        response = client.get("/users")
        from config import settings
        expected_status = 200 if settings.API_KEY else 401
        assert_status(response, expected_status)

    def test_response_time_within_sla(self, client):
        """Response arrives within the configured MAX_RESPONSE_TIME_MS"""
        response = client.get("/users")
        assert_response_time(response)

    def test_response_has_json_body(self, client):
        """Response body parses to a dict - confirms Content-Type handling"""
        response = client.get("/users")
        assert isinstance(response.body, dict)
        f"Expected dict body, got {type(response.body).__name__}"

    def test_response_schema_is_valid(self, client):
        """Response body matches the appropriate schema based on auth state"""
        response = client.get("/users")
        from config import settings
        if settings.API_KEY:
            model = assert_schema(response, UserListResponse)
            assert len(model.data) > 0, "Expected at least one user in the list"
        else:
            # Without API key, ReqRes returns 401 with a specific error schema
            assert "error" in response.body, "Expected error object in 401 response"
            assert response.body["error"] == "missing_api_key"

    def test_settings_are_loaded(self):
        """Smoke check that settings load from .env without exceptions"""
        from config import settings
        assert settings.BASE_URL.startswith("https")
        assert settings.API_PREFIX == "/api"
        assert settings.MAX_RESPONSE_TIME_MS > 0
        assert settings.REQUEST_TIMEOUT_MS > 0
        assert "@" in settings.TEST_EMAIL