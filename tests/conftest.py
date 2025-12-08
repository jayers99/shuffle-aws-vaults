"""Shared pytest fixtures for shuffle-aws-vaults tests."""

from datetime import datetime, timezone

import pytest

from shuffle_aws_vaults.domain.filter_rule import FilterCriteria, FilterRule, FilterRuleSet
from shuffle_aws_vaults.domain.recovery_point import RecoveryPoint
from shuffle_aws_vaults.domain.vault import Vault


@pytest.fixture
def sample_recovery_point() -> RecoveryPoint:
    """Create a sample recovery point for testing.

    Returns:
        RecoveryPoint instance
    """
    return RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-123",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-123",
        resource_type="EBS",
        creation_date=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        completion_date=datetime(2025, 1, 1, 13, 0, 0, tzinfo=timezone.utc),
        status="COMPLETED",
        size_bytes=10 * 1024**3,  # 10 GB
        backup_job_id="job-123",
    )


@pytest.fixture
def sample_vault() -> Vault:
    """Create a sample vault for testing.

    Returns:
        Vault instance
    """
    return Vault(
        name="test-vault",
        arn="arn:aws:backup:us-east-1:123456789012:backup-vault:test-vault",
        region="us-east-1",
        account_id="123456789012",
        recovery_point_count=5,
        encryption_key_arn="arn:aws:kms:us-east-1:123456789012:key/key-123",
    )


@pytest.fixture
def empty_vault() -> Vault:
    """Create an empty vault for testing.

    Returns:
        Vault instance with no recovery points
    """
    return Vault(
        name="empty-vault",
        arn="arn:aws:backup:us-east-1:123456789012:backup-vault:empty-vault",
        region="us-east-1",
        account_id="123456789012",
        recovery_point_count=0,
    )


@pytest.fixture
def sample_filter_rules() -> FilterRuleSet:
    """Create a sample filter rule set for testing.

    Returns:
        FilterRuleSet instance
    """
    rules = [
        FilterRule(FilterCriteria.STATUS, "COMPLETED", include=True),
        FilterRule(FilterCriteria.MIN_SIZE_GB, 1.0, include=True),
    ]
    return FilterRuleSet(rules=rules, match_all=True)
