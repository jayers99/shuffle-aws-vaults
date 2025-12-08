#!/usr/bin/env python3
"""
Service for listing vaults and recovery points.

Orchestrates the discovery of backup vaults and recovery points
across AWS accounts and regions.
"""

from typing import Protocol

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
        "name": "list_service",
        "description": "Service for listing vaults and recovery points",
        "version": __version__,
        "author": __author__,
        "last_updated": "2025-12-07",
    }


class BackupRepository(Protocol):
    """Protocol defining interface for backup operations.

    Infrastructure layer must implement this protocol.
    """

    def list_vaults(self, region: str) -> list[Vault]:
        """List all backup vaults in a region.

        Args:
            region: AWS region

        Returns:
            List of Vault objects
        """
        ...

    def list_recovery_points(self, vault_name: str, region: str) -> list[RecoveryPoint]:
        """List recovery points in a vault.

        Args:
            vault_name: Name of backup vault
            region: AWS region

        Returns:
            List of RecoveryPoint objects
        """
        ...


class ListService:
    """Application service for listing operations."""

    def __init__(self, backup_repo: BackupRepository, dry_run: bool = False) -> None:
        """Initialize the list service.

        Args:
            backup_repo: Repository for backup operations
            dry_run: If True, don't make actual AWS calls
        """
        self.backup_repo = backup_repo
        self.dry_run = dry_run

    def list_all_vaults(self, region: str) -> list[Vault]:
        """List all backup vaults in a region.

        Args:
            region: AWS region

        Returns:
            List of vaults sorted by name
        """
        if self.dry_run:
            return []

        vaults = self.backup_repo.list_vaults(region)
        return sorted(vaults, key=lambda v: v.name)

    def list_vault_recovery_points(self, vault_name: str, region: str) -> list[RecoveryPoint]:
        """List all recovery points in a specific vault.

        Args:
            vault_name: Name of vault
            region: AWS region

        Returns:
            List of recovery points sorted by creation date (newest first)
        """
        if self.dry_run:
            return []

        recovery_points = self.backup_repo.list_recovery_points(vault_name, region)
        return sorted(recovery_points, key=lambda rp: rp.creation_date, reverse=True)

    def get_vault_summary(self, region: str) -> dict[str, int]:
        """Get summary statistics for all vaults.

        Args:
            region: AWS region

        Returns:
            Dictionary with summary stats (vault_count, total_recovery_points, etc.)
        """
        vaults = self.list_all_vaults(region)

        return {
            "vault_count": len(vaults),
            "total_recovery_points": sum(v.recovery_point_count for v in vaults),
            "encrypted_vaults": sum(1 for v in vaults if v.is_encrypted()),
            "empty_vaults": sum(1 for v in vaults if not v.has_recovery_points()),
        }


if __name__ == "__main__":
    # Example usage
    info = file_info()
    print(f"{info['name']} v{info['version']}")
