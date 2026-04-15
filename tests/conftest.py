"""
tests/conftest.py
─────────────────
Global pytest fixtures shared across all test modules.

Fixture scope strategy:
  - `playwright` and `browser`  → session scope  (created once per run)
  - `api_request_context`       → session scope  (one HTTP context for all tests)
  - `client`                    → session scope  (one ReqResClient instance)

Using session scope avoids the overhead of spinning up a new browser
context for every single test while keeping full Playwright routing
capabilities (needed for mocking in Day 6).

If a test needs an isolated context (e.g. to test a specific header),
it can create its own fixture with a narrower scope by overriding
`api_request_context` locally in that test module.
"""

import pytest
from playwright.sync_api import Playwright, APIRequestContext

from clients.api_client import ReqResClient
from config import settings


@pytest.fixture(scope="session")
def api_request_context(playwright: Playwright) -> APIRequestContext:
    """
    Playwright APIRequestContext with base URL and default headers set.

    Using extraHTTPHeaders here means every request automatically
    sends Content-Type: application/json without repeating it in tests.
    """
    context = playwright.request.new_context(
        base_url=settings.BASE_URL,
        extra_http_headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    yield context
    context.dispose()


@pytest.fixture(scope="session")
def client(api_request_context: APIRequestContext) -> ReqResClient:
    """
    Ready-to-use ReqResClient instance.

    Tests import and use this fixture directly:
        def test_something(client):
            response = client.get("/users")
    """
    return ReqResClient(api_request_context)