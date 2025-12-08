#!/usr/bin/env python3
"""
Domain models for state persistence.

Represents the state of migration operations for resumability.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

__version__ = "0.1.0"
__author__ = "John Ayers"


def file_info() -> dict[str, str]:
    """Return metadata about this module.

    Returns:
        Dictionary containing module metadata
    """
    return {
        "name": "state",
        "description": "Domain models for state persistence",
        "version": __version__,
        "author": __author__,
        "last_updated": "2025-12-07",
    }


@dataclass
class RecoveryPointRef:
    """Lightweight reference to a recovery point for state persistence.

    Attributes:
        recovery_point_arn: ARN of the recovery point
        resource_arn: ARN of the backed-up resource
        vault_name: Name of the backup vault
        size_bytes: Size in bytes
    """

    recovery_point_arn: str
    resource_arn: str
    vault_name: str
    size_bytes: int


@dataclass
class InventoryState:
    """State representing the inventory of recovery points.

    Attributes:
        vault_name: Name of the vault being inventoried
        recovery_points: List of recovery point references
        total_count: Total number of recovery points
        total_size_bytes: Total size in bytes
        timestamp: When the inventory was taken
    """

    vault_name: str
    recovery_points: list[RecoveryPointRef] = field(default_factory=list)
    total_count: int = 0
    total_size_bytes: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    def add_recovery_point(self, ref: RecoveryPointRef) -> None:
        """Add a recovery point to the inventory.

        Args:
            ref: Recovery point reference to add
        """
        self.recovery_points.append(ref)
        self.total_count += 1
        self.total_size_bytes += ref.size_bytes


@dataclass
class CopyOperation:
    """State representing a single copy operation.

    Attributes:
        recovery_point_arn: ARN of the recovery point being copied
        resource_arn: ARN of the backed-up resource
        status: Status of the copy (pending, in_progress, completed, failed, skipped)
        started_at: When the copy started
        completed_at: When the copy completed
        error_message: Error message if failed
    """

    recovery_point_arn: str
    resource_arn: str
    status: str = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class CopyState:
    """State representing the copy operation progress.

    Attributes:
        source_account: Source AWS account ID
        dest_account: Destination AWS account ID
        vault_name: Name of the vault being copied
        operations: List of copy operations
        schema_version: Schema version for state format
        timestamp: When the state was last updated
    """

    source_account: str
    dest_account: str
    vault_name: str
    operations: list[CopyOperation] = field(default_factory=list)
    schema_version: str = "1.0"
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    def add_operation(self, operation: CopyOperation) -> None:
        """Add a copy operation to the state.

        Args:
            operation: Copy operation to add
        """
        self.operations.append(operation)

    def get_operation(self, recovery_point_arn: str) -> Optional[CopyOperation]:
        """Get a copy operation by recovery point ARN.

        Args:
            recovery_point_arn: ARN of the recovery point

        Returns:
            Copy operation if found, None otherwise
        """
        for op in self.operations:
            if op.recovery_point_arn == recovery_point_arn:
                return op
        return None

    def count_by_status(self, status: str) -> int:
        """Count operations by status.

        Args:
            status: Status to count

        Returns:
            Number of operations with the given status
        """
        return sum(1 for op in self.operations if op.status == status)

    def get_pending_operations(self) -> list[CopyOperation]:
        """Get all pending operations.

        Returns:
            List of pending copy operations
        """
        return [op for op in self.operations if op.status == "pending"]

    def get_failed_operations(self) -> list[CopyOperation]:
        """Get all failed operations.

        Returns:
            List of failed copy operations
        """
        return [op for op in self.operations if op.status == "failed"]

    def is_complete(self) -> bool:
        """Check if all operations are complete.

        Returns:
            True if all operations are completed or skipped
        """
        return all(
            op.status in ["completed", "skipped", "failed"] for op in self.operations
        )


if __name__ == "__main__":
    # Example usage
    info = file_info()
    print(f"{info['name']} v{info['version']}")
