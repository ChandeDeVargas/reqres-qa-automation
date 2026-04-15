"""
tests/test_get_users.py
───────────────────────
Day 2 — GET /users and GET /users/{id}

Coverage matrix:
  ┌─────────────────────────────────────────┬────────┬────────┬──────────┐
  │ Scenario                                │ Status │ Schema │ Time SLA │
  ├─────────────────────────────────────────┼────────┼────────┼──────────┤
  │ List users — default (page 1)           │  200   │   ✓    │    ✓     │
  │ List users — page 2                     │  200   │   ✓    │    ✓     │
  │ List users — parametrized pages 1 & 2  │  200   │   ✓    │    ✓     │
  │ List users — pagination fields correct  │  200   │   ✓    │          │
  │ List users — per_page matches data len  │  200   │   ✓    │          │
  │ Single user — valid id (1..6)           │  200   │   ✓    │    ✓     │
  │ Single user — all fields populated      │  200   │   ✓    │          │
  │ Single user — id = 12 (page 2)          │  200   │   ✓    │    ✓     │
  │ Single user — not found (id = 999)      │  404   │        │    ✓     │
  │ Single user — not found body is empty   │  404   │        │          │
  └─────────────────────────────────────────┴────────┴────────┴──────────┘

Design decisions:
  - @pytest.mark.parametrize drives data-driven cases without code duplication.
  - All test methods receive `client` from conftest — no setup/teardown needed.
  - Assertions delegate to utils.assertions helpers for consistent error messages.
  - No hardcoded waits; Playwright's timeout (REQUEST_TIMEOUT_MS) handles it.
"""

import pytest

from models.user import UserListResponse, SingleUserResponse
from utils.assertions import (
    assert_status,
    assert_response_time,
    assert_schema,
    assert_field_present,
)


# ── Constants ─────────────────────────────────────────────────────────────────
# Keep endpoint strings here, not scattered across test bodies.
USERS_ENDPOINT = "/users"

# ReqRes has 12 seeded users across 2 pages (6 per page).
VALID_USER_IDS = [1, 2, 3, 4, 5, 6]
VALID_PAGES = [1, 2]
NON_EXISTENT_USER_ID = 999


# ── Test class: list endpoint ─────────────────────────────────────────────────

