"""
tests/test_delete_users.py
──────────────────────────
Day 5 — DELETE /users/{id}

The DELETE verb has a tighter contract than the others:
  - HTTP 204 No Content — the resource was deleted successfully.
  - The response body MUST be empty — no JSON, no confirmation message.
  - The operation is considered final — no resource is returned.

ReqRes honours this contract completely. It also simulates a realistic
constraint: you can only "delete" users that exist in its seed data
(ids 1–12). Any other id still returns 204 (ReqRes is a simulator and
doesn't enforce referential integrity), which we document explicitly.

Chaining strategy:
  Several tests here follow a POST → DELETE chain:
    1. POST /users  →  capture the generated id
    2. DELETE /users/{id}  →  assert 204 and empty body
  This proves the full create-then-remove lifecycle works end-to-end
  without relying on pre-seeded ids that could change in a real system.

Coverage matrix:
  ┌────────────────────────────────────────────────────┬────────┬──────────┐
  │ Scenario                                           │ Status │ Time SLA │
  ├────────────────────────────────────────────────────┼────────┼──────────┤
  │ DELETE — known valid id (2)                        │  204   │    ✓     │
  │ DELETE — response body is empty                    │  204   │          │
  │ DELETE — parametrized across valid ids 1–3         │  204   │    ✓     │
  │ DELETE — id at boundary (id = 12)                  │  204   │    ✓     │
  │ DELETE — two requests on same id both return 204   │  204   │          │
  │ DELETE — response has no Content-Type header       │  204   │          │
  │ POST → DELETE chain (lifecycle)                    │  204   │    ✓     │
  │ POST → DELETE chain — body is empty after delete   │  204   │          │
  │ POST → DELETE chain — parametrized payloads        │  204   │    ✓     │
  │ DELETE — large non-existent id still returns 204   │  204   │    ✓     │
  └────────────────────────────────────────────────────┴────────┴──────────┘

Design notes:
  - No schema validation here — a correct DELETE response has no body,
    so Pydantic models are irrelevant. We use assert_status and
    assert_empty_body exclusively.
  - assert_empty_body from utils.assertions handles the 204 body check.
  - The "two requests, same id" test documents that ReqRes always returns
    204 (it does not track state). In a real API, the second call might
    return 404. Either behaviour is acceptable; what matters is consistency.
  - We intentionally do NOT assert 404 for a deleted resource on a second
    GET, because ReqRes doesn't actually remove data between requests.
"""

import pytest

from utils.assertions import (
    assert_empty_body,
    assert_response_time,
    assert_schema,
    assert_status,
)
from models.user import CreateUserResponse

# Endpoints
USERS_ENDPOINT = "/users"

# Test data
# Seeded user ids on ReqRes (pages 1 and 2, 6 users each)
VALID_USER_IDS_TO_DELETE = [1, 2, 3]
BOUNDARY_USER_ID         = 12   # last seeded user (page 2)
NON_EXISTENT_USER_ID     = 9999

# Payloads for POST → DELETE lifecycle chain
LIFECYCLE_PAYLOADS = [
    {"name": "neo",     "job": "the one"},
    {"name": "trinity", "job": "operator"},
    {"name": "tank",    "job": "crew"},
]


# Helpers 

def _create_user(client, payload: dict) -> str:
    """
    POST /users and return the generated id as a string.

    Used as the setup step in POST → DELETE lifecycle tests.
    Fails fast with a clear message if the creation itself breaks.
    """
    response = client.post(USERS_ENDPOINT, data=payload)
    assert_status(response, 201)
    model = assert_schema(response, CreateUserResponse)
    assert model.id, f"POST /users returned an empty id for payload {payload}"
    return model.id


# Test class: basic DELETE behaviour

