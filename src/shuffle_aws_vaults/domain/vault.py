#!/usr/bin/env python3
"""
Domain model for AWS Backup vaults.

Represents a backup vault and provides business logic for vault operations.
"""

from dataclasses import dataclass
from typing import Optional

__version__ = "0.1.0"
__author__ = "John Ayers"


def file_info() -> dict[str, str]:
    """Return metadata about this module.

    Returns:
        Dictionary containing module metadata
    """
    return {
        "name": "vault",
        "description": "Domain model for backup vaults",
        "version": __version__,
        "author": __author__,
        "last_updated": "2025-12-07",
    }


@dataclass(frozen=True)
class Vault:
    """Immutable domain model representing an AWS Backup vault.

    Attributes:
        name: Vault name
        arn: Vault ARN
        region: AWS region where vault exists
        account_id: AWS account ID
        recovery_point_count: Number of recovery points in vault
        encryption_key_arn: KMS key ARN used for encryption (optional)
    """

    name: str
    arn: str
    region: str
    account_id: str
    recovery_point_count: int = 0
    encryption_key_arn: Optional[str] = None

    def is_encrypted(self) -> bool:
        """Check if vault uses custom KMS encryption.

        Returns:
            True if custom encryption key is configured
        """
        return self.encryption_key_arn is not None

    def has_recovery_points(self) -> bool:
        """Check if vault contains any recovery points.

        Returns:
            True if recovery_point_count > 0
        """
        return self.recovery_point_count > 0

    def matches_pattern(self, pattern: str) -> bool:
        """Check if vault name matches a pattern.

        Args:
            pattern: Pattern to match (supports * wildcard)

        Returns:
            True if vault name matches pattern
        """
        if pattern == "*":
            return True
        if "*" in pattern:
            prefix = pattern.rstrip("*")
            return self.name.startswith(prefix)
        return self.name == pattern


if __name__ == "__main__":
    # Example usage
    info = file_info()
    print(f"{info['name']} v{info['version']}")