class TestGetUsersList:
    """Tests for GET /users — the paginated list endpoint."""

    def test_status_200_default_page(self, client):
        """GET /users with no params returns 200 OK."""
        response = client.get(USERS_ENDPOINT)

        assert_status(response, 200)

    def test_response_time_default_page(self, client):
        """Default page response arrives within the SLA."""
        response = client.get(USERS_ENDPOINT)

        assert_response_time(response)

    def test_schema_default_page(self, client):
        """Default page response matches the UserListResponse schema."""
        response = client.get(USERS_ENDPOINT)

        assert_schema(response, UserListResponse)

    @pytest.mark.parametrize("page", VALID_PAGES)
    def test_status_200_parametrized_pages(self, client, page):
        """GET /users?page={n} returns 200 for each valid page."""
        response = client.get(USERS_ENDPOINT, params={"page": page})

        assert_status(response, 200)

    @pytest.mark.parametrize("page", VALID_PAGES)
    def test_schema_parametrized_pages(self, client, page):
        """Each page response matches the UserListResponse schema."""
        response = client.get(USERS_ENDPOINT, params={"page": page})

        assert_schema(response, UserListResponse)

    @pytest.mark.parametrize("page", VALID_PAGES)
    def test_response_time_parametrized_pages(self, client, page):
        """Each page response arrives within the SLA."""
        response = client.get(USERS_ENDPOINT, params={"page": page})

        assert_response_time(response)

    def test_pagination_fields_are_correct(self, client):
        """
        Pagination metadata is internally consistent.

        Validates: page number matches request, total_pages is calculable
        from total and per_page, and the data array is non-empty.
        """
        response = client.get(USERS_ENDPOINT, params={"page": 1})
        model = assert_schema(response, UserListResponse)

        assert model.page == 1, f"Expected page=1, got page={model.page}"
        assert model.per_page > 0, "per_page must be a positive integer"
        assert model.total > 0, "total must be a positive integer"
        assert model.total_pages > 0, "total_pages must be a positive integer"

        expected_total_pages = -(-model.total // model.per_page)  # ceiling division
        assert model.total_pages == expected_total_pages, (
            f"total_pages={model.total_pages} does not match "
            f"ceil(total/per_page) = ceil({model.total}/{model.per_page}) = {expected_total_pages}"
        )

    def test_data_length_matches_per_page(self, client):
        """
        Number of users in `data` equals `per_page` on a full page.

        Page 1 is always full on ReqRes (6 users, per_page=6).
        """
        response = client.get(USERS_ENDPOINT, params={"page": 1})
        model = assert_schema(response, UserListResponse)

        assert len(model.data) == model.per_page, (
            f"Expected {model.per_page} users in data, got {len(model.data)}"
        )

    def test_page_2_has_different_users_than_page_1(self, client):
        """
        Users on page 2 are distinct from users on page 1.

        Catches bugs where pagination params are ignored and the same
        page is returned regardless of the query parameter.
        """
        page1 = assert_schema(
            client.get(USERS_ENDPOINT, params={"page": 1}), UserListResponse
        )
        page2 = assert_schema(
            client.get(USERS_ENDPOINT, params={"page": 2}), UserListResponse
        )

        ids_page1 = {u.id for u in page1.data}
        ids_page2 = {u.id for u in page2.data}

        assert ids_page1.isdisjoint(ids_page2), (
            f"Pages 1 and 2 share user ids: {ids_page1 & ids_page2}. "
            "Pagination may be broken."
        )

    def test_user_fields_are_populated(self, client):
        """
        Every user in the list has non-empty string fields.

        Guards against the API returning null or empty values for
        first_name, last_name, email, or avatar.
        """
        response = client.get(USERS_ENDPOINT, params={"page": 1})
        model = assert_schema(response, UserListResponse)

        for user in model.data:
            assert user.first_name.strip(), f"User id={user.id} has empty first_name"
            assert user.last_name.strip(), f"User id={user.id} has empty last_name"
            assert user.email.strip(), f"User id={user.id} has empty email"
            assert user.avatar.strip(), f"User id={user.id} has empty avatar"

    def test_support_block_is_present(self, client):
        """
        The `support` block exists and has non-empty url and text.

        ReqRes includes a support object in every response — validating
        it ensures we're parsing the full contract, not just the data.
        """
        response = client.get(USERS_ENDPOINT)
        model = assert_schema(response, UserListResponse)

        assert model.support.url.startswith("http"), (
            f"support.url does not look like a URL: {model.support.url!r}"
        )
        assert model.support.text.strip(), "support.text must not be empty"

    def test_response_contains_required_top_level_keys(self, client):
        """
        Raw response body has all expected top-level keys.

        Complements schema validation — catches extra/missing keys
        that Pydantic might silently ignore.
        """
        response = client.get(USERS_ENDPOINT)

        assert_field_present(
            response, "page", "per_page", "total", "total_pages", "data", "support"
        )


# ── Test class: single user endpoint ─────────────────────────────────────────

class TestGetSingleUser:
    """Tests for GET /users/{id} — the single-resource endpoint."""

    @pytest.mark.parametrize("user_id", VALID_USER_IDS)
    def test_status_200_valid_ids(self, client, user_id):
        """GET /users/{id} returns 200 for each seeded user id."""
        response = client.get(f"{USERS_ENDPOINT}/{user_id}")

        assert_status(response, 200)

    @pytest.mark.parametrize("user_id", VALID_USER_IDS)
    def test_schema_valid_ids(self, client, user_id):
        """Each valid user response matches the SingleUserResponse schema."""
        response = client.get(f"{USERS_ENDPOINT}/{user_id}")

        assert_schema(response, SingleUserResponse)

    @pytest.mark.parametrize("user_id", VALID_USER_IDS)
    def test_response_time_valid_ids(self, client, user_id):
        """Each single-user response arrives within the SLA."""
        response = client.get(f"{USERS_ENDPOINT}/{user_id}")

        assert_response_time(response)

    def test_returned_id_matches_requested_id(self, client):
        """
        The `id` field in the response matches the id in the URL.

        Catches routing bugs where the wrong user record is returned.
        """
        target_id = 2
        response = client.get(f"{USERS_ENDPOINT}/{target_id}")
        model = assert_schema(response, SingleUserResponse)

        assert model.data.id == target_id, (
            f"Requested user id={target_id} but got id={model.data.id} in response"
        )

    def test_all_user_fields_are_populated(self, client):
        """
        The user object in the response has no empty or null fields.
        """
        response = client.get(f"{USERS_ENDPOINT}/1")
        model = assert_schema(response, SingleUserResponse)

        user = model.data
        assert user.id > 0
        assert user.first_name.strip()
        assert user.last_name.strip()
        assert "@" in user.email
        assert user.avatar.strip()

    def test_user_id_12_is_on_page_2(self, client):
        """
        User id=12 (last user, page 2) is retrievable directly.

        Validates that the single-user endpoint works for both pages,
        not just for the first page of users.
        """
        response = client.get(f"{USERS_ENDPOINT}/12")

        assert_status(response, 200)
        assert_response_time(response)
        model = assert_schema(response, SingleUserResponse)
        assert model.data.id == 12

    def test_not_found_returns_404(self, client):
        """GET /users/{non_existent_id} returns 404 Not Found."""
        response = client.get(f"{USERS_ENDPOINT}/{NON_EXISTENT_USER_ID}")

        assert_status(response, 404)

    def test_not_found_response_time_within_sla(self, client):
        """404 response also arrives within the SLA — errors must be fast."""
        response = client.get(f"{USERS_ENDPOINT}/{NON_EXISTENT_USER_ID}")

        assert_response_time(response)

    def test_not_found_body_is_empty_object(self, client):
        """
        ReqRes returns {} (empty JSON object) for 404 responses.

        Validates the contract for not-found — consumers should check
        the status code, not rely on a body with an error message.
        """
        response = client.get(f"{USERS_ENDPOINT}/{NON_EXISTENT_USER_ID}")

        assert response.body == {}, (
            f"Expected empty object {{}} for 404, got: {response.body!r}"
        )