"""Unit tests for retry logic."""

import time
from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError

from shuffle_aws_vaults.infrastructure.retry import is_transient_error, with_retry


def test_is_transient_error_throttling() -> None:
    """Test that throttling errors are identified as transient."""
    error = ClientError(
        {"Error": {"Code": "Throttling", "Message": "Rate exceeded"}}, "StartCopyJob"
    )
    assert is_transient_error(error) is True


def test_is_transient_error_service_unavailable() -> None:
    """Test that service unavailable errors are identified as transient."""
    error = ClientError(
        {"Error": {"Code": "ServiceUnavailable", "Message": "Service temporarily unavailable"}},
        "StartCopyJob",
    )
    assert is_transient_error(error) is True


def test_is_transient_error_request_timeout() -> None:
    """Test that timeout errors are identified as transient."""
    error = ClientError(
        {"Error": {"Code": "RequestTimeout", "Message": "Request timed out"}}, "StartCopyJob"
    )
    assert is_transient_error(error) is True


def test_is_transient_error_non_transient() -> None:
    """Test that non-transient errors are not identified as transient."""
    error = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "StartCopyJob"
    )
    assert is_transient_error(error) is False


def test_is_transient_error_non_client_error() -> None:
    """Test that non-ClientError exceptions are not transient."""
    error = ValueError("Invalid value")
    assert is_transient_error(error) is False


def test_with_retry_success_on_first_attempt() -> None:
    """Test that function succeeds on first attempt without retry."""
    mock_func = Mock(return_value="success")

    @with_retry(max_attempts=3)
    def test_func() -> str:
        return mock_func()

    result = test_func()

    assert result == "success"
    assert mock_func.call_count == 1


def test_with_retry_success_on_second_attempt() -> None:
    """Test that function retries and succeeds on second attempt."""
    mock_func = Mock(
        side_effect=[
            ClientError(
                {"Error": {"Code": "Throttling", "Message": "Rate exceeded"}}, "StartCopyJob"
            ),
            "success",
        ]
    )

    @with_retry(max_attempts=3, initial_delay=0.1)
    def test_func() -> str:
        return mock_func()

    result = test_func()

    assert result == "success"
    assert mock_func.call_count == 2


def test_with_retry_fails_after_max_attempts() -> None:
    """Test that function fails after max attempts."""
    error = ClientError(
        {"Error": {"Code": "Throttling", "Message": "Rate exceeded"}}, "StartCopyJob"
    )
    mock_func = Mock(side_effect=error)

    @with_retry(max_attempts=3, initial_delay=0.1)
    def test_func() -> str:
        return mock_func()

    with pytest.raises(ClientError):
        test_func()

    assert mock_func.call_count == 3


def test_with_retry_non_transient_error_no_retry() -> None:
    """Test that non-transient errors are not retried."""
    error = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "StartCopyJob"
    )
    mock_func = Mock(side_effect=error)

    @with_retry(max_attempts=3)
    def test_func() -> str:
        return mock_func()

    with pytest.raises(ClientError):
        test_func()

    # Should fail immediately without retry
    assert mock_func.call_count == 1


def test_with_retry_exponential_backoff() -> None:
    """Test that retry delay increases exponentially."""
    attempts = []

    def track_attempts() -> str:
        attempts.append(time.time())
        if len(attempts) < 3:
            raise ClientError(
                {"Error": {"Code": "Throttling", "Message": "Rate exceeded"}}, "StartCopyJob"
            )
        return "success"

    @with_retry(max_attempts=3, initial_delay=0.1, exponential_base=2.0)
    def test_func() -> str:
        return track_attempts()

    result = test_func()

    assert result == "success"
    assert len(attempts) == 3

    # Check that delays increase (approximately)
    delay1 = attempts[1] - attempts[0]
    delay2 = attempts[2] - attempts[1]

    # Second delay should be roughly 2x the first delay
    assert delay2 > delay1
    assert delay2 / delay1 >= 1.5  # Allow some tolerance


def test_with_retry_max_delay() -> None:
    """Test that retry delay is capped at max_delay."""
    attempts = []

    def track_attempts() -> str:
        attempts.append(time.time())
        if len(attempts) < 3:
            raise ClientError(
                {"Error": {"Code": "Throttling", "Message": "Rate exceeded"}}, "StartCopyJob"
            )
        return "success"

    @with_retry(max_attempts=5, initial_delay=0.5, exponential_base=10.0, max_delay=0.6)
    def test_func() -> str:
        return track_attempts()

    result = test_func()

    assert result == "success"

    # Second delay should be capped at max_delay
    delay2 = attempts[2] - attempts[1]
    assert delay2 <= 0.7  # Allow some tolerance for timing


def test_with_retry_preserves_function_metadata() -> None:
    """Test that decorator preserves function name and docstring."""

    @with_retry(max_attempts=3)
    def test_function() -> str:
        """Test docstring."""
        return "test"

    assert test_function.__name__ == "test_function"
    assert test_function.__doc__ == "Test docstring."
