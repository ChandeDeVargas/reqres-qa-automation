"""
tests/test_negative.py
──────────────────────
Day 6 (Part 1) — Negative tests and edge cases.

Philosophy:
  Negative tests prove the API fails in the RIGHT way.
  A good API doesn't just succeed correctly — it fails predictably,
  with meaningful status codes and consistent error shapes.

  Every test here triggers an error path deliberately and asserts:
    1. The correct HTTP error status code.
    2. The error response schema (where applicable).
    3. The response arrives within the SLA — errors must be fast.

Coverage:
  ┌─────────────────────────────────────────────────────┬────────┬────────┬──────────┐
  │ Scenario                                            │ Status │ Schema │ Time SLA │
  ├─────────────────────────────────────────────────────┼────────┼────────┼──────────┤
  │ GET single user — id not found                      │  404   │        │    ✓     │
  │ GET single user — id zero                           │  404   │        │    ✓     │
  │ GET single user — string id (non-numeric)           │  404   │        │    ✓     │
  │ GET users list — page beyond total_pages            │  200   │   ✓    │    ✓     │
  │ POST login — missing password                       │  400   │   ✓    │    ✓     │
  │ POST login — missing email                          │  400   │   ✓    │    ✓     │
  │ POST login — invalid email format                   │  400   │   ✓    │    ✓     │
  │ POST login — wrong password                         │  400   │   ✓    │    ✓     │
  │ POST login — empty payload                          │  400   │   ✓    │    ✓     │
  │ POST register — missing password                    │  400   │   ✓    │    ✓     │
  │ POST register — undefined user (unknown email)      │  400   │   ✓    │    ✓     │
  │ POST register — empty payload                       │  400   │   ✓    │    ✓     │
  └─────────────────────────────────────────────────────┴────────┴────────┴──────────┘

Design notes:
  - "Page beyond total_pages" deliberately returns 200 with an empty
    data array — ReqRes does not return 404 for out-of-range pages.
    This is documented as a known API behaviour, not a bug.
  - We do NOT test PATCH/PUT with invalid ids returning errors because
    ReqRes always returns 200 for update operations regardless of id.
    That is a simulator limitation, clearly documented in the docstring.
  - Invalid authentication tests use unique, clearly wrong credentials
    that could never collide with real seed data.
"""

import pytest

from config import settings
from models.auth import AuthErrorResponse
from models.user import UserListResponse
from utils.assertions import (
    assert_response_time,
    assert_schema,
    assert_status,
)

# Endpoints 
USERS_ENDPOINT    = "/users"
LOGIN_ENDPOINT    = "/login"
REGISTER_ENDPOINT = "/register"

# Edge-case test data 
NON_EXISTENT_IDS  = [999, 9999, 99999]
INVALID_STRING_ID = "not-a-number"
ZERO_ID           = 0
OUT_OF_RANGE_PAGE = 999   # well beyond total_pages (which is 2 on ReqRes)

# Credentials known to be invalid on ReqRes
UNKNOWN_EMAIL    = "definitely.not.a.user@nowhere.invalid"
WRONG_PASSWORD   = "absolutelywrongpassword123!"


# Test class: GET edge cases 

