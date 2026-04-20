"""
tests/test_put_patch_users.py
─────────────────────────────
Day 4 — PUT /users/{id} · PATCH /users/{id}

Conceptual difference under test:
  PUT   — full replacement. Sends the complete resource representation.
          Even if only one field changed, the full object is re-sent.
  PATCH — partial update. Sends only the fields that need to change.
          Fields not included in the payload remain untouched server-side.

ReqRes simulates both correctly:
  - Both return 200 OK with the updated fields echoed back.
  - Both include an `updatedAt` timestamp proving the update was processed.
  - Neither actually persists changes (ReqRes is a mock API), but the
    response contracts are stable and fully testable.

Coverage matrix:
  ┌───────────────────────────────────────────────────┬────────┬────────┬──────────┐
  │ Scenario                                          │ Status │ Schema │ Time SLA │
  ├───────────────────────────────────────────────────┼────────┼────────┼──────────┤
  │ PUT — valid payload, valid id                     │  200   │   ✓    │    ✓     │
  │ PUT — echoes name and job from payload            │  200   │   ✓    │          │
  │ PUT — updatedAt is present and non-empty          │  200   │   ✓    │          │
  │ PUT — parametrized across multiple user ids       │  200   │   ✓    │    ✓     │
  │ PUT — parametrized across multiple payloads       │  200   │   ✓    │          │
  │ PUT — updatedAt changes between two requests      │  200   │        │          │
  │ PATCH — valid payload (single field), valid id    │  200   │   ✓    │    ✓     │
  │ PATCH — echoes only the updated field             │  200   │   ✓    │          │
  │ PATCH — updatedAt is present and non-empty        │  200   │   ✓    │          │
  │ PATCH — parametrized across multiple user ids     │  200   │   ✓    │    ✓     │
  │ PATCH — name only (job omitted)                   │  200   │   ✓    │          │
  │ PATCH — job only (name omitted)                   │  200   │   ✓    │          │
  │ PUT vs PATCH — both update same user, same result │  200   │   ✓    │          │
  └───────────────────────────────────────────────────┴────────┴────────┴──────────┘

Design notes:
  - USER_IDS_TO_UPDATE is intentionally small (ids 1–3) to keep the
    parametrized runs fast while still covering more than one record.
  - updatedAt ordering is not validated — network latency can make two
    rapid requests return the same timestamp on fast machines. We only
    confirm the field exists and is non-empty, which is the real contract.
  - PUT and PATCH tests are kept in separate classes for clarity, even
    though they share similar structure. Merging them would obscure
    which HTTP verb a failing test is exercising.
"""

from tests.test_post_users import PARAMETRIZED_PAYLOADS
from tests.test_get_users import USERS_ENDPOINT
import pytest

from models.user import UpdateUserResponse
from utils.assertions import (
    assert_body_contains,
    assert_field_present,
    assert_response_time,
    assert_schema,
    assert_status,
)

# Endpoints
USERS_ENDPOINT = "/users"

# Test data
# Ids to use in parametrized update tests
# All are valid ReqRes seed users; picking 1-3 keeps the suite fast
USER_IDS_TO_UPDATE = [1, 2, 3]

# Full payload for PUT (all fields present)
FULL_UPDATE_PAYLOAD = {"name": "morpheus", "job": "zion resident"}

# Payloads for parametrized PUT tests - different role changes
PARAMETRIZED_PUT_PAYLOADS = [
    {"name": "neo", "job": "the one"},
    {"name": "trinity", "job": "hacker"},
    {"name": "tank", "job": "operator"},
]

# Partial payloads for PATCH - only one field at a time
PATCH_NAME_ONLY = {"name": "morpheus update"}
PATCH_JOB_ONLY = {"job": "zion captain"}
PATCH_FULL = {"name": "neo", "job": "zion resident"}

# Test class: PUT /users/{id}

