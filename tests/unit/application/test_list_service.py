"""Unit tests for ListService."""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from shuffle_aws_vaults.application.list_service import ListService
from shuffle_aws_vaults.domain.recovery_point import RecoveryPoint
from shuffle_aws_vaults.domain.vault import Vault


def test_list_all_vaults() -> None:
    """Test listing all vaults."""
    # Arrange
    mock_repo = Mock()
    mock_repo.list_vaults.return_value = [
        Vault(
            name="vault-1",
            arn="arn:aws:backup:us-east-1:123456789012:backup-vault:vault-1",
            region="us-east-1",
            account_id="123456789012",
            recovery_point_count=5,
        ),
        Vault(
            name="vault-2",
            arn="arn:aws:backup:us-east-1:123456789012:backup-vault:vault-2",
            region="us-east-1",
            account_id="123456789012",
            recovery_point_count=10,
        ),
    ]

    service = ListService(mock_repo, dry_run=False)

    # Act
    vaults = service.list_all_vaults("us-east-1")

    # Assert
    assert len(vaults) == 2
    assert vaults[0].name == "vault-1"
    assert vaults[1].name == "vault-2"
    mock_repo.list_vaults.assert_called_once_with("us-east-1")


def test_list_all_vaults_sorted_by_name() -> None:
    """Test that vaults are sorted by name."""
    # Arrange
    mock_repo = Mock()
    mock_repo.list_vaults.return_value = [
        Vault(
            name="zebra-vault",
            arn="arn:aws:backup:us-east-1:123456789012:backup-vault:zebra-vault",
            region="us-east-1",
            account_id="123456789012",
        ),
        Vault(
            name="alpha-vault",
            arn="arn:aws:backup:us-east-1:123456789012:backup-vault:alpha-vault",
            region="us-east-1",
            account_id="123456789012",
        ),
    ]

    service = ListService(mock_repo, dry_run=False)

    # Act
    vaults = service.list_all_vaults("us-east-1")

    # Assert
    assert vaults[0].name == "alpha-vault"
    assert vaults[1].name == "zebra-vault"


def test_list_vault_recovery_points() -> None:
    """Test listing recovery points in a vault."""
    # Arrange
    mock_repo = Mock()
    recovery_points = [
        RecoveryPoint(
            recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-1",
            backup_vault_name="test-vault",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-1",
            resource_type="EBS",
            creation_date=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            completion_date=datetime(2025, 1, 1, 13, 0, 0, tzinfo=timezone.utc),
            status="COMPLETED",
            size_bytes=10 * 1024**3,
            backup_job_id="job-1",
        ),
        RecoveryPoint(
            recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-2",
            backup_vault_name="test-vault",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-2",
            resource_type="EBS",
            creation_date=datetime(2025, 1, 2, 12, 0, 0, tzinfo=timezone.utc),
            completion_date=datetime(2025, 1, 2, 13, 0, 0, tzinfo=timezone.utc),
            status="COMPLETED",
            size_bytes=20 * 1024**3,
            backup_job_id="job-2",
        ),
    ]
    mock_repo.list_recovery_points.return_value = recovery_points

    service = ListService(mock_repo, dry_run=False)

    # Act
    result = service.list_vault_recovery_points("test-vault", "us-east-1")

    # Assert
    assert len(result) == 2
    # Should be sorted by creation date descending (newest first)
    assert result[0].creation_date > result[1].creation_date
    mock_repo.list_recovery_points.assert_called_once_with("test-vault", "us-east-1")


def test_get_vault_summary() -> None:
    """Test getting vault summary statistics."""
    # Arrange
    mock_repo = Mock()
    mock_repo.list_vaults.return_value = [
        Vault(
            name="vault-1",
            arn="arn:aws:backup:us-east-1:123456789012:backup-vault:vault-1",
            region="us-east-1",
            account_id="123456789012",
            recovery_point_count=5,
            encryption_key_arn="arn:aws:kms:us-east-1:123456789012:key/key-1",
        ),
        Vault(
            name="vault-2",
            arn="arn:aws:backup:us-east-1:123456789012:backup-vault:vault-2",
            region="us-east-1",
            account_id="123456789012",
            recovery_point_count=10,
        ),
        Vault(
            name="vault-3-empty",
            arn="arn:aws:backup:us-east-1:123456789012:backup-vault:vault-3-empty",
            region="us-east-1",
            account_id="123456789012",
            recovery_point_count=0,
        ),
    ]

    service = ListService(mock_repo, dry_run=False)

    # Act
    summary = service.get_vault_summary("us-east-1")

    # Assert
    assert summary["vault_count"] == 3
    assert summary["total_recovery_points"] == 15
    assert summary["encrypted_vaults"] == 1
    assert summary["empty_vaults"] == 1


def test_list_dry_run_mode() -> None:
    """Test that dry-run mode returns empty results."""
    # Arrange
    mock_repo = Mock()
    service = ListService(mock_repo, dry_run=True)

    # Act
    vaults = service.list_all_vaults("us-east-1")
    recovery_points = service.list_vault_recovery_points("test-vault", "us-east-1")

    # Assert
    assert len(vaults) == 0
    assert len(recovery_points) == 0
    mock_repo.list_vaults.assert_not_called()
    mock_repo.list_recovery_points.assert_not_called()
