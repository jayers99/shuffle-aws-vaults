#!/usr/bin/env python3
"""
Service for enriching recovery points with external metadata.

Joins recovery points with CSV metadata by resourceArn.
"""

import logging
from dataclasses import replace
from typing import Protocol

from shuffle_aws_vaults.domain.recovery_point import RecoveryPoint

__version__ = "0.1.0"
__author__ = "John Ayers"

logger = logging.getLogger(__name__)


def file_info() -> dict[str, str]:
    """Return metadata about this module.

    Returns:
        Dictionary containing module metadata
    """
    return {
        "name": "metadata_enrichment_service",
        "description": "Service for enriching recovery points with CSV metadata",
        "version": __version__,
        "author": __author__,
        "last_updated": "2025-12-07",
    }


class MetadataRepository(Protocol):
    """Protocol for metadata repositories."""

    def get_metadata_for_resource(self, resource_arn: str) -> dict[str, str] | None:
        """Get metadata for a resource ARN."""
        ...


class MetadataEnrichmentService:
    """Application service for enriching recovery points with metadata."""

    def __init__(self, metadata_repo: MetadataRepository) -> None:
        """Initialize the enrichment service.

        Args:
            metadata_repo: Repository providing metadata lookup
        """
        self.metadata_repo = metadata_repo

    def enrich_recovery_point(self, recovery_point: RecoveryPoint) -> RecoveryPoint:
        """Enrich a single recovery point with metadata.

        Args:
            recovery_point: Recovery point to enrich

        Returns:
            New RecoveryPoint with metadata populated (or original if no metadata found)
        """
        metadata = self.metadata_repo.get_metadata_for_resource(recovery_point.resource_arn)

        if metadata is None:
            logger.warning(
                f"No metadata found for resource ARN: {recovery_point.resource_arn} "
                f"(recovery point: {recovery_point.recovery_point_arn})"
            )
            return recovery_point

        # Create new RecoveryPoint with enriched metadata (immutable)
        return replace(recovery_point, metadata=metadata)

    def enrich_recovery_points(self, recovery_points: list[RecoveryPoint]) -> list[RecoveryPoint]:
        """Enrich multiple recovery points with metadata.

        Args:
            recovery_points: List of recovery points to enrich

        Returns:
            List of recovery points with metadata enriched
        """
        return [self.enrich_recovery_point(rp) for rp in recovery_points]

    def get_enrichment_stats(self, recovery_points: list[RecoveryPoint]) -> dict[str, int]:
        """Get statistics about metadata enrichment.

        Args:
            recovery_points: List of recovery points (before enrichment)

        Returns:
            Dictionary with enrichment statistics
        """
        enriched = self.enrich_recovery_points(recovery_points)

        total_count = len(recovery_points)
        enriched_count = sum(1 for rp in enriched if rp.metadata)
        missing_count = total_count - enriched_count

        return {
            "total_count": total_count,
            "enriched_count": enriched_count,
            "missing_count": missing_count,
        }


if __name__ == "__main__":
    # Example usage
    info = file_info()
    print(f"{info['name']} v{info['version']}")