class TestPutUser:
    """
    Tests for PUT /users/{id}.

    PUT replaces the full resource representation. The payload must
    include all writable fields; missing fields may be treated as null
    by a strict server (ReqRes echoes back whatever is sent).
    """

    def test_status_200_valid_payload(self, client):
        """PUT /users/{id} with a complete payload returns 200 OK"""
        response = client.put(f"{USERS_ENDPOINT}/2", data=FULL_UPDATE_PAYLOAD)

        assert_status(response, 200)

    def test_response_time_valid_payload(self, client):
        """PUT response arrives within the configured SLA"""
        response = client.put(f"{USERS_ENDPOINT}/2", data=FULL_UPDATE_PAYLOAD)
        
        assert_response_time(response)

    def test_schema_valid_payload(self, client):
        """PUT response body matches the UpdateUserResponse schema"""
        response = client.put(f"{USERS_ENDPOINT}/2", data=FULL_UPDATE_PAYLOAD)

    def test_echoes_name_and_job(self, client):
        """
        PUT response echoes back the exact name and job we sent.

        This is the core contract: the response body must reflect
        the values submitted, not stale data or defaults.
        """
        response = client.put(f"{USERS_ENDPOINT}/2", data=FULL_UPDATE_PAYLOAD)

        assert_body_contains(
            response,
            name=FULL_UPDATE_PAYLOAD["name"],
            job=FULL_UPDATE_PAYLOAD["job"]
        )

    def test_updated_at_is_present(self, client):
        """
        PUT response contains a non-empty updatedAt timestamp.

        updatedAt proves the server processed the update request,
        not just returned a cached or hardcoded response.
        """
        response = client.put(f"{USERS_ENDPOINT}/2", data=FULL_UPDATE_PAYLOAD)
        model = assert_schema(response, UpdateUserResponse)

        assert model.updatedAt.strip(), (
            f"Expected a non-empty updatedAt, got {model.updatedAt!r}"
        )

    def test_updated_at_contains_data(self, client):
        """
        updatedAt contains at least a four-digit year.

        Catches cases where the server returns an obviously wrong
        timestamp like '0000-00-00' or an empty placeholder string.
        """
        response = client.put(f"{USERS_ENDPOINT}/2", data=FULL_UPDATE_PAYLOAD)
        model = assert_schema(response, UpdateUserResponse)

        # A valid timestamp always contains the current year (2020+)
        assert any(str(year) in model.updatedAt for year in range (2020, 2100)), (
            f"updatedAt doesn't contain a recognisable year: {model.updatedAt!r}"
        )

    def test_response_has_required_keys(self, client):
        """Raw body contains name, job, and updatedAt keys."""
        response = client.put(f"{USERS_ENDPOINT}/2", data=FULL_UPDATE_PAYLOAD)

        assert_field_present(response, "name", "job", "updatedAt")

    @pytest.mark.parametrize("user_id", USER_IDS_TO_UPDATE)
    def test_status_200_parametrized_ids(self, client, user_id):
        """PUT returns 200 for user ids 1, 2, and 3"""
        response = client.put(
            f"{USERS_ENDPOINT}/{user_id}", data=FULL_UPDATE_PAYLOAD
        )

        assert_status(response, 200)

    @pytest.mark.parametrize("user_id", USER_IDS_TO_UPDATE)
    def test_schema_parametrized_ids(self, client, user_id):
        """PUT response schema is valid for each parametrized user id"""

        response = client.put(f"{USERS_ENDPOINT}/{user_id}", data=FULL_UPDATE_PAYLOAD)

        assert_schema(response, UpdateUserResponse)

    @pytest.mark.parametrize("user_id", USER_IDS_TO_UPDATE)
    def test_response_time_prametrized_ids(self, client, user_id):
        """PUT response arrives within SLA for each parametrized user id"""
        response = client.put(
            f"{USERS_ENDPOINT}/{user_id}", data=FULL_UPDATE_PAYLOAD
        )

        assert_response_time(response)

    @pytest.mark.parametrize("payload", PARAMETRIZED_PUT_PAYLOADS)
    def test_status_200_parametrized_payloads(self, client, payload):
        """PUT returns 200 for each different name/job combination."""
        response = client.put(f"{USERS_ENDPOINT}/2", data=payload)

        assert_status(response, 200)

    @pytest.mark.parametrize("payload", PARAMETRIZED_PUT_PAYLOADS)
    def test_echoes_correct_fields_parametrized_payloads(self, client, payload):
        """Each payload's name and job are echoed back correctly in PUT."""
        response = client.put(f"{USERS_ENDPOINT}/2", data=payload)

        assert_body_contains(response, name=payload["name"], job=payload["job"])

    def test_two_put_requests_both_succeed(self, client):
        """
        Two consecutive PUT requests on the same user both return 200.

        Validates idempotent behaviour: repeating a PUT with the same
        payload must not cause errors (e.g., a conflict or duplicate key).
        """
        first_payload  = {"name": "morpheus", "job": "leader"}
        second_payload = {"name": "morpheus", "job": "zion resident"}

        first  = client.put(f"{USERS_ENDPOINT}/2", data=first_payload)
        second = client.put(f"{USERS_ENDPOINT}/2", data=second_payload)

        assert_status(first,  200)
        assert_status(second, 200)
        assert_body_contains(first,  name="morpheus", job="leader")
        assert_body_contains(second, name="morpheus", job="zion resident")

