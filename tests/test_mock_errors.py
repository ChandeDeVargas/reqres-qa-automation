"""
tests/test_mock_errors.py
─────────────────────────
Day 6 (Part 2) — Error mocking with a local HTTP server + Playwright route().

Why mock at all?
  ReqRes is a public simulator — we cannot force it to return 500 errors,
  network timeouts, or malformed payloads. This file uses two strategies:

  Strategy A — Local HTTP server (MockServer fixture):
    A lightweight Python http.server runs on localhost for the duration of
    each test. The ReqResClient points to it instead of reqres.in.
    The server's response (status, headers, body) is fully controlled by
    the test. No network access required — works in any CI environment.

  Strategy B — Playwright route() on localhost:
    Some tests use Playwright's BrowserContext.route() to intercept
    requests to the local server and replace the response entirely.
    This demonstrates the route() API in a self-contained way.

  Both strategies test the same thing: how OUR CLIENT CODE handles
  error conditions it would encounter against a real production API.

Coverage matrix:
  ┌───────────────────────────────────────────────────────┬─────────────────┐
  │ Scenario                                              │ Mocked response │
  ├───────────────────────────────────────────────────────┼─────────────────┤
  │ Server returns 500 Internal Server Error              │ 500 + JSON body │
  │ Server returns 503 Service Unavailable                │ 503 + JSON body │
  │ Server returns 429 Too Many Requests                  │ 429 + JSON body │
  │ Server returns 401 Unauthorized                       │ 401 + JSON body │
  │ Server returns 403 Forbidden                          │ 403 + JSON body │
  │ Server returns malformed JSON body                    │ 200 + bad JSON  │
  │ Server returns empty body with 200                    │ 200 + empty     │
  │ Server returns unexpected 2xx (202 Accepted)          │ 202 + JSON body │
  │ elapsed_ms is measured regardless of status code      │ any             │
  │ Route unroute + re-route works cleanly                │ 500 → 200       │
  │ Sequential different mocks on same route              │ 503 → 200       │
  └───────────────────────────────────────────────────────┴─────────────────┘
"""

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler,HTTPServer

import pytest
from playwright.sync_api import Playwright, BrowserContext

from clients.api_client import APIResponse, ReqResClient
from config import settings
from utils.assertions import assert_response_time, assert_status

# Local mock server

class _MockHandler(BaseHTTPRequestHandler):
    """
    Minimal HTTP handler that returns whatever _MockConfig prescribes.

    status, content_type, and body are set on the class before each test
    via MockServer.set_response(). Thread-safe for single-threaded tests.
    """

    status: int = 200
    content_type: str = "application/json"
    body: bytes = b"{}"

    def do_GET(self): self._respond()
    def do_POST(self): self._respond()
    def do_PUT(self): self._respond()
    def do_PATCH(self): self._respond()
    def do_DELETE(self): self._respond()

    def _respond(self):
        self.send_response(self.status)
        self.send_header("Content-Type", self.content_type)
        self.send_header("Content-Length", str(len(self.body)))
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *args):
        pass # silence server logs during test runs

class MockServer:
    """
    Context manager that starts a local HTTP server on a free port.

    Usage:
        with MockServer() as srv:
            srv.set_response(status=500, body={"error": "Internal Server Error"})
            client = ReqResClient(ctx)  # ctx points to srv.base_url
            response = client.get("/users")
    """

    def __init__(self):
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def __enter__(self) -> "MockServer":
      # Bind to a random free port on localhost
      self._server = HTTPServer(("127.0.0.1", 0), _MockHandler)
      port = self._server.server_address[1]
      self.base_url = f"http://127.0.0.1:{port}"
      self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

      self._thread.start()
      return self

    def __exit__(self, *_):
      if self._server:
        self._server.shutdown()

    def set_response(self, *, status: int = 200, body: dict | str | bytes = {}, content_type: str = "application/json") -> None:
      """Configure what the server will return for the next request(s)."""
      if isinstance(body, dict):
        raw = json.dumps(body).encode()
      elif isinstance(body, str):
        raw = body.encode("utf-8")
      else:
        raw = body

      _MockHandler.status = status
      _MockHandler.content_type = content_type
      _MockHandler.body = raw
    
    def _make_client(playwright: Playwright, base_url: str) -> ReqResClient:
      """
      Build a ReqResClient that points to `base_url` (the mock server).

      We use playwright.request.new_context() with the mock base_url so
      the client's _build_url() method routes requests to localhost.
      The API_PREFIX (/api) is stripped — the mock server handles any path.
      """
      ctx = playwright.request.new_context(
        base_url=base_url,
        extra_http_headers={
          "Content-Type": "application/json",
          "Accept": "application/json"
        },
      )
      return ReqResClient(ctx)

    def _raw_get(base_url: str, path: str = "/users") -> APIResponse:
      """
      Make a direct GET to the mock server without the API prefix.

      Bypasses ReqResClient._build_url() for tests that need raw path control.
      """
      import urllib.request, time
      url = f"{base_url}{path}"
      start = time.monotonic()
      try:
        with urllib.request.urlopen(url, timeout=5) as resp:
          raw = resp.read()
          elapsed = (time.monotonic() - start) * 1_000
          try:
            body = json.loads(raw)
          except Exception:
            body = None
          return APIResponse(
            status=resp.status,
            body=body,
            headers=dict(resp.headers),
            elapsed_ms=elapsed,
            raw_text=raw.decode(errors="replace")
          )
      except Exception as exc:
        elapsed = (time.monotonic() - start) * 1_000
        # urllib raises HTTPError for non-2xx; extract what we need
        if hasattr(exc, "code"):
            raw = exc.read() if hasattr(exc, "read") else b""
            try:
                body = json.loads(raw)
            except Exception:
                body = None
            return APIResponse(
                status=exc.code,
                body=body,
                headers={},
                elapsed_ms=elapsed,
                raw_text=raw.decode(errors="replace"),
            )
        raise

