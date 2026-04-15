"""
clients/api_client.py
─────────────────────
Thin wrapper around Playwright's APIRequestContext.

Responsibilities:
  - Set base URL and default headers once
  - Measure response time for every request
  - Expose clean GET / POST / PUT / PATCH / DELETE methods
  - Return a lightweight APIResponse dataclass with the data tests need

Tests never call playwright's request context directly — they always
go through this client. That way, if the underlying HTTP layer ever
changes, only this file needs updating.
"""

import time
from dataclasses import dataclass, field
from typing import Any

from playwright.sync_api import APIRequestContext
from config import settings

@dataclass
class APIResponse:
    """Structured response returned by every client method"""

    status: int # Parsed JSON or None
    body: Any
    headers: dict[str, str]
    elapsed_ms: float # Actual round-trip time
    raw_text: str = field(default="") # Useful for debugging non-JSON bodies

class ReqResClient:
    """
    HTTP client for the ReqRes API.

    Usage inside a pytest fixture:
        client = ReqResClient(api_request_context)
        response = client.get("/users", params={"page": 2})
        assert response.status == 200
    """

    def __init__(self, context: APIRequestContext) -> None:
        self._ctx = context

    # Private helpers

    def _build_url(self, path: str) -> str:
        """
        Combine BASE_API_URL with a path.

        Accepts paths with or without a leading slash so callers
        can write either client.get('/users') or client.get('users').
        """
        return f"{settings.BASE_API_URL}/{path.lstrip('/')}"

    def _parse(self, response) -> APIResponse:
        """Convert a Playwright APIResponse into our internal dataclass"""
        start = time.monotonic()

        # Attempt JSON parse; fall back to plain text for non-JSON bodies
        try:
            body = response.json()
        except Exception:
            body = None

        elapsed_ms = (time.monotonic() - start) * 1_000 # Convert to ms

        return APIResponse(
            status = response.status,
            body=body,
            headers = dict(response.headers),
            elapsed_ms=elapsed_ms,
            raw_text=response.text(),
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> APIResponse:
        """
        Core method — every public method delegates here.
        Times the full round-trip (not just parse time).
        """
        if settings.MOCK_API:
            from clients.api_mock import get_mock_response
            return get_mock_response(method, path, params)

        url = self._build_url(path)
        kwargs: dict[str, Any] = {
            "timeout": settings.REQUEST_TIMEOUT_MS,
        }

        req_headers = {}
        if settings.API_KEY:
            req_headers["x-api-key"] = settings.API_KEY
        if headers:
            req_headers.update(headers)
            
        if req_headers:
            kwargs["headers"] = req_headers

        if params:
            kwargs["params"] = params
        if data is not None:
            kwargs["data"] = data

        start = time.monotonic()
        raw = self._ctx.fetch(url, method=method, **kwargs)
        elapsed_ms = (time.monotonic() - start) * 1_000

        # Build the response - override elpased so it covers the full trip
        response = self._parse(raw)
        response.elapsed_ms = elapsed_ms
        return response

    # Public API

    def get(self, path: str, *, params: dict | None = None) -> APIResponse:
        return self._request("GET", path, params=params)

    def post(
        self,
        path: str,
        *,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> APIResponse:
        return self._request("POST", path, data=data, headers=headers)

    def put(self, path: str, *, data: dict | None = None) -> APIResponse:
        return self._request("PUT", path, data=data)

    def patch(self, path: str, *, data: dict | None = None) -> APIResponse:
        return self._request("PATCH", path, data = data)

    def delete(self, path: str) -> APIResponse:
        return self._request("DELETE", path)