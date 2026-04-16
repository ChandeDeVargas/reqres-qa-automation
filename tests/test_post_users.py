"""
tests/test_post_users.py
────────────────────────
Day 3 — POST /users · POST /login · POST /register

Coverage matrix:
  ┌──────────────────────────────────────────────────┬────────┬────────┬──────────┐
  │ Scenario                                         │ Status │ Schema │ Time SLA │
  ├──────────────────────────────────────────────────┼────────┼────────┼──────────┤
  │ Create user — valid payload                      │  201   │   ✓    │    ✓     │
  │ Create user — response echoes sent fields        │  201   │   ✓    │          │
  │ Create user — id is generated and non-empty      │  201   │   ✓    │          │
  │ Create user — createdAt is present (ISO-like)    │  201   │   ✓    │          │
  │ Create user — parametrized payloads              │  201   │   ✓    │    ✓     │
  │ Create user — only name (no job field)           │  201   │        │          │
  │ Create user — only job (no name field)           │  201   │        │          │
  │ Login — valid credentials                        │  200   │   ✓    │    ✓     │
  │ Login — token is non-empty string                │  200   │   ✓    │          │
  │ Login — missing password returns 400             │  400   │   ✓    │    ✓     │
  │ Login — missing email returns 400                │  400   │   ✓    │          │
  │ Register — valid credentials                     │  200   │   ✓    │    ✓     │
  │ Register — returns id and token                  │  200   │   ✓    │          │
  │ Register — missing password returns 400          │  400   │   ✓    │    ✓     │
  └──────────────────────────────────────────────────┴────────┴────────┴──────────┘

Design notes:
  - Payloads live as module-level constants — no magic strings inside tests.
  - @pytest.mark.parametrize covers multiple create-user scenarios in one pass.
  - Auth tests use credentials from settings (loaded from .env), never hardcoded.
  - createdAt validation is intentionally lenient: we confirm it exists and is
    a non-empty string. Strict ISO-8601 parsing would couple tests to ReqRes's
    exact timestamp format, which is an implementation detail, not a contract.
"""

import pytest

from config import settings
from models.auth import AuthErrorResponse, LoginResponse, RegisterResponse
from models.user import CreateUserResponse
from utils.assertions import (
    assert_body_contains,
    assert_field_present,
    assert_response_time,
    assert_schema,
    assert_status,
)

# Endpoints
USERS_ENDPOINT    = "/users"
LOGIN_ENDPOINT    = "/login"
REGISTER_ENDPOINT = "/register"

# Reusable payloads
# Defined once here so every test references the same data.
# If ReqRes changes its seed data, only these constants need updating.

VALID_USER_PAYLOAD = {"name": "morpheus", "job": "leader"}

PARAMETRIZED_PAYLOADS = [
    {"name": "neo",      "job": "the one"},
    {"name": "trinity",  "job": "operator"},
    {"name": "agent smith", "job": "agent"},
]


# Test class: POST /users

