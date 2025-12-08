#!/usr/bin/env python3
"""
Service for verifying migration results.

Validates that recovery points were successfully migrated to the destination account.
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
        "name": "verify_service",
        "description": "Service for verifying migration results",
        "version": __version__,
        "author": __author__,
        "last_updated": "2025-12-07",
    }


class VerifyRepository(Protocol):
    """Protocol defining interface for verification operations.

    Infrastructure layer must implement this protocol.
    """

    def list_vaults(self, region: str) -> list[Vault]:
        """List all backup vaults in a region."""
        ...

    def list_recovery_points(self, vault_name: str, region: str) -> list[RecoveryPoint]:
        """List recovery points in a vault."""
        ...


@dataclass
class VerificationResult:
    """Result of migration verification.

    Attributes:
        vault_name: Name of vault verified
        source_count: Number of recovery points in source
        dest_count: Number of recovery points in destination
        missing_count: Number of recovery points missing in destination
        matched_count: Number of recovery points successfully migrated
        extra_count: Number of extra recovery points in destination
    """

    vault_name: str
    source_count: int
    dest_count: int
    missing_count: int = 0
    matched_count: int = 0
    extra_count: int = 0

    def is_complete(self) -> bool:
        """Check if migration is complete.

        Returns:
            True if all source recovery points exist in destination
        """
        return self.missing_count == 0 and self.matched_count == self.source_count


class VerifyService:
    """Application service for verification operations."""

    def __init__(
        self, source_repo: VerifyRepository, dest_repo: VerifyRepository
    ) -> None:
        """Initialize the verify service.

        Args:
            source_repo: Repository for source account
            dest_repo: Repository for destination account
        """
        self.source_repo = source_repo
        self.dest_repo = dest_repo

    def verify_vault(self, vault_name: str, region: str) -> VerificationResult:
        """Verify migration for a specific vault.

        Args:
            vault_name: Name of vault to verify
            region: AWS region

        Returns:
            VerificationResult with comparison details
        """
        source_points = self.source_repo.list_recovery_points(vault_name, region)
        dest_points = self.dest_repo.list_recovery_points(vault_name, region)

        source_arns = {rp.resource_arn for rp in source_points}
        dest_arns = {rp.resource_arn for rp in dest_points}

        missing_arns = source_arns - dest_arns
        matched_arns = source_arns & dest_arns
        extra_arns = dest_arns - source_arns

        return VerificationResult(
            vault_name=vault_name,
            source_count=len(source_points),
            dest_count=len(dest_points),
            missing_count=len(missing_arns),
            matched_count=len(matched_arns),
            extra_count=len(extra_arns),
        )

    def verify_all_vaults(self, region: str) -> list[VerificationResult]:
        """Verify migration for all vaults.

        Args:
            region: AWS region

        Returns:
            List of VerificationResult for each vault
        """
        source_vaults = self.source_repo.list_vaults(region)
        results = []

        for vault in source_vaults:
            if vault.has_recovery_points():
                result = self.verify_vault(vault.name, region)
                results.append(result)

        return results


# Import at bottom to avoid circular dependency
from dataclasses import dataclass

if __name__ == "__main__":
    # Example usage
    info = file_info()
    print(f"{info['name']} v{info['version']}")
