"""Unit tests for AWSBackupRepository."""

from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch

import pytest

from shuffle_aws_vaults.infrastructure.aws_backup_repository import AWSBackupRepository


def test_list_vaults_with_pagination() -> None:
    """Test that list_vaults handles pagination correctly."""
    # Arrange
    repo = AWSBackupRepository(account_id="123456789012")

    # Mock boto3 client
    mock_client = Mock()
    mock_paginator = Mock()

    # Simulate paginated response (2 pages)
    mock_paginator.paginate.return_value = [
        {
            "BackupVaultList": [
                {
                    "BackupVaultName": "vault-1",
                    "BackupVaultArn": "arn:aws:backup:us-east-1:123456789012:backup-vault:vault-1",
                    "NumberOfRecoveryPoints": 5,
                },
                {
                    "BackupVaultName": "vault-2",
                    "BackupVaultArn": "arn:aws:backup:us-east-1:123456789012:backup-vault:vault-2",
                    "NumberOfRecoveryPoints": 10,
                    "EncryptionKeyArn": "arn:aws:kms:us-east-1:123456789012:key/key-1",
                },
            ]
        },
        {
            "BackupVaultList": [
                {
                    "BackupVaultName": "vault-3",
                    "BackupVaultArn": "arn:aws:backup:us-east-1:123456789012:backup-vault:vault-3",
                    "NumberOfRecoveryPoints": 100,
                },
            ]
        },
    ]

    mock_client.get_paginator.return_value = mock_paginator

    with patch.object(repo, "_get_backup_client", return_value=mock_client):
        # Act
        vaults = repo.list_vaults("us-east-1")

        # Assert
        assert len(vaults) == 3
        assert vaults[0].name == "vault-1"
        assert vaults[1].name == "vault-2"
        assert vaults[2].name == "vault-3"
        assert vaults[2].recovery_point_count == 100

        mock_client.get_paginator.assert_called_once_with("list_backup_vaults")
        mock_paginator.paginate.assert_called_once()


def test_list_recovery_points_with_pagination() -> None:
    """Test that list_recovery_points handles pagination correctly."""
    # Arrange
    repo = AWSBackupRepository(account_id="123456789012")

    # Mock boto3 client
    mock_client = Mock()
    mock_paginator = Mock()

    # Simulate paginated response (2 pages)
    creation_date = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    completion_date = datetime(2025, 1, 1, 13, 0, 0, tzinfo=timezone.utc)

    mock_paginator.paginate.return_value = [
        {
            "RecoveryPoints": [
                {
                    "RecoveryPointArn": "arn:aws:backup:us-east-1:123456789012:recovery-point:rp-1",
                    "ResourceArn": "arn:aws:ec2:us-east-1:123456789012:volume/vol-1",
                    "ResourceType": "EBS",
                    "CreationDate": creation_date,
                    "CompletionDate": completion_date,
                    "Status": "COMPLETED",
                    "BackupSizeInBytes": 10 * 1024**3,
                    "BackupJobId": "job-1",
                },
            ]
        },
        {
            "RecoveryPoints": [
                {
                    "RecoveryPointArn": "arn:aws:backup:us-east-1:123456789012:recovery-point:rp-2",
                    "ResourceArn": "arn:aws:rds:us-east-1:123456789012:db:mydb",
                    "ResourceType": "RDS",
                    "CreationDate": creation_date,
                    "CompletionDate": completion_date,
                    "Status": "COMPLETED",
                    "BackupSizeInBytes": 20 * 1024**3,
                    "BackupJobId": "job-2",
                },
            ]
        },
    ]

    mock_client.get_paginator.return_value = mock_paginator

    with patch.object(repo, "_get_backup_client", return_value=mock_client):
        # Act
        recovery_points = repo.list_recovery_points("test-vault", "us-east-1")

        # Assert
        assert len(recovery_points) == 2
        assert recovery_points[0].resource_type == "EBS"
        assert recovery_points[1].resource_type == "RDS"

        mock_client.get_paginator.assert_called_once_with(
            "list_recovery_points_by_backup_vault"
        )
        mock_paginator.paginate.assert_called_once_with(BackupVaultName="test-vault")


def test_list_vaults_handles_missing_fields() -> None:
    """Test that missing optional fields are handled gracefully."""
    # Arrange
    repo = AWSBackupRepository(account_id="123456789012")

    # Mock boto3 client
    mock_client = Mock()
    mock_paginator = Mock()

    # Vault with minimal fields (no encryption, no recovery points count)
    mock_paginator.paginate.return_value = [
        {
            "BackupVaultList": [
                {
                    "BackupVaultName": "minimal-vault",
                    "BackupVaultArn": "arn:aws:backup:us-east-1:123456789012:backup-vault:minimal-vault",
                },
            ]
        },
    ]

    mock_client.get_paginator.return_value = mock_paginator

    with patch.object(repo, "_get_backup_client", return_value=mock_client):
        # Act
        vaults = repo.list_vaults("us-east-1")

        # Assert
        assert len(vaults) == 1
        assert vaults[0].name == "minimal-vault"
        assert vaults[0].recovery_point_count == 0  # Default value
        assert vaults[0].encryption_key_arn is None


def test_list_recovery_points_handles_missing_fields() -> None:
    """Test that missing optional fields in recovery points are handled gracefully."""
    # Arrange
    repo = AWSBackupRepository(account_id="123456789012")

    # Mock boto3 client
    mock_client = Mock()
    mock_paginator = Mock()

    creation_date = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    # Recovery point with minimal fields
    mock_paginator.paginate.return_value = [
        {
            "RecoveryPoints": [
                {
                    "RecoveryPointArn": "arn:aws:backup:us-east-1:123456789012:recovery-point:rp-1",
                    "ResourceArn": "arn:aws:ec2:us-east-1:123456789012:volume/vol-1",
                    "CreationDate": creation_date,
                    # Missing: ResourceType, CompletionDate, Status, BackupSizeInBytes, BackupJobId
                },
            ]
        },
    ]

    mock_client.get_paginator.return_value = mock_paginator

    with patch.object(repo, "_get_backup_client", return_value=mock_client):
        # Act
        recovery_points = repo.list_recovery_points("test-vault", "us-east-1")

        # Assert
        assert len(recovery_points) == 1
        assert recovery_points[0].resource_type == "UNKNOWN"  # Default value
        assert recovery_points[0].completion_date is None
        assert recovery_points[0].status == "UNKNOWN"  # Default value
        assert recovery_points[0].size_bytes == 0  # Default value
        assert recovery_points[0].backup_job_id == ""  # Default value