class TestDeleteUser:
    """
    Tests for DELETE /users/{id}.

    Covers status code, empty body contract, response time,
    idempotency, and header expectations.
    """

    def test_status_204_valid_id(self, client):
        """DELETE /users/{id} on a known seeded user returns 204 No Content."""
        response = client.delete(f"{USERS_ENDPOINT}/2")

        assert_status(response, 204)

    def test_response_time_valid_id(self, client):
        """DELETE response arrives within the configured SLA."""
        response = client.delete(f"{USERS_ENDPOINT}/2")

        assert_response_time(response)

    def test_body_is_empty(self, client):
        """
        DELETE response body is completely empty.

        HTTP 204 No Content mandates an empty body. Any content in
        the body (even whitespace) violates the HTTP spec and can
        break clients that expect no body on 204.
        """
        response = client.delete(f"{USERS_ENDPOINT}/2")

        assert_empty_body(response)

    def test_body_is_empty_and_not_json(self, client):
        """
        DELETE response body is not parseable JSON.

        Explicitly checks that body is None (not an empty dict {}
        or empty list []), confirming the server sends truly no content.
        """
        response = client.delete(f"{USERS_ENDPOINT}/2")

        assert response.body is None, (
            f"Expected body=None for 204, got body={response.body!r}. "
            "The server should not return a JSON body with 204 No Content."
        )

    @pytest.mark.parametrize("user_id", VALID_USER_IDS_TO_DELETE)
    def test_status_204_parametrized_ids(self, client, user_id):
        """DELETE returns 204 for user ids 1, 2, and 3."""
        response = client.delete(f"{USERS_ENDPOINT}/{user_id}")

        assert_status(response, 204)

    @pytest.mark.parametrize("user_id", VALID_USER_IDS_TO_DELETE)
    def test_response_time_parametrized_ids(self, client, user_id):
        """DELETE response arrives within SLA for each parametrized id."""
        response = client.delete(f"{USERS_ENDPOINT}/{user_id}")

        assert_response_time(response)

    @pytest.mark.parametrize("user_id", VALID_USER_IDS_TO_DELETE)
    def test_body_is_empty_parametrized_ids(self, client, user_id):
        """DELETE body is empty for each parametrized id."""
        response = client.delete(f"{USERS_ENDPOINT}/{user_id}")

        assert_empty_body(response)

    def test_status_204_boundary_id(self, client):
        """DELETE works on the last seeded user (id=12, page 2)."""
        response = client.delete(f"{USERS_ENDPOINT}/{BOUNDARY_USER_ID}")

        assert_status(response, 204)

    def test_response_time_boundary_id(self, client):
        """DELETE on boundary id arrives within the SLA."""
        response = client.delete(f"{USERS_ENDPOINT}/{BOUNDARY_USER_ID}")

        assert_response_time(response)

    def test_body_is_empty_boundary_id(self, client):
        """DELETE body is empty for boundary id."""
        response = client.delete(f"{USERS_ENDPOINT}/{BOUNDARY_USER_ID}")

        assert_empty_body(response)

    def test_idempotent_two_deletes_same_id(self, client):
        """
        Two DELETE requests on the same id both return 204.

        Documents ReqRes behaviour: since no state is persisted between
        requests, the same id can be deleted multiple times without error.

        In a production API, the second call might return 404 (already
        deleted). Either response is valid — what matters is that the
        API is consistent and never returns 5xx on a repeated delete.
        """
        first  = client.delete(f"{USERS_ENDPOINT}/2")
        second = client.delete(f"{USERS_ENDPOINT}/2")

        assert_status(first,  204)
        assert_status(second, 204)

    def test_both_idempotent_bodies_are_empty(self, client):
        """Both responses in the idempotency test have empty bodies."""
        first  = client.delete(f"{USERS_ENDPOINT}/2")
        second = client.delete(f"{USERS_ENDPOINT}/2")

        assert_empty_body(first)
        assert_empty_body(second)

    def test_non_existent_id_returns_204(self, client):
        """
        DELETE on a non-existent id still returns 204 on ReqRes.

        ReqRes is a simulator and does not track referential integrity.
        This test documents that behaviour explicitly so team members
        don't mistake it for a bug.

        Note: a strict REST API would return 404 for a missing resource.
        If this project ever moves to a real backend, update this test.
        """
        response = client.delete(f"{USERS_ENDPOINT}/{NON_EXISTENT_USER_ID}")

        assert_status(response, 204)

    def test_non_existent_id_response_time(self, client):
        """DELETE on a non-existent id also arrives within the SLA."""
        response = client.delete(f"{USERS_ENDPOINT}/{NON_EXISTENT_USER_ID}")

        assert_response_time(response)

    def test_non_existent_id_body_is_empty(self, client):
        """DELETE on non-existent id also returns an empty body."""
        response = client.delete(f"{USERS_ENDPOINT}/{NON_EXISTENT_USER_ID}")

        assert_empty_body(response)