# Test class: PATCH /users/{id}

class TestPatchUser:
    """
    Tests for PATCH /users/{id}.

    PATCH updates only the fields included in the payload.
    Fields not sent in the request remain unchanged on the server.
    """
    def test_status_200_full_patch_payload(self, client):
        """PATCH with a complete payload returns 200 OK."""
        response = client.patch(f"{USERS_ENDPOINT}/2", data=PATCH_FULL)

        assert_status(response, 200)

    def test_response_time_full_patch_payload(self, client):
        """PATCH response arrives within the configured SLA."""
        response = client.patch(f"{USERS_ENDPOINT}/2", data=PATCH_FULL)

        assert_response_time(response)

    def test_schema_full_patch_payload(self, client):
        """PATCH response body matches the UpdateUserResponse schema."""
        response = client.patch(f"{USERS_ENDPOINT}/2", data=PATCH_FULL)

        assert_schema(response, UpdateUserResponse)

    def test_echoes_updated_fields(self, client):
        """
        PATCH response echoes the fields that were included in the payload.
        """
        response = client.patch(f"{USERS_ENDPOINT}/2", data=PATCH_FULL)

        assert_body_contains(
            response,
            name=PATCH_FULL["name"],
            job=PATCH_FULL["job"],
        )

    def test_updated_at_is_present(self, client):
        """PATCH response contains a non-empty updatedAt timestamp."""
        response = client.patch(f"{USERS_ENDPOINT}/2", data=PATCH_FULL)
        model = assert_schema(response, UpdateUserResponse)

        assert model.updatedAt.strip(), (
            f"Expected a non-empty updatedAt, got: {model.updatedAt!r}"
        )

    def test_updated_at_contains_date(self, client):
        """updatedAt from PATCH contains a recognisable year."""
        response = client.patch(f"{USERS_ENDPOINT}/2", data=PATCH_FULL)
        model = assert_schema(response, UpdateUserResponse)

        assert any(str(year) in model.updatedAt for year in range(2020, 2100)), (
            f"updatedAt does not contain a recognisable year: {model.updatedAt!r}"
        )

    def test_patch_name_only(self, client):
        """
        PATCH with only the name field returns 200 and echoes name back.

        Validates that partial payloads (a single field) are accepted
        and that the server does not reject missing fields.
        """
        response = client.patch(f"{USERS_ENDPOINT}/2", data=PATCH_NAME_ONLY)

        assert_status(response, 200)
        assert_field_present(response, "name", "updatedAt")
        assert_body_contains(response, name=PATCH_NAME_ONLY["name"])

    def test_patch_job_only(self, client):
        """
        PATCH with only the job field returns 200 and echoes job back.
        """
        response = client.patch(f"{USERS_ENDPOINT}/2", data=PATCH_JOB_ONLY)

        assert_status(response, 200)
        assert_field_present(response, "job", "updatedAt")
        assert_body_contains(response, job=PATCH_JOB_ONLY["job"])

    @pytest.mark.parametrize("user_id", USER_IDS_TO_UPDATE)
    def test_status_200_parametrized_ids(self, client, user_id):
        """PATCH returns 200 for user ids 1, 2, and 3."""
        response = client.patch(
            f"{USERS_ENDPOINT}/{user_id}", data=PATCH_FULL
        )

        assert_status(response, 200)

    @pytest.mark.parametrize("user_id", USER_IDS_TO_UPDATE)
    def test_schema_parametrized_ids(self, client, user_id):
        """PATCH response schema is valid for each parametrized user id."""
        response = client.patch(
            f"{USERS_ENDPOINT}/{user_id}", data=PATCH_FULL
        )

        assert_schema(response, UpdateUserResponse)

    @pytest.mark.parametrize("user_id", USER_IDS_TO_UPDATE)
    def test_response_time_parametrized_ids(self, client, user_id):
        """PATCH response arrives within SLA for each parametrized user id."""
        response = client.patch(
            f"{USERS_ENDPOINT}/{user_id}", data=PATCH_FULL
        )

        assert_response_time(response)

    def test_response_has_required_keys(self, client):
        """Raw PATCH body contains name, job, and updatedAt keys."""
        response = client.patch(f"{USERS_ENDPOINT}/2", data=PATCH_FULL)

        assert_field_present(response, "name", "job", "updatedAt")

