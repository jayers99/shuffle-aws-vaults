#!/usr/bin/env python3
"""
Domain model for filter rules.

Provides business logic for filtering recovery points based on various criteria.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from shuffle_aws_vaults.domain.recovery_point import RecoveryPoint

__version__ = "0.1.0"
__author__ = "John Ayers"


def file_info() -> dict[str, str]:
    """Return metadata about this module.

    Returns:
        Dictionary containing module metadata
    """
    return {
        "name": "filter_rule",
        "description": "Domain model for filter rules",
        "version": __version__,
        "author": __author__,
        "last_updated": "2025-12-07",
    }


class FilterCriteria(Enum):
    """Enumeration of available filter criteria."""

    RESOURCE_TYPE = "resource_type"
    MIN_AGE_DAYS = "min_age_days"
    MAX_AGE_DAYS = "max_age_days"
    MIN_SIZE_GB = "min_size_gb"
    MAX_SIZE_GB = "max_size_gb"
    STATUS = "status"
    VAULT_NAME_PATTERN = "vault_name_pattern"


@dataclass(frozen=True)
class FilterRule:
    """Immutable domain model for a single filter rule.

    Attributes:
        criteria: Type of filter criteria
        value: Value to filter against
        include: If True, include matches; if False, exclude matches
    """

    criteria: FilterCriteria
    value: str | int | float
    include: bool = True

    def matches(self, recovery_point: RecoveryPoint) -> bool:
        """Check if recovery point matches this filter rule.

        Args:
            recovery_point: Recovery point to evaluate

        Returns:
            True if recovery point matches the criteria
        """
        match self.criteria:
            case FilterCriteria.RESOURCE_TYPE:
                result = recovery_point.resource_type == self.value
            case FilterCriteria.MIN_AGE_DAYS:
                result = recovery_point.age_days() >= int(self.value)
            case FilterCriteria.MAX_AGE_DAYS:
                result = recovery_point.age_days() <= int(self.value)
            case FilterCriteria.MIN_SIZE_GB:
                result = recovery_point.size_gb() >= float(self.value)
            case FilterCriteria.MAX_SIZE_GB:
                result = recovery_point.size_gb() <= float(self.value)
            case FilterCriteria.STATUS:
                result = recovery_point.status == self.value
            case FilterCriteria.VAULT_NAME_PATTERN:
                pattern = str(self.value)
                if "*" in pattern:
                    prefix = pattern.rstrip("*")
                    result = recovery_point.backup_vault_name.startswith(prefix)
                else:
                    result = recovery_point.backup_vault_name == pattern
            case _:
                result = False

        return result if self.include else not result


@dataclass
class FilterRuleSet:
    """Mutable collection of filter rules with evaluation logic.

    Attributes:
        rules: List of filter rules to apply
        match_all: If True, all rules must match; if False, any rule matching is sufficient
    """

    rules: list[FilterRule]
    match_all: bool = True

    def add_rule(self, rule: FilterRule) -> None:
        """Add a filter rule to the set.

        Args:
            rule: Filter rule to add
        """
        self.rules.append(rule)

    def should_include(self, recovery_point: RecoveryPoint) -> bool:
        """Determine if recovery point should be included based on all rules.

        Args:
            recovery_point: Recovery point to evaluate

        Returns:
            True if recovery point passes the filter
        """
        if not self.rules:
            return True

        if self.match_all:
            return all(rule.matches(recovery_point) for rule in self.rules)
        else:
            return any(rule.matches(recovery_point) for rule in self.rules)


if __name__ == "__main__":
    # Example usage
    info = file_info()
    print(f"{info['name']} v{info['version']}")
