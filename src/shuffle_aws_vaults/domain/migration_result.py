#!/usr/bin/env python3
"""
Domain model for migration results.

Tracks the outcome of recovery point migration operations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

__version__ = "0.1.0"
__author__ = "John Ayers"


def file_info() -> dict[str, str]:
    """Return metadata about this module.

    Returns:
        Dictionary containing module metadata
    """
    return {
        "name": "migration_result",
        "description": "Domain model for migration tracking",
        "version": __version__,
        "author": __author__,
        "last_updated": "2025-12-07",
    }


class MigrationStatus(Enum):
    """Enumeration of migration statuses."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class CopyOperation:
    """Represents a single copy operation for a recovery point.

    Attributes:
        source_recovery_point_arn: ARN of source recovery point
        source_vault_name: Name of source vault
        dest_vault_name: Name of destination vault
        status: Current status of the operation
        started_at: When the operation started
        completed_at: When the operation completed (if finished)
        error_message: Error details if operation failed
        copy_job_id: AWS copy job ID (if started)
    """

    source_recovery_point_arn: str
    source_vault_name: str
    dest_vault_name: str
    status: MigrationStatus = MigrationStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    copy_job_id: str | None = None

    def start(self, copy_job_id: str) -> None:
        """Mark operation as started.

        Args:
            copy_job_id: AWS copy job ID
        """
        self.status = MigrationStatus.IN_PROGRESS
        self.started_at = datetime.now()
        self.copy_job_id = copy_job_id

    def complete(self) -> None:
        """Mark operation as completed successfully."""
        self.status = MigrationStatus.COMPLETED
        self.completed_at = datetime.now()

    def fail(self, error: str) -> None:
        """Mark operation as failed.

        Args:
            error: Error message describing the failure
        """
        self.status = MigrationStatus.FAILED
        self.completed_at = datetime.now()
        self.error_message = error

    def skip(self, reason: str) -> None:
        """Mark operation as skipped.

        Args:
            reason: Reason for skipping
        """
        self.status = MigrationStatus.SKIPPED
        self.completed_at = datetime.now()
        self.error_message = reason

    def duration_seconds(self) -> float | None:
        """Calculate operation duration in seconds.

        Returns:
            Duration in seconds if operation has started, None otherwise
        """
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()


@dataclass
class MigrationBatch:
    """Tracks a batch of copy operations.

    Attributes:
        batch_id: Unique identifier for this batch
        operations: List of copy operations in this batch
        started_at: When batch processing started
        completed_at: When batch processing completed
    """

    batch_id: str
    operations: list[CopyOperation] = field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def add_operation(self, operation: CopyOperation) -> None:
        """Add a copy operation to the batch.

        Args:
            operation: Copy operation to add
        """
        self.operations.append(operation)

    def start(self) -> None:
        """Mark batch as started."""
        self.started_at = datetime.now()

    def complete(self) -> None:
        """Mark batch as completed."""
        self.completed_at = datetime.now()

    def count_by_status(self, status: MigrationStatus) -> int:
        """Count operations with given status.

        Args:
            status: Status to count

        Returns:
            Number of operations with the specified status
        """
        return sum(1 for op in self.operations if op.status == status)

    def success_rate(self) -> float:
        """Calculate success rate as percentage.

        Returns:
            Percentage of completed operations (0-100)
        """
        if not self.operations:
            return 0.0
        completed = self.count_by_status(MigrationStatus.COMPLETED)
        return round((completed / len(self.operations)) * 100, 2)

    def is_complete(self) -> bool:
        """Check if all operations are finished.

        Returns:
            True if no operations are pending or in progress
        """
        pending = self.count_by_status(MigrationStatus.PENDING)
        in_progress = self.count_by_status(MigrationStatus.IN_PROGRESS)
        return pending == 0 and in_progress == 0


if __name__ == "__main__":
    # Example usage
    info = file_info()
    print(f"{info['name']} v{info['version']}")
