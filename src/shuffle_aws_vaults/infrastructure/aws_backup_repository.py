#!/usr/bin/env python3
"""
AWS Backup repository implementation.

Provides concrete implementations of repository protocols using boto3.
"""

from datetime import datetime
from typing import Any

import boto3
from botocore.exceptions import ClientError

from shuffle_aws_vaults.domain.recovery_point import RecoveryPoint
from shuffle_aws_vaults.domain.vault import Vault

__version__ = "0.1.0"
__author__ = "John Ayers"


def file_info() -> dict[str, str]:
    """Return metadata about this module.

    Returns:
        Dictionary containing module metadata
    """
    return {
        "name": "aws_backup_repository",
        "description": "AWS Backup repository implementation",
        "version": __version__,
        "author": __author__,
        "last_updated": "2025-12-07",
    }


class AWSBackupRepository:
    """Repository for AWS Backup operations using boto3.

    Implements BackupRepository and CopyRepository protocols.
    """

    def __init__(self, account_id: str, role_arn: str | None = None) -> None:
        """Initialize AWS Backup repository.

        Args:
            account_id: AWS account ID
            role_arn: Optional IAM role ARN to assume for cross-account access
        """
        self.account_id = account_id
        self.role_arn = role_arn
        self._sessions: dict[str, boto3.Session] = {}

    def _get_session(self, region: str) -> boto3.Session:
        """Get or create a boto3 session for a region.

        Args:
            region: AWS region

        Returns:
            boto3 Session
        """
        if region not in self._sessions:
            if self.role_arn:
                sts = boto3.client("sts")
                response = sts.assume_role(
                    RoleArn=self.role_arn,
                    RoleSessionName=f"shuffle-aws-vaults-{self.account_id}",
                )
                credentials = response["Credentials"]
                self._sessions[region] = boto3.Session(
                    aws_access_key_id=credentials["AccessKeyId"],
                    aws_secret_access_key=credentials["SecretAccessKey"],
                    aws_session_token=credentials["SessionToken"],
                    region_name=region,
                )
            else:
                self._sessions[region] = boto3.Session(region_name=region)

        return self._sessions[region]

    def _get_backup_client(self, region: str) -> Any:
        """Get boto3 backup client for a region.

        Args:
            region: AWS region

        Returns:
            boto3 backup client
        """
        session = self._get_session(region)
        return session.client("backup")

    def list_vaults(self, region: str) -> list[Vault]:
        """List all backup vaults in a region.

        Args:
            region: AWS region

        Returns:
            List of Vault domain objects
        """
        client = self._get_backup_client(region)
        vaults = []

        try:
            paginator = client.get_paginator("list_backup_vaults")
            for page in paginator.paginate():
                for vault_data in page.get("BackupVaultList", []):
                    vault = Vault(
                        name=vault_data["BackupVaultName"],
                        arn=vault_data["BackupVaultArn"],
                        region=region,
                        account_id=self.account_id,
                        recovery_point_count=vault_data.get("NumberOfRecoveryPoints", 0),
                        encryption_key_arn=vault_data.get("EncryptionKeyArn"),
                    )
                    vaults.append(vault)
        except ClientError as e:
            raise RuntimeError(f"Failed to list vaults in {region}: {e}") from e

        return vaults

    def create_vault(
        self, vault_name: str, region: str, encryption_key_arn: str | None = None
    ) -> Vault:
        """Create a backup vault.

        Args:
            vault_name: Name for the new vault
            region: AWS region
            encryption_key_arn: Optional KMS key ARN for encryption

        Returns:
            Created Vault domain object
        """
        client = self._get_backup_client(region)

        try:
            params = {"BackupVaultName": vault_name}
            if encryption_key_arn:
                params["EncryptionKeyArn"] = encryption_key_arn

            response = client.create_backup_vault(**params)

            return Vault(
                name=vault_name,
                arn=response["BackupVaultArn"],
                region=region,
                account_id=self.account_id,
                encryption_key_arn=encryption_key_arn,
            )
        except ClientError as e:
            # Vault already exists is not an error - return existing vault info
            if e.response["Error"]["Code"] == "AlreadyExistsException":
                # Get vault details
                try:
                    desc_response = client.describe_backup_vault(BackupVaultName=vault_name)
                    return Vault(
                        name=vault_name,
                        arn=desc_response["BackupVaultArn"],
                        region=region,
                        account_id=self.account_id,
                        recovery_point_count=desc_response.get("NumberOfRecoveryPoints", 0),
                        encryption_key_arn=desc_response.get("EncryptionKeyArn"),
                    )
                except ClientError:
                    pass
            raise RuntimeError(f"Failed to create vault {vault_name}: {e}") from e

    def list_recovery_points(self, vault_name: str, region: str) -> list[RecoveryPoint]:
        """List recovery points in a vault.

        Args:
            vault_name: Name of backup vault
            region: AWS region

        Returns:
            List of RecoveryPoint domain objects
        """
        client = self._get_backup_client(region)
        recovery_points = []

        try:
            paginator = client.get_paginator("list_recovery_points_by_backup_vault")
            for page in paginator.paginate(BackupVaultName=vault_name):
                for rp_data in page.get("RecoveryPoints", []):
                    recovery_point = RecoveryPoint(
                        recovery_point_arn=rp_data["RecoveryPointArn"],
                        backup_vault_name=vault_name,
                        resource_arn=rp_data["ResourceArn"],
                        resource_type=rp_data.get("ResourceType", "UNKNOWN"),
                        creation_date=rp_data["CreationDate"],
                        completion_date=rp_data.get("CompletionDate"),
                        status=rp_data.get("Status", "UNKNOWN"),
                        size_bytes=rp_data.get("BackupSizeInBytes", 0),
                        backup_job_id=rp_data.get("BackupJobId", ""),
                    )
                    recovery_points.append(recovery_point)
        except ClientError as e:
            raise RuntimeError(
                f"Failed to list recovery points in vault {vault_name}: {e}"
            ) from e

        return recovery_points

    def start_copy_job(
        self,
        source_recovery_point_arn: str,
        source_vault_name: str,
        dest_vault_name: str,
        dest_account_id: str,
        region: str,
    ) -> str:
        """Start a copy job for a recovery point.

        Args:
            source_recovery_point_arn: ARN of source recovery point
            source_vault_name: Source vault name
            dest_vault_name: Destination vault name
            dest_account_id: Destination account ID
            region: AWS region

        Returns:
            Copy job ID
        """
        client = self._get_backup_client(region)

        try:
            response = client.start_copy_job(
                RecoveryPointArn=source_recovery_point_arn,
                SourceBackupVaultName=source_vault_name,
                DestinationBackupVaultArn=f"arn:aws:backup:{region}:{dest_account_id}:backup-vault:{dest_vault_name}",
                IamRoleArn=f"arn:aws:iam::{self.account_id}:role/service-role/AWSBackupDefaultServiceRole",
            )
            return response["CopyJobId"]
        except ClientError as e:
            raise RuntimeError(f"Failed to start copy job: {e}") from e

    def get_copy_job_status(self, copy_job_id: str, region: str) -> str:
        """Get status of a copy job.

        Args:
            copy_job_id: Copy job ID
            region: AWS region

        Returns:
            Job status (CREATED, RUNNING, COMPLETED, FAILED)
        """
        client = self._get_backup_client(region)

        try:
            response = client.describe_copy_job(CopyJobId=copy_job_id)
            return response["CopyJob"]["State"]
        except ClientError as e:
            raise RuntimeError(f"Failed to get copy job status: {e}") from e

    def get_vault_lock_configuration(
        self, vault_name: str, region: str
    ) -> dict[str, int | bool] | None:
        """Get vault lock configuration.

        Args:
            vault_name: Vault name
            region: AWS region

        Returns:
            Dict with min_retention_days, max_retention_days, and locked status,
            or None if no lock configuration exists
        """
        client = self._get_backup_client(region)

        # Get vault lock configuration from describe_backup_vault
        try:
            response = client.describe_backup_vault(BackupVaultName=vault_name)
            if "MinRetentionDays" in response or "MaxRetentionDays" in response:
                return {
                    "min_retention_days": response.get("MinRetentionDays"),
                    "max_retention_days": response.get("MaxRetentionDays"),
                    "locked": response.get("Locked", False),
                }
        except ClientError:
            pass

        return None

    def put_vault_lock_configuration(
        self,
        vault_name: str,
        region: str,
        min_retention_days: int | None = None,
        max_retention_days: int | None = None,
    ) -> None:
        """Set vault lock configuration.

        Args:
            vault_name: Vault name
            region: AWS region
            min_retention_days: Minimum retention days
            max_retention_days: Maximum retention days
        """
        client = self._get_backup_client(region)

        try:
            params = {"BackupVaultName": vault_name}
            if min_retention_days is not None:
                params["MinRetentionDays"] = min_retention_days
            if max_retention_days is not None:
                params["MaxRetentionDays"] = max_retention_days

            client.put_backup_vault_lock_configuration(**params)
        except ClientError as e:
            raise RuntimeError(
                f"Failed to set vault lock configuration for {vault_name}: {e}"
            ) from e


if __name__ == "__main__":
    # Example usage
    info = file_info()
    print(f"{info['name']} v{info['version']}")