class TestCreateUser:
    """Tests for POST /users — creates a new user resource."""

    def test_status_201_valid_payload(self, client):
        """POST /users with a valid payload returns 201 Created."""
        response = client.post(USERS_ENDPOINT, data=VALID_USER_PAYLOAD)

        assert_status(response, 201)

    def test_response_time_valid_payload(self, client):
        """Create user response arrives within the SLA."""
        response = client.post(USERS_ENDPOINT, data=VALID_USER_PAYLOAD)

        assert_response_time(response)

    def test_schema_valid_payload(self, client):
        """Response body matches the CreateUserResponse schema."""
        response = client.post(USERS_ENDPOINT, data=VALID_USER_PAYLOAD)

        assert_schema(response, CreateUserResponse)

    def test_response_echoes_name_and_job(self, client):
        """
        The API echoes back the name and job fields we sent.

        This is a fundamental contract: what you POST is what you get back,
        letting clients confirm the resource was created with the right data.
        """
        response = client.post(USERS_ENDPOINT, data=VALID_USER_PAYLOAD)

        assert_body_contains(
            response,
            name=VALID_USER_PAYLOAD["name"],
            job=VALID_USER_PAYLOAD["job"],
        )

    def test_id_is_generated(self, client):
        """
        The API generates and returns a non-empty id for each new user.

        ReqRes returns id as a string (e.g. "123"), not an integer.
        We verify presence and non-emptiness, not the exact value,
        since generated ids vary per request.
        """
        response = client.post(USERS_ENDPOINT, data=VALID_USER_PAYLOAD)
        model = assert_schema(response, CreateUserResponse)

        assert model.id, f"Expected a non-empty id, got: {model.id!r}"
        assert str(model.id).isdigit(), (
            f"Expected id to be a numeric string, got: {model.id!r}"
        )

    def test_created_at_is_present(self, client):
        """
        createdAt is returned and is a non-empty string.

        We validate presence and non-emptiness only — not strict ISO format —
        because the exact timestamp format is an implementation detail.
        """
        response = client.post(USERS_ENDPOINT, data=VALID_USER_PAYLOAD)
        model = assert_schema(response, CreateUserResponse)

        assert model.createdAt.strip(), (
            f"Expected a non-empty createdAt timestamp, got: {model.createdAt!r}"
        )

    def test_each_created_user_gets_unique_id(self, client):
        """
        Two consecutive POST /users requests produce different ids.

        Catches broken implementations where the same id is returned
        for every creation request.
        """
        first  = client.post(USERS_ENDPOINT, data=VALID_USER_PAYLOAD)
        second = client.post(USERS_ENDPOINT, data=VALID_USER_PAYLOAD)

        first_model  = assert_schema(first,  CreateUserResponse)
        second_model = assert_schema(second, CreateUserResponse)

        assert first_model.id != second_model.id, (
            f"Both requests returned the same id={first_model.id!r}. "
            "The API should generate a unique id per creation."
        )

    @pytest.mark.parametrize("payload", PARAMETRIZED_PAYLOADS)
    def test_status_201_parametrized_payloads(self, client, payload):
        """POST /users returns 201 for varied name/job combinations."""
        response = client.post(USERS_ENDPOINT, data=payload)

        assert_status(response, 201)

    @pytest.mark.parametrize("payload", PARAMETRIZED_PAYLOADS)
    def test_schema_parametrized_payloads(self, client, payload):
        """Each varied payload response matches the CreateUserResponse schema."""
        response = client.post(USERS_ENDPOINT, data=payload)

        assert_schema(response, CreateUserResponse)

    @pytest.mark.parametrize("payload", PARAMETRIZED_PAYLOADS)
    def test_response_time_parametrized_payloads(self, client, payload):
        """Each varied payload response arrives within the SLA."""
        response = client.post(USERS_ENDPOINT, data=payload)

        assert_response_time(response)

    @pytest.mark.parametrize("payload", PARAMETRIZED_PAYLOADS)
    def test_echoes_correct_fields_parametrized(self, client, payload):
        """Each payload's name and job are echoed back correctly."""
        response = client.post(USERS_ENDPOINT, data=payload)

        assert_body_contains(response, name=payload["name"], job=payload["job"])

    def test_create_user_with_name_only(self, client):
        """
        POST /users with only a name field (no job) still returns 201.

        ReqRes is lenient: it accepts partial payloads.
        We confirm the API doesn't reject requests with optional fields missing.
        """
        response = client.post(USERS_ENDPOINT, data={"name": "morpheus"})

        assert_status(response, 201)
        assert_field_present(response, "name", "id", "createdAt")

    def test_create_user_with_job_only(self, client):
        """
        POST /users with only a job field (no name) still returns 201.
        """
        response = client.post(USERS_ENDPOINT, data={"job": "leader"})

        assert_status(response, 201)
        assert_field_present(response, "job", "id", "createdAt")


# Test class: POST /login