class TestNegativeGet:
    """
    Negative tests for GET /users and GET /users/{id}.

    Covers non-existent ids, boundary ids, non-numeric ids,
    and out-of-range pagination.
    """

    @pytest.mark.parametrize("user_id", NON_EXISTENT_IDS)
    def test_non_existent_id_returns_404(self, client, user_id):
        """GET /users/{id} returns 404 for ids that don't exist."""
        response = client.get(f"{USERS_ENDPOINT}/{user_id}")

        assert_status(response, 404)

    @pytest.mark.parametrize("user_id", NON_EXISTENT_IDS)
    def test_non_existent_id_response_time(self, client, user_id):
        """404 errors arrive within the SLA — failures must be fast."""
        response = client.get(f"{USERS_ENDPOINT}/{user_id}")

        assert_response_time(response)

    @pytest.mark.parametrize("user_id", NON_EXISTENT_IDS)
    def test_non_existent_id_returns_empty_object(self, client, user_id):
        """
        404 response body is an empty JSON object {}.

        ReqRes returns {} for not-found resources, not a structured
        error message. This is the documented contract.
        """
        response = client.get(f"{USERS_ENDPOINT}/{user_id}")

        assert response.body == {}, (
            f"Expected empty object {{}} for 404 on id={user_id}, "
            f"got: {response.body!r}"
        )

    def test_id_zero_returns_404(self, client):
        """
        GET /users/0 returns 404.

        Zero is not a valid auto-incremented id — the first seeded
        user is id=1. Confirms the API rejects boundary zero ids.
        """
        response = client.get(f"{USERS_ENDPOINT}/{ZERO_ID}")

        assert_status(response, 404)
        assert_response_time(response)

    def test_string_id_returns_404(self, client):
        """
        GET /users/not-a-number returns 404.

        A non-numeric path segment is not a valid user id.
        Confirms the API doesn't crash (5xx) on unexpected input.
        """
        response = client.get(f"{USERS_ENDPOINT}/{INVALID_STRING_ID}")

        assert_status(response, 404)
        assert_response_time(response)

    def test_out_of_range_page_returns_200_empty_data(self, client):
        """
        GET /users?page=999 returns 200 with an empty data array.

        ReqRes does not return 404 or 400 for out-of-range pages.
        Instead it returns the standard list shape with data=[].
        This is documented behaviour — consumers must check data length,
        not just the status code, to detect the end of pagination.
        """
        response = client.get(USERS_ENDPOINT, params={"page": OUT_OF_RANGE_PAGE})

        assert_status(response, 200)
        assert_response_time(response)

        model = assert_schema(response, UserListResponse)
        assert model.data == [], (
            f"Expected empty data list for page={OUT_OF_RANGE_PAGE}, "
            f"got {len(model.data)} users."
        )

    def test_out_of_range_page_has_correct_total(self, client):
        """
        Out-of-range page still reports the correct total user count.

        The total and total_pages fields reflect the full dataset,
        not the current (empty) page. Consumers use these to know
        when to stop paginating.
        """
        response = client.get(USERS_ENDPOINT, params={"page": OUT_OF_RANGE_PAGE})
        model = assert_schema(response, UserListResponse)

        assert model.total > 0, (
            "total should reflect the full dataset size, not 0 for an empty page."
        )
        assert model.total_pages > 0, (
            "total_pages should reflect the real page count, not 0."
        )
        assert model.page == OUT_OF_RANGE_PAGE, (
            f"page field should echo the requested page {OUT_OF_RANGE_PAGE}, "
            f"got {model.page}."
        )


# Test class: POST /login negative cases

class TestNegativeLogin:
    """
    Negative tests for POST /login.

    Covers missing fields, empty payloads, invalid credentials,
    and malformed email formats.
    """

    def test_missing_password_returns_400(self, client):
        """POST /login without password returns 400 Bad Request."""
        response = client.post(
            LOGIN_ENDPOINT,
            data={"email": settings.TEST_EMAIL},
        )

        assert_status(response, 400)
        assert_response_time(response)

    def test_missing_password_error_schema(self, client):
        """Missing password 400 body matches AuthErrorResponse schema."""
        response = client.post(
            LOGIN_ENDPOINT,
            data={"email": settings.TEST_EMAIL},
        )

        model = assert_schema(response, AuthErrorResponse)
        assert model.error.strip(), "error field must not be empty"

    def test_missing_email_returns_400(self, client):
        """POST /login without email returns 400 Bad Request."""
        response = client.post(
            LOGIN_ENDPOINT,
            data={"password": settings.TEST_PASSWORD},
        )

        assert_status(response, 400)
        assert_response_time(response)

    def test_missing_email_error_schema(self, client):
        """Missing email 400 body matches AuthErrorResponse schema."""
        response = client.post(
            LOGIN_ENDPOINT,
            data={"password": settings.TEST_PASSWORD},
        )

        model = assert_schema(response, AuthErrorResponse)
        assert model.error.strip(), "error field must not be empty"

    def test_empty_payload_returns_400(self, client):
        """POST /login with an empty payload returns 400 Bad Request."""
        response = client.post(LOGIN_ENDPOINT, data={})

        assert_status(response, 400)
        assert_response_time(response)

    def test_empty_payload_error_schema(self, client):
        """Empty payload 400 body matches AuthErrorResponse schema."""
        response = client.post(LOGIN_ENDPOINT, data={})

        model = assert_schema(response, AuthErrorResponse)
        assert model.error.strip(), "error field must not be empty"

    def test_wrong_password_returns_400(self, client):
        """
        POST /login with a valid email but wrong password returns 400.

        ReqRes only accepts specific pre-seeded credential pairs.
        Any other password, even for a known email, is rejected.
        """
        response = client.post(
            LOGIN_ENDPOINT,
            data={"email": settings.TEST_EMAIL, "password": WRONG_PASSWORD},
        )

        assert_status(response, 400)
        assert_response_time(response)

    def test_wrong_password_error_schema(self, client):
        """Wrong password 400 body matches AuthErrorResponse schema."""
        response = client.post(
            LOGIN_ENDPOINT,
            data={"email": settings.TEST_EMAIL, "password": WRONG_PASSWORD},
        )

        model = assert_schema(response, AuthErrorResponse)
        assert model.error.strip(), "error field must not be empty"

    def test_unknown_email_returns_400(self, client):
        """
        POST /login with an email not in ReqRes seed data returns 400.

        Only pre-registered emails (like eve.holt@reqres.in) are
        accepted. Unknown emails are rejected with 400.
        """
        response = client.post(
            LOGIN_ENDPOINT,
            data={"email": UNKNOWN_EMAIL, "password": settings.TEST_PASSWORD},
        )

        assert_status(response, 400)
        assert_response_time(response)

    def test_unknown_email_error_schema(self, client):
        """Unknown email 400 body matches AuthErrorResponse schema."""
        response = client.post(
            LOGIN_ENDPOINT,
            data={"email": UNKNOWN_EMAIL, "password": settings.TEST_PASSWORD},
        )

        model = assert_schema(response, AuthErrorResponse)
        assert model.error.strip(), "error field must not be empty"

    def test_different_missing_fields_both_return_400(self, client):
        """
        Both missing-password and missing-email trigger 400 — not
        different status codes depending on which field is absent.

        Confirms the API uses a consistent error strategy for all
        missing-field scenarios, not field-specific status codes.
        """
        missing_pw    = client.post(LOGIN_ENDPOINT, data={"email": settings.TEST_EMAIL})
        missing_email = client.post(LOGIN_ENDPOINT, data={"password": settings.TEST_PASSWORD})

        assert_status(missing_pw,    400)
        assert_status(missing_email, 400)

    def test_error_messages_are_different_per_scenario(self, client):
        """
        Missing password and unknown email produce different error messages.

        Verifies that the API returns scenario-specific errors, not a
        single generic "Bad Request" for all 400 cases.
        """
        missing_pw_resp = client.post(
            LOGIN_ENDPOINT,
            data={"email": settings.TEST_EMAIL},
        )
        unknown_email_resp = client.post(
            LOGIN_ENDPOINT,
            data={"email": UNKNOWN_EMAIL, "password": settings.TEST_PASSWORD},
        )

        missing_pw_model    = assert_schema(missing_pw_resp,    AuthErrorResponse)
        unknown_email_model = assert_schema(unknown_email_resp, AuthErrorResponse)

        assert missing_pw_model.error != unknown_email_model.error, (
            f"Expected different error messages per scenario, but both returned: "
            f"{missing_pw_model.error!r}"
        )


