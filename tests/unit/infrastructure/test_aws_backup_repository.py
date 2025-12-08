"""Unit tests for AWSBackupRepository."""

from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch

import pytest
from botocore.exceptions import ClientError

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

        mock_client.get_paginator.assert_called_once_with("list_recovery_points_by_backup_vault")
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


def test_start_copy_job() -> None:
    """Test starting a copy job."""
    # Arrange
    repo = AWSBackupRepository(account_id="123456789012")

    # Mock boto3 client
    mock_client = Mock()
    mock_client.start_copy_job.return_value = {"CopyJobId": "copy-job-123"}

    with patch.object(repo, "_get_backup_client", return_value=mock_client):
        # Act
        copy_job_id = repo.start_copy_job(
            source_recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-1",
            source_vault_name="source-vault",
            dest_vault_name="dest-vault",
            dest_account_id="222222222222",
            region="us-east-1",
        )

        # Assert
        assert copy_job_id == "copy-job-123"
        mock_client.start_copy_job.assert_called_once_with(
            RecoveryPointArn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-1",
            SourceBackupVaultName="source-vault",
            DestinationBackupVaultArn="arn:aws:backup:us-east-1:222222222222:backup-vault:dest-vault",
            IamRoleArn="arn:aws:iam::123456789012:role/service-role/AWSBackupDefaultServiceRole",
        )


def test_get_copy_job_status() -> None:
    """Test getting copy job status."""
    # Arrange
    repo = AWSBackupRepository(account_id="123456789012")

    # Mock boto3 client
    mock_client = Mock()
    mock_client.describe_copy_job.return_value = {"CopyJob": {"State": "COMPLETED"}}

    with patch.object(repo, "_get_backup_client", return_value=mock_client):
        # Act
        status = repo.get_copy_job_status("copy-job-123", "us-east-1")

        # Assert
        assert status == "COMPLETED"
        mock_client.describe_copy_job.assert_called_once_with(CopyJobId="copy-job-123")


def test_create_vault() -> None:
    """Test creating a new vault."""
    # Arrange
    repo = AWSBackupRepository(account_id="123456789012")

    # Mock boto3 client
    mock_client = Mock()
    mock_client.create_backup_vault.return_value = {
        "BackupVaultArn": "arn:aws:backup:us-east-1:123456789012:backup-vault:new-vault"
    }

    with patch.object(repo, "_get_backup_client", return_value=mock_client):
        # Act
        vault = repo.create_vault("new-vault", "us-east-1")

        # Assert
        assert vault.name == "new-vault"
        assert vault.arn == "arn:aws:backup:us-east-1:123456789012:backup-vault:new-vault"
        assert vault.region == "us-east-1"
        assert vault.account_id == "123456789012"
        mock_client.create_backup_vault.assert_called_once_with(BackupVaultName="new-vault")


def test_create_vault_with_encryption() -> None:
    """Test creating a vault with encryption key."""
    # Arrange
    repo = AWSBackupRepository(account_id="123456789012")
    kms_key_arn = "arn:aws:kms:us-east-1:123456789012:key/test-key"

    # Mock boto3 client
    mock_client = Mock()
    mock_client.create_backup_vault.return_value = {
        "BackupVaultArn": "arn:aws:backup:us-east-1:123456789012:backup-vault:encrypted-vault"
    }

    with patch.object(repo, "_get_backup_client", return_value=mock_client):
        # Act
        vault = repo.create_vault("encrypted-vault", "us-east-1", encryption_key_arn=kms_key_arn)

        # Assert
        assert vault.name == "encrypted-vault"
        assert vault.encryption_key_arn == kms_key_arn
        mock_client.create_backup_vault.assert_called_once_with(
            BackupVaultName="encrypted-vault",
            EncryptionKeyArn=kms_key_arn,
        )


def test_create_vault_already_exists() -> None:
    """Test creating a vault that already exists."""
    # Arrange
    repo = AWSBackupRepository(account_id="123456789012")

    # Mock boto3 client
    mock_client = Mock()
    error_response = {"Error": {"Code": "AlreadyExistsException"}}
    mock_client.create_backup_vault.side_effect = ClientError(error_response, "create_backup_vault")
    mock_client.describe_backup_vault.return_value = {
        "BackupVaultArn": "arn:aws:backup:us-east-1:123456789012:backup-vault:existing-vault",
        "NumberOfRecoveryPoints": 10,
    }

    with patch.object(repo, "_get_backup_client", return_value=mock_client):
        # Act
        vault = repo.create_vault("existing-vault", "us-east-1")

        # Assert
        assert vault.name == "existing-vault"
        assert vault.recovery_point_count == 10
        mock_client.describe_backup_vault.assert_called_once_with(BackupVaultName="existing-vault")


def test_get_vault_lock_configuration() -> None:
    """Test getting vault lock configuration."""
    # Arrange
    repo = AWSBackupRepository(account_id="123456789012")

    # Mock boto3 client
    mock_client = Mock()
    mock_client.describe_backup_vault.return_value = {
        "MinRetentionDays": 90,
        "MaxRetentionDays": 365,
        "Locked": True,
    }

    with patch.object(repo, "_get_backup_client", return_value=mock_client):
        # Act
        config = repo.get_vault_lock_configuration("locked-vault", "us-east-1")

        # Assert
        assert config is not None
        assert config["min_retention_days"] == 90
        assert config["max_retention_days"] == 365
        assert config["locked"] is True


def test_get_vault_lock_configuration_no_lock() -> None:
    """Test getting vault lock configuration when no lock exists."""
    # Arrange
    repo = AWSBackupRepository(account_id="123456789012")

    # Mock boto3 client
    mock_client = Mock()
    mock_client.describe_backup_vault.return_value = {}

    with patch.object(repo, "_get_backup_client", return_value=mock_client):
        # Act
        config = repo.get_vault_lock_configuration("no-lock-vault", "us-east-1")

        # Assert
        assert config is None


def test_put_vault_lock_configuration() -> None:
    """Test setting vault lock configuration."""
    # Arrange
    repo = AWSBackupRepository(account_id="123456789012")

    # Mock boto3 client
    mock_client = Mock()

    with patch.object(repo, "_get_backup_client", return_value=mock_client):
        # Act
        repo.put_vault_lock_configuration(
            "locked-vault", "us-east-1", min_retention_days=90, max_retention_days=365
        )

        # Assert
        mock_client.put_backup_vault_lock_configuration.assert_called_once_with(
            BackupVaultName="locked-vault",
            MinRetentionDays=90,
            MaxRetentionDays=365,
        )