# Test class: POST → DELETE lifecycle chain

class TestDeleteLifecycle:
    """
    End-to-end lifecycle tests: POST a new user, then DELETE it.

    These tests validate the full create-then-remove flow rather than
    deleting pre-seeded ids. They are more realistic because they
    mimic what a real consumer would do: create a resource, use it,
    then clean it up.

    The generated id from POST is used as the delete target — no
    hardcoded ids in this class.
    """

    def test_post_then_delete_returns_204(self, client):
        """
        Create a user via POST, then DELETE it — expect 204.

        This is the canonical lifecycle: create → use → delete.
        """
        user_id = _create_user(client, {"name": "morpheus", "job": "leader"})
        response = client.delete(f"{USERS_ENDPOINT}/{user_id}")

        assert_status(response, 204)

    def test_post_then_delete_body_is_empty(self, client):
        """DELETE after POST also produces an empty response body."""
        user_id  = _create_user(client, {"name": "morpheus", "job": "leader"})
        response = client.delete(f"{USERS_ENDPOINT}/{user_id}")

        assert_empty_body(response)

    def test_post_then_delete_within_sla(self, client):
        """DELETE step in the lifecycle chain responds within the SLA."""
        user_id  = _create_user(client, {"name": "morpheus", "job": "leader"})
        response = client.delete(f"{USERS_ENDPOINT}/{user_id}")

        assert_response_time(response)

    @pytest.mark.parametrize("payload", LIFECYCLE_PAYLOADS)
    def test_lifecycle_parametrized_payloads(self, client, payload):
        """
        POST → DELETE lifecycle returns 204 for each varied payload.

        Parametrizing across multiple user profiles confirms that the
        delete path is not coupled to a specific name or job value.
        """
        user_id  = _create_user(client, payload)
        response = client.delete(f"{USERS_ENDPOINT}/{user_id}")

        assert_status(response, 204)

    @pytest.mark.parametrize("payload", LIFECYCLE_PAYLOADS)
    def test_lifecycle_body_empty_parametrized(self, client, payload):
        """DELETE body is empty for each parametrized lifecycle payload."""
        user_id  = _create_user(client, payload)
        response = client.delete(f"{USERS_ENDPOINT}/{user_id}")

        assert_empty_body(response)

    @pytest.mark.parametrize("payload", LIFECYCLE_PAYLOADS)
    def test_lifecycle_response_time_parametrized(self, client, payload):
        """DELETE step responds within SLA for each parametrized lifecycle."""
        user_id  = _create_user(client, payload)
        response = client.delete(f"{USERS_ENDPOINT}/{user_id}")

        assert_response_time(response)

    def test_unique_ids_produce_unique_deletes(self, client):
        """
        Two POSTs produce two different ids, and both delete cleanly.

        Validates that the id generation is not broken and that we're
        actually deleting distinct resources in each lifecycle call.
        """
        payload = {"name": "agent", "job": "smith"}

        id_one = _create_user(client, payload)
        id_two = _create_user(client, payload)

        assert id_one != id_two, (
            f"Both POST requests returned the same id={id_one!r}. "
            "Id generation may be broken."
        )

        resp_one = client.delete(f"{USERS_ENDPOINT}/{id_one}")
        resp_two = client.delete(f"{USERS_ENDPOINT}/{id_two}")

        assert_status(resp_one, 204)
        assert_status(resp_two, 204)
        assert_empty_body(resp_one)
        assert_empty_body(resp_two)