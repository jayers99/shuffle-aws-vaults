"""Unit tests for PermissionValidator."""

from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError

from shuffle_aws_vaults.infrastructure.permission_validator import (
    PermissionCheckResult,
    PermissionValidator,
)


def test_permission_check_result_creation() -> None:
    """Test creating a permission check result."""
    result = PermissionCheckResult(
        permission="backup:ListBackupVaults",
        granted=True,
    )

    assert result.permission == "backup:ListBackupVaults"
    assert result.granted is True
    assert result.error_message is None


def test_permission_check_result_with_error() -> None:
    """Test creating a permission check result with error."""
    result = PermissionCheckResult(
        permission="backup:ListBackupVaults",
        granted=False,
        error_message="Access denied",
    )

    assert result.permission == "backup:ListBackupVaults"
    assert result.granted is False
    assert result.error_message == "Access denied"


def test_permission_validator_creation() -> None:
    """Test creating a permission validator."""
    validator = PermissionValidator(
        source_account_id="123456789012",
        dest_account_id="222222222222",
    )

    assert validator.source_account_id == "123456789012"
    assert validator.dest_account_id == "222222222222"


def test_check_source_permissions_granted() -> None:
    """Test checking source permissions when granted."""
    validator = PermissionValidator(source_account_id="123456789012")

    # Mock boto3 client
    mock_client = Mock()
    mock_client.list_backup_vaults.return_value = {"BackupVaultList": []}

    with patch.object(validator, "_get_backup_client", return_value=mock_client):
        results = validator.check_source_permissions("us-east-1")

        # Should return 5 results (all source permissions)
        assert len(results) == 5

        # All should be granted
        assert all(r.granted for r in results)

        # First result should be ListBackupVaults
        assert results[0].permission == "backup:ListBackupVaults"
        assert results[0].granted is True


def test_check_source_permissions_access_denied() -> None:
    """Test checking source permissions when access denied."""
    validator = PermissionValidator(source_account_id="123456789012")

    # Mock boto3 client
    mock_client = Mock()
    error_response = {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}
    mock_client.list_backup_vaults.side_effect = ClientError(
        error_response, "list_backup_vaults"
    )

    with patch.object(validator, "_get_backup_client", return_value=mock_client):
        results = validator.check_source_permissions("us-east-1")

        # Should return 5 results
        assert len(results) == 5

        # First result (ListBackupVaults) should be denied
        assert results[0].permission == "backup:ListBackupVaults"
        assert results[0].granted is False
        assert results[0].error_message is not None

        # Other results should be granted (we can't check them without resources)
        assert all(r.granted for r in results[1:])


def test_check_source_permissions_other_error() -> None:
    """Test checking source permissions when other error occurs."""
    validator = PermissionValidator(source_account_id="123456789012")

    # Mock boto3 client
    mock_client = Mock()
    error_response = {"Error": {"Code": "Throttling", "Message": "Rate exceeded"}}
    mock_client.list_backup_vaults.side_effect = ClientError(
        error_response, "list_backup_vaults"
    )

    with patch.object(validator, "_get_backup_client", return_value=mock_client):
        results = validator.check_source_permissions("us-east-1")

        # Should return 5 results
        assert len(results) == 5

        # All should be granted (throttling doesn't mean no permission)
        assert all(r.granted for r in results)


def test_check_dest_permissions() -> None:
    """Test checking destination permissions."""
    validator = PermissionValidator(
        source_account_id="123456789012", dest_account_id="222222222222"
    )

    results = validator.check_dest_permissions("us-east-1")

    # Should return 2 results (dest permissions)
    assert len(results) == 2

    # All should be granted (we mark them as granted since we can't verify)
    assert all(r.granted for r in results)

    # Check permission names
    assert results[0].permission == "backup:CreateBackupVault"
    assert results[1].permission == "backup:PutBackupVaultAccessPolicy"


def test_validate_permissions_all_granted() -> None:
    """Test validating permissions when all granted."""
    validator = PermissionValidator(
        source_account_id="123456789012", dest_account_id="222222222222"
    )

    # Mock boto3 client
    mock_client = Mock()
    mock_client.list_backup_vaults.return_value = {"BackupVaultList": []}

    with patch.object(validator, "_get_backup_client", return_value=mock_client):
        all_granted, results = validator.validate_permissions("us-east-1")

        # All should be granted
        assert all_granted is True

        # Should have 7 results (5 source + 2 dest)
        assert len(results) == 7


def test_validate_permissions_some_denied() -> None:
    """Test validating permissions when some denied."""
    validator = PermissionValidator(source_account_id="123456789012")

    # Mock boto3 client
    mock_client = Mock()
    error_response = {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}
    mock_client.list_backup_vaults.side_effect = ClientError(
        error_response, "list_backup_vaults"
    )

    with patch.object(validator, "_get_backup_client", return_value=mock_client):
        all_granted, results = validator.validate_permissions("us-east-1")

        # Not all should be granted
        assert all_granted is False

        # Should have 5 results (source only, no dest account)
        assert len(results) == 5

        # First should be denied
        assert results[0].granted is False


def test_validate_permissions_source_only() -> None:
    """Test validating permissions for source account only."""
    validator = PermissionValidator(source_account_id="123456789012")

    # Mock boto3 client
    mock_client = Mock()
    mock_client.list_backup_vaults.return_value = {"BackupVaultList": []}

    with patch.object(validator, "_get_backup_client", return_value=mock_client):
        all_granted, results = validator.validate_permissions("us-east-1")

        # All should be granted
        assert all_granted is True

        # Should have 5 results (source only)
        assert len(results) == 5
