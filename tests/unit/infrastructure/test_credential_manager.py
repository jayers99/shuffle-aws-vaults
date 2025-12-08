"""Unit tests for CredentialManager."""

from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError

from shuffle_aws_vaults.infrastructure.credential_manager import CredentialManager


def test_credential_manager_creation() -> None:
    """Test creating a credential manager."""
    manager = CredentialManager()

    assert manager._auth_failure_count == 0
    assert len(manager._sessions) == 0


def test_get_session() -> None:
    """Test getting a session."""
    manager = CredentialManager()

    # First call should create session
    session1 = manager.get_session("us-east-1")
    assert session1 is not None
    assert "us-east-1" in manager._sessions

    # Second call should return cached session
    session2 = manager.get_session("us-east-1")
    assert session1 is session2


def test_clear_sessions() -> None:
    """Test clearing sessions."""
    manager = CredentialManager()

    # Create some sessions
    manager.get_session("us-east-1")
    manager.get_session("us-west-2")
    assert len(manager._sessions) == 2

    # Clear sessions
    manager.clear_sessions()
    assert len(manager._sessions) == 0


def test_is_credential_error() -> None:
    """Test detecting credential errors."""
    manager = CredentialManager()

    # ExpiredToken error
    error1 = ClientError(
        {"Error": {"Code": "ExpiredToken", "Message": "Token expired"}},
        "operation",
    )
    assert manager._is_credential_error(error1) is True

    # ExpiredTokenException error
    error2 = ClientError(
        {"Error": {"Code": "ExpiredTokenException", "Message": "Token expired"}},
        "operation",
    )
    assert manager._is_credential_error(error2) is True

    # InvalidClientTokenId error
    error3 = ClientError(
        {"Error": {"Code": "InvalidClientTokenId", "Message": "Invalid token"}},
        "operation",
    )
    assert manager._is_credential_error(error3) is True

    # Non-credential error
    error4 = ClientError(
        {"Error": {"Code": "Throttling", "Message": "Rate exceeded"}},
        "operation",
    )
    assert manager._is_credential_error(error4) is False


def test_with_retry_success() -> None:
    """Test with_retry when operation succeeds."""
    manager = CredentialManager()

    mock_func = Mock(return_value="success")
    wrapped = manager.with_retry(mock_func)

    result = wrapped()

    assert result == "success"
    assert mock_func.call_count == 1
    assert manager._auth_failure_count == 0


def test_with_retry_non_credential_error() -> None:
    """Test with_retry when non-credential error occurs."""
    manager = CredentialManager()

    error = ClientError(
        {"Error": {"Code": "Throttling", "Message": "Rate exceeded"}},
        "operation",
    )
    mock_func = Mock(side_effect=error)
    wrapped = manager.with_retry(mock_func)

    with pytest.raises(ClientError):
        wrapped()

    # Should not retry for non-credential errors
    assert mock_func.call_count == 1
    assert manager._auth_failure_count == 0


def test_with_retry_credential_error_then_success() -> None:
    """Test with_retry when credential error occurs then succeeds."""
    manager = CredentialManager()

    error = ClientError(
        {"Error": {"Code": "ExpiredToken", "Message": "Token expired"}},
        "operation",
    )
    # First call fails, second succeeds
    mock_func = Mock(side_effect=[error, "success"])
    wrapped = manager.with_retry(mock_func)

    result = wrapped()

    assert result == "success"
    assert mock_func.call_count == 2
    assert manager._auth_failure_count == 0  # Reset after success


def test_with_retry_credential_error_exhausted() -> None:
    """Test with_retry when all retries are exhausted."""
    manager = CredentialManager()

    error = ClientError(
        {"Error": {"Code": "ExpiredToken", "Message": "Token expired"}},
        "operation",
    )
    # All retries fail
    mock_func = Mock(side_effect=error)
    wrapped = manager.with_retry(mock_func)

    # Mock user input to avoid blocking
    with patch("builtins.input", return_value=""):
        with pytest.raises(ClientError):
            wrapped()

    # Should have tried multiple times
    assert mock_func.call_count > 1


def test_with_retry_max_auth_failures() -> None:
    """Test with_retry when max auth failures is reached."""
    manager = CredentialManager()
    manager._auth_failure_count = CredentialManager.MAX_AUTH_FAILURES - 1

    error = ClientError(
        {"Error": {"Code": "ExpiredToken", "Message": "Token expired"}},
        "operation",
    )
    mock_func = Mock(side_effect=error)
    wrapped = manager.with_retry(mock_func)

    # Mock user input to avoid blocking
    with patch("builtins.input", return_value=""):
        with pytest.raises((ClientError, RuntimeError)):
            wrapped()

    # After exhausting retries, function should have been called multiple times
    assert mock_func.call_count > 1


def test_with_retry_clears_sessions() -> None:
    """Test that with_retry clears sessions on credential error."""
    manager = CredentialManager()

    # Create a session
    manager.get_session("us-east-1")
    assert len(manager._sessions) == 1

    error = ClientError(
        {"Error": {"Code": "ExpiredToken", "Message": "Token expired"}},
        "operation",
    )
    # First call fails, second succeeds
    mock_func = Mock(side_effect=[error, "success"])
    wrapped = manager.with_retry(mock_func)

    result = wrapped()

    assert result == "success"
    # Sessions should have been cleared
    assert len(manager._sessions) == 0


def test_wait_for_user_refresh_keyboard_interrupt() -> None:
    """Test that wait_for_user_refresh handles KeyboardInterrupt."""
    manager = CredentialManager()

    with patch("builtins.input", side_effect=KeyboardInterrupt()):
        with pytest.raises(SystemExit):
            manager._wait_for_user_refresh()