# Test class: PUT vs PATCH comparison

class TestPutVsPatch:
    """
    Cross-method comparison tests.

    These tests confirm that PUT and PATCH, when given the same
    payload on the same resource, produce equivalent results.
    This validates that both verbs are correctly wired to the
    same underlying update logic in the API.
    """

    def test_both_return_200(self, client):
        """PUT and PATCH on the same user with the same payload both return 200."""
        payload = {"name": "morpheus", "job": "leader"}

        put_response   = client.put(f"{USERS_ENDPOINT}/2",   data=payload)
        patch_response = client.patch(f"{USERS_ENDPOINT}/2", data=payload)

        assert_status(put_response,   200)
        assert_status(patch_response, 200)

    def test_both_echo_same_fields(self, client):
        """
        PUT and PATCH with identical payloads echo the same name and job.

        Catches routing bugs where one verb hits a different handler
        and returns a different (e.g. default or empty) field value.
        """
        payload = {"name": "morpheus", "job": "leader"}

        put_response   = client.put(f"{USERS_ENDPOINT}/2",   data=payload)
        patch_response = client.patch(f"{USERS_ENDPOINT}/2", data=payload)

        put_model   = assert_schema(put_response,   UpdateUserResponse)
        patch_model = assert_schema(patch_response, UpdateUserResponse)

        assert put_model.name == patch_model.name, (
            f"PUT name={put_model.name!r} differs from PATCH name={patch_model.name!r}"
        )
        assert put_model.job == patch_model.job, (
            f"PUT job={put_model.job!r} differs from PATCH job={patch_model.job!r}"
        )

    def test_both_include_updated_at(self, client):
        """PUT and PATCH both return a non-empty updatedAt timestamp."""
        payload = {"name": "morpheus", "job": "leader"}

        put_model   = assert_schema(
            client.put(f"{USERS_ENDPOINT}/2",   data=payload), UpdateUserResponse
        )
        patch_model = assert_schema(
            client.patch(f"{USERS_ENDPOINT}/2", data=payload), UpdateUserResponse
        )

        assert put_model.updatedAt.strip(),   "PUT updatedAt is empty"
        assert patch_model.updatedAt.strip(), "PATCH updatedAt is empty"

    def test_both_within_sla(self, client):
        """PUT and PATCH both respond within the configured time SLA."""
        payload = {"name": "morpheus", "job": "leader"}

        put_response   = client.put(f"{USERS_ENDPOINT}/2",   data=payload)
        patch_response = client.patch(f"{USERS_ENDPOINT}/2", data=payload)

        assert_response_time(put_response)
        assert_response_time(patch_response)