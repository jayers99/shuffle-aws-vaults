#!/usr/bin/env python3
"""
Domain model for AWS Backup recovery points.

Represents a recovery point with its metadata and provides business logic
for comparison and filtering operations.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

__version__ = "0.1.0"
__author__ = "John Ayers"


def file_info() -> dict[str, str]:
    """Return metadata about this module.

    Returns:
        Dictionary containing module metadata
    """
    return {
        "name": "recovery_point",
        "description": "Domain model for recovery points",
        "version": __version__,
        "author": __author__,
        "last_updated": "2025-12-07",
    }


@dataclass(frozen=True)
class RecoveryPoint:
    """Immutable domain model representing an AWS Backup recovery point.

    Attributes:
        recovery_point_arn: Unique ARN identifier
        backup_vault_name: Name of the backup vault containing this recovery point
        resource_arn: ARN of the resource that was backed up
        resource_type: Type of resource (e.g., EBS, RDS, EFS)
        creation_date: When the recovery point was created
        completion_date: When the recovery point backup completed
        status: Current status (COMPLETED, PARTIAL, DELETING, EXPIRED)
        size_bytes: Size of the backup in bytes
        backup_job_id: ID of the backup job that created this recovery point
    """

    recovery_point_arn: str
    backup_vault_name: str
    resource_arn: str
    resource_type: str
    creation_date: datetime
    completion_date: Optional[datetime]
    status: str
    size_bytes: int
    backup_job_id: str

    def is_completed(self) -> bool:
        """Check if recovery point is fully completed.

        Returns:
            True if status is COMPLETED
        """
        return self.status == "COMPLETED"

    def is_copyable(self) -> bool:
        """Check if recovery point can be copied.

        Returns:
            True if status is COMPLETED and completion_date is set
        """
        return self.is_completed() and self.completion_date is not None

    def age_days(self, reference_date: Optional[datetime] = None) -> int:
        """Calculate age of recovery point in days.

        Args:
            reference_date: Date to calculate age from (defaults to now)

        Returns:
            Age in days
        """
        ref = reference_date or datetime.now(tz=self.creation_date.tzinfo)
        delta = ref - self.creation_date
        return delta.days

    def size_gb(self) -> float:
        """Get size in gigabytes.

        Returns:
            Size in GB rounded to 2 decimal places
        """
        return round(self.size_bytes / (1024**3), 2)


if __name__ == "__main__":
    # Example usage
    info = file_info()
    print(f"{info['name']} v{info['version']}")
