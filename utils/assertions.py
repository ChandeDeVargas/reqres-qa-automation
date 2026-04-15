"""
utils/assertions.py
───────────────────
Reusable assertion helpers that keep test code clean and readable.

Instead of repeating the same assertion patterns across every test,
tests call these helpers. Error messages are descriptive so failures
are self-explanatory without needing to read the helper source.
"""

from typing import Type

from pydantic import BaseModel, ValidationError

from clients.api_client import APIResponse
from config import settings

def assert_status(response: APIResponse, expected: int) -> None:
    """Assert HTTP status code with a clear failure message"""
    assert response.status == expected, (
        f"Expected status {expected}, got {response.status}.\n"
        f"Response body: {response.raw_text}"
    )

def assert_response_time(response: APIResponse) -> None:
    """Assert the response arrived within the configured SLA"""
    assert response.elapsed_ms <= settings.MAX_RESPONSE_TIME_MS, (
        f"Response time {response.elapsed_ms:.0f}ms exceeds "
        f"SLA of {settings.MAX_RESPONSE_TIME_MS}ms"
    )

def assert_schema(response: APIResponse, schema: Type[BaseModel]) -> BaseModel:
    """
    Validate response body against a Pydantic schema.

    Returns the validated model instance so tests can access fields
    without re-parsing the body.

    Raises AssertionError with a human-readable diff on failure.
    """
    assert response.body is not None, (
        f"Expected a JSON body to validate against {schema.__name__}, "
        f"but response body is empty. Raw text: {response.raw_text!r}"
    )
    try:
        return schema.model_validate(response.body)
    except ValidationError as exc:
        raise AssertionError(
            f"Response body doesn't match schema {schema.__name__}.\n"
        ) from exc

def assert_body_contains(response: APIResponse, **expected_fields) -> None:
    """
    Assert that specific key-value pairs exist in the response body.

    Usage:
        assert_body_contains(response, name="morpheus", job="leader")
    """
    assert isinstance(response.body, dict), (
        f"Expected a dict body, got {type(response.body).__name__}."
    )
    for key, expected_value in expected_fields.items():
        actual = response.body.get(key)
        assert actual == expected_value, (
            f"Field '{key}': expected {expected_value!r}, got {actual!r}."
        )


def assert_field_present(response: APIResponse, *fields: str) -> None:
    """Assert that all given field names are present in the response body."""
    assert isinstance(response.body, dict), (
        f"Expected a dict body, got {type(response.body).__name__}."
    )
    for field in fields:
        assert field in response.body, (
            f"Expected field '{field}' to be present in response body.\n"
            f"Available keys: {list(response.body.keys())}"
        )


def assert_empty_body(response: APIResponse) -> None:
    """Assert the response body is empty (used for 204 No Content)."""
    assert not response.raw_text.strip(), (
        f"Expected empty body, got: {response.raw_text!r}"
    )