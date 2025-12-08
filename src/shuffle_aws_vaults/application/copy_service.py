#!/usr/bin/env python3
"""
Service for copying recovery points.

Orchestrates the migration of recovery points from source to destination account.
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Protocol

from shuffle_aws_vaults.domain.migration_result import CopyOperation, MigrationBatch, MigrationStatus
from shuffle_aws_vaults.domain.recovery_point import RecoveryPoint

logger = logging.getLogger(__name__)

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

    def copy_single_threaded(
        self,
        recovery_points: list[RecoveryPoint],
        dest_account_id: str,
        region: str,
        progress_callback: Callable[[str, int, int], None] | None = None,
        shutdown_check: Callable[[], bool] | None = None,
        poll_interval: int = 30,
    ) -> MigrationBatch:
        """Copy recovery points one at a time with status polling.

        Args:
            recovery_points: List of recovery points to copy
            dest_account_id: Destination account ID
            region: AWS region
            progress_callback: Optional callback for progress updates (message, current, total)
            shutdown_check: Optional callback to check if shutdown requested
            poll_interval: Seconds between status checks (default: 30)

        Returns:
            MigrationBatch with final results
        """
        batch = self.create_copy_batch(recovery_points, dest_account_id, "single-threaded")

        if self.dry_run:
            for op in batch.operations:
                if op.status == MigrationStatus.PENDING:
                    op.skip("Dry run mode")
            return batch

        batch.start()
        total = len(batch.operations)

        for idx, operation in enumerate(batch.operations, 1):
            # Check for shutdown request
            if shutdown_check and shutdown_check():
                if progress_callback:
                    progress_callback("Shutdown requested, stopping copy operations", idx, total)
                break

            if operation.status != MigrationStatus.PENDING:
                continue

            # Start copy job
            try:
                if progress_callback:
                    progress_callback(
                        f"Starting copy for {operation.source_recovery_point_arn}",
                        idx,
                        total,
                    )

                copy_job_id = self.copy_repo.start_copy_job(
                    source_recovery_point_arn=operation.source_recovery_point_arn,
                    source_vault_name=operation.source_vault_name,
                    dest_vault_name=operation.dest_vault_name,
                    dest_account_id=dest_account_id,
                    region=region,
                )
                operation.start(copy_job_id)

                # Poll for completion
                while True:
                    # Check for shutdown request
                    if shutdown_check and shutdown_check():
                        if progress_callback:
                            progress_callback(
                                "Shutdown requested during polling, will resume later",
                                idx,
                                total,
                            )
                        break

                    time.sleep(poll_interval)

                    status = self.copy_repo.get_copy_job_status(copy_job_id, region)

                    if status == "COMPLETED":
                        operation.complete()
                        if progress_callback:
                            progress_callback(
                                f"Completed copy for {operation.source_recovery_point_arn}",
                                idx,
                                total,
                            )
                        break
                    elif status == "FAILED":
                        operation.fail("Copy job failed")
                        if progress_callback:
                            progress_callback(
                                f"Failed copy for {operation.source_recovery_point_arn}",
                                idx,
                                total,
                            )
                        break
                    else:
                        # Still running, continue polling
                        if progress_callback:
                            progress_callback(
                                f"Copy in progress ({status}): {operation.source_recovery_point_arn}",
                                idx,
                                total,
                            )

            except Exception as e:
                operation.fail(str(e))
                if progress_callback:
                    progress_callback(
                        f"Error copying {operation.source_recovery_point_arn}: {e}",
                        idx,
                        total,
                    )

        if batch.is_complete():
            batch.complete()

        return batch

    def copy_multithreaded(
        self,
        recovery_points: list[RecoveryPoint],
        dest_account_id: str,
        region: str,
        workers: int = 10,
        progress_callback: Callable[[str, int, int], None] | None = None,
        shutdown_check: Callable[[], bool] | None = None,
        poll_interval: int = 30,
    ) -> MigrationBatch:
        """Copy recovery points in parallel using multiple worker threads.

        Uses ThreadPoolExecutor for parallel copy jobs with thread-safe
        operation tracking.

        Args:
            recovery_points: List of recovery points to copy
            dest_account_id: Destination account ID
            region: AWS region
            workers: Number of concurrent worker threads (default: 10)
            progress_callback: Optional callback for progress updates (message, current, total)
            shutdown_check: Optional callback to check if shutdown requested
            poll_interval: Seconds between status checks (default: 30)

        Returns:
            MigrationBatch with final results
        """
        batch = self.create_copy_batch(recovery_points, dest_account_id, "multithreaded")

        if self.dry_run:
            for op in batch.operations:
                if op.status == MigrationStatus.PENDING:
                    op.skip("Dry run mode")
            return batch

        batch.start()
        total = len(batch.operations)

        # Thread-safe tracking of completed operations
        completed_count = 0
        completed_lock = threading.Lock()

        def process_copy_operation(idx: int, operation: CopyOperation) -> tuple[int, CopyOperation]:
            """Process a single copy operation (submit + poll).

            Thread Safety: Each worker processes a unique operation (by index).
            No two workers access the same CopyOperation instance, so no
            synchronization is needed at the operation level.

            Returns:
                Tuple of (index, updated operation)
            """
            nonlocal completed_count

            # Check for shutdown
            if shutdown_check and shutdown_check():
                return (idx, operation)

            if operation.status != MigrationStatus.PENDING:
                return (idx, operation)

            try:
                # Start copy job
                if progress_callback:
                    with completed_lock:
                        progress_callback(
                            f"Worker {threading.current_thread().name}: Starting copy for {operation.source_recovery_point_arn[:80]}...",
                            completed_count,
                            total,
                        )

                copy_job_id = self.copy_repo.start_copy_job(
                    source_recovery_point_arn=operation.source_recovery_point_arn,
                    source_vault_name=operation.source_vault_name,
                    dest_vault_name=operation.dest_vault_name,
                    dest_account_id=dest_account_id,
                    region=region,
                )
                operation.start(copy_job_id)

                # Poll for completion
                while True:
                    # Check for shutdown
                    if shutdown_check and shutdown_check():
                        if progress_callback:
                            with completed_lock:
                                progress_callback(
                                    f"Worker {threading.current_thread().name}: Shutdown requested during polling",
                                    completed_count,
                                    total,
                                )
                        break

                    time.sleep(poll_interval)

                    status = self.copy_repo.get_copy_job_status(copy_job_id, region)

                    if status == "COMPLETED":
                        operation.complete()
                        with completed_lock:
                            completed_count += 1
                            if progress_callback:
                                progress_callback(
                                    f"Worker {threading.current_thread().name}: Completed ({completed_count}/{total})",
                                    completed_count,
                                    total,
                                )
                        break
                    elif status == "FAILED":
                        operation.fail("Copy job failed")
                        with completed_lock:
                            completed_count += 1
                            if progress_callback:
                                progress_callback(
                                    f"Worker {threading.current_thread().name}: Failed ({completed_count}/{total})",
                                    completed_count,
                                    total,
                                )
                        break
                    else:
                        # Still running, log progress
                        if progress_callback:
                            with completed_lock:
                                progress_callback(
                                    f"Worker {threading.current_thread().name}: Copy in progress ({status})",
                                    completed_count,
                                    total,
                                )

            except Exception as e:
                operation.fail(str(e))
                with completed_lock:
                    completed_count += 1
                    if progress_callback:
                        progress_callback(
                            f"Worker {threading.current_thread().name}: Error - {e}",
                            completed_count,
                            total,
                        )

            return (idx, operation)

        # Submit operations to thread pool
        logger.info(f"Starting {workers} worker threads for {total} operations")

        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="CopyWorker") as executor:
            # Submit all pending operations
            futures = {}
            for idx, operation in enumerate(batch.operations):
                if operation.status == MigrationStatus.PENDING:
                    future = executor.submit(process_copy_operation, idx, operation)
                    futures[future] = idx

            # Wait for completion (or shutdown)
            for future in as_completed(futures):
                if shutdown_check and shutdown_check():
                    logger.info("Shutdown requested, waiting for workers to finish current operations...")
                    break

                try:
                    idx, updated_op = future.result()
                    # Update batch with result
                    batch.operations[idx] = updated_op
                except Exception as e:
                    idx = futures[future]
                    logger.error(f"Unexpected error processing operation {idx}: {e}")
                    batch.operations[idx].fail(f"Unexpected error: {e}")

        if batch.is_complete():
            batch.complete()

        return batch


if __name__ == "__main__":
    # Example usage
    info = file_info()
    print(f"{info['name']} v{info['version']}")
