#!/usr/bin/env python3
"""
Service for filtering recovery points.

Applies filter rules to recovery points to determine which should be migrated.
"""

from shuffle_aws_vaults.domain.filter_rule import FilterRuleSet
from shuffle_aws_vaults.domain.recovery_point import RecoveryPoint

__version__ = "0.1.0"
__author__ = "John Ayers"


def file_info() -> dict[str, str]:
    """Return metadata about this module.

    Returns:
        Dictionary containing module metadata
    """
    return {
        "name": "filter_service",
        "description": "Service for filtering recovery points",
        "version": __version__,
        "author": __author__,
        "last_updated": "2025-12-07",
    }


class FilterService:
    """Application service for filtering operations."""

    def __init__(self, filter_rules: FilterRuleSet) -> None:
        """Initialize the filter service.

        Args:
            filter_rules: Set of filter rules to apply
        """
        self.filter_rules = filter_rules

    def apply_filters(
        self, recovery_points: list[RecoveryPoint]
    ) -> tuple[list[RecoveryPoint], list[RecoveryPoint]]:
        """Apply filter rules to recovery points.

        Args:
            recovery_points: List of recovery points to filter

        Returns:
            Tuple of (included_points, excluded_points)
        """
        included = []
        excluded = []

        for rp in recovery_points:
            if self.filter_rules.should_include(rp):
                included.append(rp)
            else:
                excluded.append(rp)

        return included, excluded

    def get_filter_summary(self, recovery_points: list[RecoveryPoint]) -> dict[str, int | float]:
        """Get summary of filter results.

        Args:
            recovery_points: List of recovery points to analyze

        Returns:
            Dictionary with filter statistics
        """
        included, excluded = self.apply_filters(recovery_points)

        total_size_included = sum(rp.size_bytes for rp in included)
        total_size_excluded = sum(rp.size_bytes for rp in excluded)

        return {
            "total_count": len(recovery_points),
            "included_count": len(included),
            "excluded_count": len(excluded),
            "inclusion_rate_percent": round(
                (len(included) / len(recovery_points) * 100) if recovery_points else 0, 2
            ),
            "total_size_gb_included": round(total_size_included / (1024**3), 2),
            "total_size_gb_excluded": round(total_size_excluded / (1024**3), 2),
        }


if __name__ == "__main__":
    # Example usage
    info = file_info()
    print(f"{info['name']} v{info['version']}")