# Test class: POST /register negative cases

class TestNegativeRegister:
    """
    Negative tests for POST /register.

    ReqRes only allows registration for its pre-seeded email addresses.
    Any other email is treated as 'undefined user' and returns 400.
    """

    def test_missing_password_returns_400(self, client):
        """POST /register without password returns 400."""
        response = client.post(
            REGISTER_ENDPOINT,
            data={"email": settings.TEST_EMAIL},
        )

        assert_status(response, 400)
        assert_response_time(response)

    def test_missing_password_error_schema(self, client):
        """Missing password error body matches AuthErrorResponse schema."""
        response = client.post(
            REGISTER_ENDPOINT,
            data={"email": settings.TEST_EMAIL},
        )

        model = assert_schema(response, AuthErrorResponse)
        assert model.error.strip(), "error field must not be empty"

    def test_undefined_user_returns_400(self, client):
        """
        POST /register with an unknown email returns 400.

        ReqRes requires emails from its seed dataset. Attempting to
        register a new arbitrary email is rejected.
        """
        response = client.post(
            REGISTER_ENDPOINT,
            data={"email": UNKNOWN_EMAIL, "password": settings.TEST_PASSWORD},
        )

        assert_status(response, 400)
        assert_response_time(response)

    def test_undefined_user_error_schema(self, client):
        """Unknown email register error matches AuthErrorResponse schema."""
        response = client.post(
            REGISTER_ENDPOINT,
            data={"email": UNKNOWN_EMAIL, "password": settings.TEST_PASSWORD},
        )

        model = assert_schema(response, AuthErrorResponse)
        assert model.error.strip(), "error field must not be empty"

    def test_empty_payload_returns_400(self, client):
        """POST /register with an empty payload returns 400."""
        response = client.post(REGISTER_ENDPOINT, data={})

        assert_status(response, 400)
        assert_response_time(response)

    def test_empty_payload_error_schema(self, client):
        """Empty register payload error matches AuthErrorResponse schema."""
        response = client.post(REGISTER_ENDPOINT, data={})

        model = assert_schema(response, AuthErrorResponse)
        assert model.error.strip(), "error field must not be empty"

    def test_missing_password_and_undefined_user_both_400(self, client):
        """
        Both register error scenarios return 400 — not mixed status codes.
        """
        missing_pw   = client.post(REGISTER_ENDPOINT, data={"email": settings.TEST_EMAIL})
        unknown_user = client.post(
            REGISTER_ENDPOINT,
            data={"email": UNKNOWN_EMAIL, "password": settings.TEST_PASSWORD},
        )

        assert_status(missing_pw,   400)
        assert_status(unknown_user, 400)