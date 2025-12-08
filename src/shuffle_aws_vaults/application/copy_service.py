#!/usr/bin/env python3
"""
Service for copying recovery points.

Orchestrates the migration of recovery points from source to destination account.
"""

from typing import Protocol

from shuffle_aws_vaults.domain.migration_result import CopyOperation, MigrationBatch, MigrationStatus
from shuffle_aws_vaults.domain.recovery_point import RecoveryPoint

__version__ = "0.1.0"
__author__ = "John Ayers"


def file_info() -> dict[str, str]:
    """Return metadata about this module.

    Returns:
        Dictionary containing module metadata
    """
    return {
        "name": "copy_service",
        "description": "Service for copying recovery points",
        "version": __version__,
        "author": __author__,
        "last_updated": "2025-12-07",
    }


class CopyRepository(Protocol):
    """Protocol defining interface for copy operations.

    Infrastructure layer must implement this protocol.
    """

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
        ...

    def get_copy_job_status(self, copy_job_id: str, region: str) -> str:
        """Get status of a copy job.

        Args:
            copy_job_id: Copy job ID
            region: AWS region

        Returns:
            Job status (CREATED, RUNNING, COMPLETED, FAILED)
        """
        ...


class CopyService:
    """Application service for copy operations."""

    def __init__(
        self, copy_repo: CopyRepository, dry_run: bool = False, batch_size: int = 10
    ) -> None:
        """Initialize the copy service.

        Args:
            copy_repo: Repository for copy operations
            dry_run: If True, don't make actual copy requests
            batch_size: Number of concurrent copy operations
        """
        self.copy_repo = copy_repo
        self.dry_run = dry_run
        self.batch_size = batch_size

    def create_copy_batch(
        self,
        recovery_points: list[RecoveryPoint],
        dest_account_id: str,
        batch_id: str,
    ) -> MigrationBatch:
        """Create a migration batch from recovery points.

        Args:
            recovery_points: List of recovery points to copy
            dest_account_id: Destination account ID
            batch_id: Unique batch identifier

        Returns:
            MigrationBatch with CopyOperation objects
        """
        batch = MigrationBatch(batch_id=batch_id)

        for rp in recovery_points:
            if not rp.is_copyable():
                operation = CopyOperation(
                    source_recovery_point_arn=rp.recovery_point_arn,
                    source_vault_name=rp.backup_vault_name,
                    dest_vault_name=rp.backup_vault_name,  # replicate structure
                )
                operation.skip(f"Recovery point not copyable: {rp.status}")
            else:
                operation = CopyOperation(
                    source_recovery_point_arn=rp.recovery_point_arn,
                    source_vault_name=rp.backup_vault_name,
                    dest_vault_name=rp.backup_vault_name,  # replicate structure
                )

            batch.add_operation(operation)

        return batch

    def execute_batch(
        self, batch: MigrationBatch, dest_account_id: str, region: str
    ) -> MigrationBatch:
        """Execute copy operations in a batch.

        Args:
            batch: Migration batch to execute
            dest_account_id: Destination account ID
            region: AWS region

        Returns:
            Updated batch with operation results
        """
        if self.dry_run:
            for op in batch.operations:
                if op.status == MigrationStatus.PENDING:
                    op.skip("Dry run mode")
            return batch

        batch.start()

        for operation in batch.operations:
            if operation.status != MigrationStatus.PENDING:
                continue

            try:
                copy_job_id = self.copy_repo.start_copy_job(
                    source_recovery_point_arn=operation.source_recovery_point_arn,
                    source_vault_name=operation.source_vault_name,
                    dest_vault_name=operation.dest_vault_name,
                    dest_account_id=dest_account_id,
                    region=region,
                )
                operation.start(copy_job_id)
            except Exception as e:
                operation.fail(str(e))

        return batch

    def check_batch_progress(self, batch: MigrationBatch, region: str) -> MigrationBatch:
        """Check progress of copy operations in a batch.

        Args:
            batch: Migration batch to check
            region: AWS region

        Returns:
            Updated batch with current status
        """
        for operation in batch.operations:
            if operation.status != MigrationStatus.IN_PROGRESS:
                continue

            if not operation.copy_job_id:
                continue

            try:
                status = self.copy_repo.get_copy_job_status(operation.copy_job_id, region)
                if status == "COMPLETED":
                    operation.complete()
                elif status == "FAILED":
                    operation.fail("Copy job failed")
            except Exception as e:
                operation.fail(f"Failed to check status: {e}")

        if batch.is_complete():
            batch.complete()

        return batch


if __name__ == "__main__":
    # Example usage
    info = file_info()
    print(f"{info['name']} v{info['version']}")