class TestLogin:
    """Tests for POST /login — authenticates a user and returns a token."""

    def test_status_200_valid_credentials(self, client):
        """POST /login with valid credentials returns 200 OK."""
        response = client.post(
            LOGIN_ENDPOINT,
            data={"email": settings.TEST_EMAIL, "password": settings.TEST_PASSWORD},
        )

        assert_status(response, 200)

    def test_response_time_valid_credentials(self, client):
        """Login response arrives within the SLA."""
        response = client.post(
            LOGIN_ENDPOINT,
            data={"email": settings.TEST_EMAIL, "password": settings.TEST_PASSWORD},
        )

        assert_response_time(response)

    def test_schema_valid_credentials(self, client):
        """Login response body matches the LoginResponse schema."""
        response = client.post(
            LOGIN_ENDPOINT,
            data={"email": settings.TEST_EMAIL, "password": settings.TEST_PASSWORD},
        )

        assert_schema(response, LoginResponse)

    def test_token_is_non_empty_string(self, client):
        """
        The returned token is a non-empty string.

        We validate the token exists and has content — not its exact value,
        since tokens are opaque to the test suite.
        """
        response = client.post(
            LOGIN_ENDPOINT,
            data={"email": settings.TEST_EMAIL, "password": settings.TEST_PASSWORD},
        )
        model = assert_schema(response, LoginResponse)

        assert model.token.strip(), (
            f"Expected a non-empty token, got: {model.token!r}"
        )

    def test_missing_password_returns_400(self, client):
        """POST /login without password returns 400 Bad Request."""
        response = client.post(
            LOGIN_ENDPOINT,
            data={"email": settings.TEST_EMAIL},
        )

        assert_status(response, 400)

    def test_missing_password_response_time(self, client):
        """400 error response also arrives within the SLA."""
        response = client.post(
            LOGIN_ENDPOINT,
            data={"email": settings.TEST_EMAIL},
        )

        assert_response_time(response)

    def test_missing_password_error_schema(self, client):
        """400 response body matches the AuthErrorResponse schema."""
        response = client.post(
            LOGIN_ENDPOINT,
            data={"email": settings.TEST_EMAIL},
        )

        assert_schema(response, AuthErrorResponse)

    def test_missing_password_error_message(self, client):
        """
        400 response contains a meaningful error field.

        ReqRes returns {"error": "Missing password"} — we validate the
        field exists and is non-empty rather than matching the exact string,
        making the test resilient to minor message wording changes.
        """
        response = client.post(
            LOGIN_ENDPOINT,
            data={"email": settings.TEST_EMAIL},
        )
        model = assert_schema(response, AuthErrorResponse)

        assert model.error.strip(), (
            f"Expected a non-empty error message, got: {model.error!r}"
        )

    def test_missing_email_returns_400(self, client):
        """POST /login without email also returns 400 Bad Request."""
        response = client.post(
            LOGIN_ENDPOINT,
            data={"password": settings.TEST_PASSWORD},
        )

        assert_status(response, 400)

    def test_missing_email_error_schema(self, client):
        """400 response for missing email also matches AuthErrorResponse schema."""
        response = client.post(
            LOGIN_ENDPOINT,
            data={"password": settings.TEST_PASSWORD},
        )

        assert_schema(response, AuthErrorResponse)


# Test class: POST /register

class TestRegister:
    """Tests for POST /register — registers a user and returns id + token."""

    def test_status_200_valid_credentials(self, client):
        """POST /register with valid credentials returns 200 OK."""
        response = client.post(
            REGISTER_ENDPOINT,
            data={"email": settings.TEST_EMAIL, "password": settings.TEST_PASSWORD},
        )

        assert_status(response, 200)

    def test_response_time_valid_credentials(self, client):
        """Register response arrives within the SLA."""
        response = client.post(
            REGISTER_ENDPOINT,
            data={"email": settings.TEST_EMAIL, "password": settings.TEST_PASSWORD},
        )

        assert_response_time(response)

    def test_schema_valid_credentials(self, client):
        """Register response body matches the RegisterResponse schema."""
        response = client.post(
            REGISTER_ENDPOINT,
            data={"email": settings.TEST_EMAIL, "password": settings.TEST_PASSWORD},
        )

        assert_schema(response, RegisterResponse)

    def test_returns_id_and_token(self, client):
        """
        Register response contains both an id (int) and a token (str).

        Both fields are required by the RegisterResponse schema, but we
        also assert they carry meaningful values — not zero or empty.
        """
        response = client.post(
            REGISTER_ENDPOINT,
            data={"email": settings.TEST_EMAIL, "password": settings.TEST_PASSWORD},
        )
        model = assert_schema(response, RegisterResponse)

        assert model.id > 0, f"Expected a positive user id, got: {model.id}"
        assert model.token.strip(), f"Expected a non-empty token, got: {model.token!r}"

    def test_missing_password_returns_400(self, client):
        """POST /register without password returns 400 Bad Request."""
        response = client.post(
            REGISTER_ENDPOINT,
            data={"email": settings.TEST_EMAIL},
        )

        assert_status(response, 400)

    def test_missing_password_response_time(self, client):
        """400 register error also arrives within the SLA."""
        response = client.post(
            REGISTER_ENDPOINT,
            data={"email": settings.TEST_EMAIL},
        )

        assert_response_time(response)

    def test_missing_password_error_schema(self, client):
        """400 register response matches the AuthErrorResponse schema."""
        response = client.post(
            REGISTER_ENDPOINT,
            data={"email": settings.TEST_EMAIL},
        )

        assert_schema(response, AuthErrorResponse)

    def test_missing_password_error_message(self, client):
        """400 register error contains a non-empty error message."""
        response = client.post(
            REGISTER_ENDPOINT,
            data={"email": settings.TEST_EMAIL},
        )
        model = assert_schema(response, AuthErrorResponse)

        assert model.error.strip(), (
            f"Expected a non-empty error message, got: {model.error!r}"
        )