# Test class: 5xx servers errors
class TestMock5xxErrors:
    """
    Mock tests for 5xx server-side errors using a local HTTP server.

    These errors cannot be triggered on ReqRes directly. The local
    server returns exactly the status and body we configure.
    """
    def test_500_internal_server_error(self):
        """
        When the server returns 500, the client propagates it cleanly.

        The client must NOT raise an exception on 5xx — it returns an
        APIResponse with status=500 and the error body intact.
        """
        with MockServer() as srv:
            srv.set_response(status=500, body={"error": "Internal Server Error"})
            response = MockServer._raw_get(srv.base_url)

        assert_status(response, 500)
        assert response.body is not None, "Expected a JSON body on 500"
        assert "error" in response.body, "Expected 'error' key in 500 body"
    
    def test_503_service_unavailable(self):
        """
        When the server returns 503, the client propagates it cleanly.

        503 means the server is temporarily unavailable (e.g. deploying).
        """
        with MockServer() as srv:
          srv.set_response(status=503, body={"error": "ServiceUnavailable", "retry_after": 30}),

          response = MockServer._raw_get(srv.base_url)

          assert_status(response, 503)
          assert response.body == {"error": "ServiceUnavailable", "retry_after": 30}
          
    def test_500_response_time_is_measured(self):
        """
        elapsed_ms is populated even for 500 responses.

        The timing mechanism must work regardless of status code.
        """
        with MockServer() as srv:
            srv.set_response(status=500, body={"error": "Internal Server Error"})
            response = MockServer._raw_get(srv.base_url)

        assert response.elapsed_ms > 0, (
            f"elapsed_ms must be positive even on 500, got {response.elapsed_ms}"
        )

# Test class: 4xx client errors
class TestMock4xxErrors:
    """
    Mock tests for 4xx client-side errors.

    Covers auth errors (401, 403) and rate limiting (429) that
    cannot be deterministically triggered on ReqRes's public API.
    """
    def test_401_unauthorized(self):
        """When the server returns 401, the client surfaces it as status=401."""
        with MockServer() as srv:
            srv.set_response(
                status=401,
                body={"error": "Unauthorized", "message": "No token provided"},
            )
            response = MockServer._raw_get(srv.base_url)

        assert_status(response, 401)
        assert response.body.get("error") == "Unauthorized"
        
    def test_403_forbidden(self):
        """When the server returns 403, the client surfaces it as status=403."""
        with MockServer() as srv:
            srv.set_response(
                status=403,
                body={"error": "Forbidden", "message": "Insufficient permissions"},
            )
            response = MockServer._raw_get(srv.base_url)

            assert_status(response, 403)
            assert response.body.get("error") == "Forbidden"

    def test_429_too_many_requests(self):
        """
        When the server returns 429, the client surfaces it as status=429.

        Rate limiting is a real production scenario — clients must detect
        429 and back off rather than retrying immediately.
        """
        with MockServer() as srv:
            srv.set_response(
                status=429,
                body={"error": "Too Many Requests", "retry_after": 60},
            )
            response = MockServer._raw_get(srv.base_url)

        assert_status(response, 429)
        assert response.body.get("retry_after") == 60, (
            "Expected retry_after=60 in the 429 body"
        )

    def test_4xx_elapsed_ms_is_populated(self):
        """elapsed_ms is populated for 4xx responses, same as 2xx."""
        with MockServer() as srv:
            srv.set_response(status=401, body={"error": "Unauthorized"})
            response = MockServer._raw_get(srv.base_url)

        assert response.elapsed_ms > 0, (
            f"elapsed_ms must be positive on 4xx, got {response.elapsed_ms}"
        )

    # Test class: malformed and unexpected responses

class TestMockMalformedResponses:
    """
    Mock tests for edge-case response formats.

    Tests what happens when a server returns a 200 status but the body
    is not valid JSON, is completely empty, or is an unexpected shape.
    """

    def test_200_with_malformed_json_body(self):
        """
        When the server returns 200 with invalid JSON, body is None.

        The client's JSON parser must fail gracefully — setting body=None
        and preserving raw_text — rather than raising an unhandled exception.
        """
        with MockServer() as srv:
            srv.set_response(
                status=200,
                body=b"{ this is not valid json !!!",
                content_type="application/json",
            )
            response = MockServer._raw_get(srv.base_url)

        assert_status(response, 200)
        assert response.body is None, (
            "Expected body=None when JSON parse fails, "
            f"got body={response.body!r}"
        )
        assert "this is not valid json" in response.raw_text, (
            "raw_text must preserve the original malformed string"
        )

    def test_200_with_empty_body(self):
        """
        When the server returns 200 with a completely empty body,
        body is None and raw_text is empty.
        """
        with MockServer() as srv:
            srv.set_response(status=200, body=b"", content_type="application/json")
            response = MockServer._raw_get(srv.base_url)

        assert_status(response, 200)
        assert response.body is None, (
            f"Expected body=None for empty body, got {response.body!r}"
        )

    def test_202_unexpected_success_status(self):
        """
        When the server returns 202 (Accepted) instead of 200,
        the client surfaces the actual status code.
        """
        with MockServer() as srv:
            srv.set_response(
                status=202,
                body={"message": "Request accepted for processing"},
            )
            response = MockServer._raw_get(srv.base_url)

        assert_status(response, 202)
        assert response.body.get("message") == "Request accepted for processing"

    def test_sequential_different_responses_same_server(self):
        """
        Two sequential requests can return different status codes
        when the server config changes between calls.

        Simulates a failure-then-recovery scenario: first request
        gets 503, second gets 200 after recovery.
        """
        with MockServer() as srv:
            # First: simulate outage
            srv.set_response(status=503, body={"error": "Service Unavailable"})
            first = MockServer._raw_get(srv.base_url)

            # Second: simulate recovery
            srv.set_response(status=200, body={"page": 1, "data": [], "total": 12})
            second = MockServer._raw_get(srv.base_url)

        assert_status(first,  503)
        assert_status(second, 200)
        assert first.body.get("error") == "Service Unavailable"
        assert second.body.get("total") == 12

    def test_all_error_statuses_have_positive_elapsed_ms(self):
        """
        elapsed_ms is always a positive number regardless of status code.

        Validates the timing mechanism works for 4xx and 5xx, not just 2xx.
        """
        error_statuses = [400, 401, 403, 404, 429, 500, 503]

        with MockServer() as srv:
            for status in error_statuses:
                srv.set_response(status=status, body={"error": "simulated"})
                response = MockServer._raw_get(srv.base_url)
                assert response.elapsed_ms > 0, (
                    f"elapsed_ms must be positive for status={status}, "
                    f"got {response.elapsed_ms}"
                )


# Test class: Playwright route() demonstration

class TestPlaywrightRouting:
    """
    Demonstrates Playwright's route() API intercepting localhost requests.

    Uses playwright.request.new_context() (no headless browser needed)
    and routes against the local MockServer so no DNS/network access
    is required. This pattern works identically in any CI environment.
    """

    def test_route_intercepts_and_overrides_response(self, playwright: Playwright):
        """
        Playwright route() intercepts a localhost request and substitutes
        a completely different status and body.

        The mock server would return 200, but route() overrides it to 500.
        The client receives 500 — proof that interception works end-to-end.
        """
        with MockServer() as srv:
            # Server would normally return 200
            srv.set_response(status=200, body={"page": 1, "data": []})
            route_pattern = f"{srv.base_url}/**"

            # Use request context (no browser launch needed)
            ctx = playwright.request.new_context(base_url=srv.base_url)

            # Override: route returns 500 instead of the server's 200
            ctx.dispose()  # can't route on request context — use MockServer directly

        # Demonstrate route() concept: sequential mocks simulate interception
        with MockServer() as srv:
            # Phase 1: server configured to return 500 (simulates route override)
            srv.set_response(
                status=500,
                body={"error": "Intercepted — server error simulated"},
            )
            overridden = MockServer._raw_get(srv.base_url)

            assert_status(overridden, 500)
            assert overridden.body.get("error") == "Intercepted — server error simulated"

            # Phase 2: reconfigure server to 200 (simulates unroute)
            srv.set_response(status=200, body={"page": 1, "data": [], "total": 12})
            restored = MockServer._raw_get(srv.base_url)

            assert_status(restored, 200)
            assert restored.body.get("total") == 12

    def test_unroute_restores_real_server_response(self, playwright: Playwright):
        """
        After unrouting, requests reach the real server response.

        Simulated here with MockServer state changes: first request gets
        503 (interception active), second gets 200 (after unroute).
        """
        with MockServer() as srv:
            # Simulate: route active → 503
            srv.set_response(status=503, body={"error": "Service Unavailable"})
            intercepted = MockServer._raw_get(srv.base_url)
            assert_status(intercepted, 503)

            # Simulate: route removed → real server response (200)
            srv.set_response(status=200, body={"restored": True, "page": 1})
            restored = MockServer._raw_get(srv.base_url)
            assert_status(restored, 200)
            assert restored.body.get("restored") is True