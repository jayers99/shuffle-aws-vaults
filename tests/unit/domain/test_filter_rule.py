"""Unit tests for FilterRule domain model."""

from datetime import datetime, timezone

import pytest

from shuffle_aws_vaults.domain.filter_rule import FilterCriteria, FilterRule, FilterRuleSet
from shuffle_aws_vaults.domain.recovery_point import RecoveryPoint


def test_filter_rule_resource_type(sample_recovery_point: RecoveryPoint) -> None:
    """Test filtering by resource type."""
    rule = FilterRule(FilterCriteria.RESOURCE_TYPE, "EBS", include=True)
    assert rule.matches(sample_recovery_point) is True

    rule_exclude = FilterRule(FilterCriteria.RESOURCE_TYPE, "RDS", include=True)
    assert rule_exclude.matches(sample_recovery_point) is False


def test_filter_rule_status(sample_recovery_point: RecoveryPoint) -> None:
    """Test filtering by status."""
    rule = FilterRule(FilterCriteria.STATUS, "COMPLETED", include=True)
    assert rule.matches(sample_recovery_point) is True

    rule_partial = FilterRule(FilterCriteria.STATUS, "PARTIAL", include=True)
    assert rule_partial.matches(sample_recovery_point) is False


def test_filter_rule_min_age_days() -> None:
    """Test filtering by minimum age."""
    old_rp = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-old",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-old",
        resource_type="EBS",
        creation_date=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        completion_date=datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc),
        status="COMPLETED",
        size_bytes=10 * 1024**3,
        backup_job_id="job-old",
    )

    rule = FilterRule(FilterCriteria.MIN_AGE_DAYS, 30, include=True)
    assert rule.matches(old_rp) is True


def test_filter_rule_size_gb(sample_recovery_point: RecoveryPoint) -> None:
    """Test filtering by size."""
    rule_min = FilterRule(FilterCriteria.MIN_SIZE_GB, 5.0, include=True)
    assert rule_min.matches(sample_recovery_point) is True

    rule_max = FilterRule(FilterCriteria.MAX_SIZE_GB, 15.0, include=True)
    assert rule_max.matches(sample_recovery_point) is True

    rule_too_small = FilterRule(FilterCriteria.MIN_SIZE_GB, 20.0, include=True)
    assert rule_too_small.matches(sample_recovery_point) is False


def test_filter_rule_vault_pattern(sample_recovery_point: RecoveryPoint) -> None:
    """Test filtering by vault name pattern."""
    rule_exact = FilterRule(FilterCriteria.VAULT_NAME_PATTERN, "test-vault", include=True)
    assert rule_exact.matches(sample_recovery_point) is True

    rule_wildcard = FilterRule(FilterCriteria.VAULT_NAME_PATTERN, "test-*", include=True)
    assert rule_wildcard.matches(sample_recovery_point) is True

    rule_no_match = FilterRule(FilterCriteria.VAULT_NAME_PATTERN, "prod-*", include=True)
    assert rule_no_match.matches(sample_recovery_point) is False


def test_filter_rule_exclude_mode(sample_recovery_point: RecoveryPoint) -> None:
    """Test filter rule in exclude mode."""
    rule = FilterRule(FilterCriteria.RESOURCE_TYPE, "EBS", include=False)
    assert rule.matches(sample_recovery_point) is False  # Excluded

    rule_other = FilterRule(FilterCriteria.RESOURCE_TYPE, "RDS", include=False)
    assert rule_other.matches(sample_recovery_point) is True  # Not RDS, so included


def test_filter_rule_set_match_all(sample_recovery_point: RecoveryPoint) -> None:
    """Test FilterRuleSet with match_all=True."""
    rules = [
        FilterRule(FilterCriteria.STATUS, "COMPLETED", include=True),
        FilterRule(FilterCriteria.RESOURCE_TYPE, "EBS", include=True),
    ]
    rule_set = FilterRuleSet(rules=rules, match_all=True)

    assert rule_set.should_include(sample_recovery_point) is True

    # Add rule that doesn't match
    rule_set.add_rule(FilterRule(FilterCriteria.RESOURCE_TYPE, "RDS", include=True))
    assert rule_set.should_include(sample_recovery_point) is False


def test_filter_rule_set_match_any(sample_recovery_point: RecoveryPoint) -> None:
    """Test FilterRuleSet with match_all=False."""
    rules = [
        FilterRule(FilterCriteria.RESOURCE_TYPE, "RDS", include=True),
        FilterRule(FilterCriteria.RESOURCE_TYPE, "EBS", include=True),
    ]
    rule_set = FilterRuleSet(rules=rules, match_all=False)

    assert rule_set.should_include(sample_recovery_point) is True  # Matches EBS


def test_filter_rule_set_empty() -> None:
    """Test FilterRuleSet with no rules includes everything."""
    rule_set = FilterRuleSet(rules=[], match_all=True)

    rp = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-any",
        backup_vault_name="any-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-any",
        resource_type="EBS",
        creation_date=datetime.now(tz=timezone.utc),
        completion_date=datetime.now(tz=timezone.utc),
        status="COMPLETED",
        size_bytes=1024,
        backup_job_id="job-any",
    )

    assert rule_set.should_include(rp) is True


def test_filter_rule_apmid_in_set_match() -> None:
    """Test filtering by APMID when value is in allowed set."""
    rp = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-1",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-1",
        resource_type="EBS",
        creation_date=datetime.now(tz=timezone.utc),
        completion_date=datetime.now(tz=timezone.utc),
        status="COMPLETED",
        size_bytes=10 * 1024**3,
        backup_job_id="job-1",
        metadata={"APMID": "APP001", "Environment": "Production"},
    )

    rule = FilterRule(FilterCriteria.APMID_IN_SET, "APP001,APP002,APP003", include=True)
    assert rule.matches(rp) is True


def test_filter_rule_apmid_in_set_no_match() -> None:
    """Test filtering by APMID when value is not in allowed set."""
    rp = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-2",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-2",
        resource_type="EBS",
        creation_date=datetime.now(tz=timezone.utc),
        completion_date=datetime.now(tz=timezone.utc),
        status="COMPLETED",
        size_bytes=10 * 1024**3,
        backup_job_id="job-2",
        metadata={"APMID": "APP999", "Environment": "Production"},
    )

    rule = FilterRule(FilterCriteria.APMID_IN_SET, "APP001,APP002,APP003", include=True)
    assert rule.matches(rp) is False


def test_filter_rule_apmid_missing_metadata() -> None:
    """Test filtering by APMID when recovery point has no APMID metadata."""
    rp = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-3",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-3",
        resource_type="EBS",
        creation_date=datetime.now(tz=timezone.utc),
        completion_date=datetime.now(tz=timezone.utc),
        status="COMPLETED",
        size_bytes=10 * 1024**3,
        backup_job_id="job-3",
        metadata={"Environment": "Production"},  # No APMID
    )

    rule = FilterRule(FilterCriteria.APMID_IN_SET, "APP001,APP002", include=True)
    assert rule.matches(rp) is False  # Missing APMID should not match


def test_filter_rule_apmid_no_metadata() -> None:
    """Test filtering by APMID when recovery point has no metadata at all."""
    rp = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-4",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-4",
        resource_type="EBS",
        creation_date=datetime.now(tz=timezone.utc),
        completion_date=datetime.now(tz=timezone.utc),
        status="COMPLETED",
        size_bytes=10 * 1024**3,
        backup_job_id="job-4",
    )

    rule = FilterRule(FilterCriteria.APMID_IN_SET, "APP001,APP002", include=True)
    assert rule.matches(rp) is False  # No metadata should not match


def test_filter_rule_apmid_whitespace_handling() -> None:
    """Test APMID filtering handles whitespace in comma-separated list."""
    rp = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-5",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-5",
        resource_type="EBS",
        creation_date=datetime.now(tz=timezone.utc),
        completion_date=datetime.now(tz=timezone.utc),
        status="COMPLETED",
        size_bytes=10 * 1024**3,
        backup_job_id="job-5",
        metadata={"APMID": "APP002"},
    )

    # Test with extra whitespace around APMIDs
    rule = FilterRule(FilterCriteria.APMID_IN_SET, "APP001, APP002 , APP003", include=True)
    assert rule.matches(rp) is True


def test_filter_rule_apmid_not_in_set_match() -> None:
    """Test excluding APMIDs - recovery point passes when APMID not in excluded set."""
    rp = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-6",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-6",
        resource_type="EBS",
        creation_date=datetime.now(tz=timezone.utc),
        completion_date=datetime.now(tz=timezone.utc),
        status="COMPLETED",
        size_bytes=10 * 1024**3,
        backup_job_id="job-6",
        metadata={"APMID": "APP999", "Environment": "Production"},
    )

    # APP999 is not in the excluded set, so it should pass
    rule = FilterRule(FilterCriteria.APMID_NOT_IN_SET, "APP001,APP002,APP003", include=True)
    assert rule.matches(rp) is True


def test_filter_rule_apmid_not_in_set_no_match() -> None:
    """Test excluding APMIDs - recovery point is excluded when APMID is in excluded set."""
    rp = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-7",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-7",
        resource_type="EBS",
        creation_date=datetime.now(tz=timezone.utc),
        completion_date=datetime.now(tz=timezone.utc),
        status="COMPLETED",
        size_bytes=10 * 1024**3,
        backup_job_id="job-7",
        metadata={"APMID": "APP002", "Environment": "Production"},
    )

    # APP002 is in the excluded set, so it should not pass
    rule = FilterRule(FilterCriteria.APMID_NOT_IN_SET, "APP001,APP002,APP003", include=True)
    assert rule.matches(rp) is False


def test_filter_rule_apmid_not_in_set_missing_metadata() -> None:
    """Test excluding APMIDs when recovery point has no APMID metadata - should pass."""
    rp = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-8",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-8",
        resource_type="EBS",
        creation_date=datetime.now(tz=timezone.utc),
        completion_date=datetime.now(tz=timezone.utc),
        status="COMPLETED",
        size_bytes=10 * 1024**3,
        backup_job_id="job-8",
        metadata={"Environment": "Production"},  # No APMID
    )

    # Missing APMID should pass (not in excluded set)
    rule = FilterRule(FilterCriteria.APMID_NOT_IN_SET, "APP001,APP002", include=True)
    assert rule.matches(rp) is True


def test_filter_rule_apmid_not_in_set_no_metadata() -> None:
    """Test excluding APMIDs when recovery point has no metadata at all - should pass."""
    rp = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-9",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-9",
        resource_type="EBS",
        creation_date=datetime.now(tz=timezone.utc),
        completion_date=datetime.now(tz=timezone.utc),
        status="COMPLETED",
        size_bytes=10 * 1024**3,
        backup_job_id="job-9",
    )

    # No metadata should pass (not in excluded set)
    rule = FilterRule(FilterCriteria.APMID_NOT_IN_SET, "APP001,APP002", include=True)
    assert rule.matches(rp) is True


def test_filter_rule_apmid_not_in_set_whitespace_handling() -> None:
    """Test APMID exclusion handles whitespace in comma-separated list."""
    rp = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-10",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-10",
        resource_type="EBS",
        creation_date=datetime.now(tz=timezone.utc),
        completion_date=datetime.now(tz=timezone.utc),
        status="COMPLETED",
        size_bytes=10 * 1024**3,
        backup_job_id="job-10",
        metadata={"APMID": "APP002"},
    )

    # Test with extra whitespace around APMIDs - APP002 should be excluded
    rule = FilterRule(FilterCriteria.APMID_NOT_IN_SET, "APP001, APP002 , APP003", include=True)
    assert rule.matches(rp) is False


def test_filter_rule_combined_allowed_and_excluded_apmids() -> None:
    """Test combining allowed and excluded APMID filters."""
    # Create recovery points with different APMIDs
    rp_allowed = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-11",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-11",
        resource_type="EBS",
        creation_date=datetime.now(tz=timezone.utc),
        completion_date=datetime.now(tz=timezone.utc),
        status="COMPLETED",
        size_bytes=10 * 1024**3,
        backup_job_id="job-11",
        metadata={"APMID": "APP001"},
    )

    rp_excluded = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-12",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-12",
        resource_type="EBS",
        creation_date=datetime.now(tz=timezone.utc),
        completion_date=datetime.now(tz=timezone.utc),
        status="COMPLETED",
        size_bytes=10 * 1024**3,
        backup_job_id="job-12",
        metadata={"APMID": "APP999"},
    )

    rp_not_in_allowed = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-13",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-13",
        resource_type="EBS",
        creation_date=datetime.now(tz=timezone.utc),
        completion_date=datetime.now(tz=timezone.utc),
        status="COMPLETED",
        size_bytes=10 * 1024**3,
        backup_job_id="job-13",
        metadata={"APMID": "APP005"},
    )

    # Create rule set with both allowed and excluded filters
    rules = FilterRuleSet(
        rules=[
            FilterRule(FilterCriteria.APMID_IN_SET, "APP001,APP002,APP003", include=True),
            FilterRule(FilterCriteria.APMID_NOT_IN_SET, "APP999", include=True),
        ],
        match_all=True,
    )

    # APP001 is in allowed set and not in excluded set - should pass
    assert rules.should_include(rp_allowed) is True

    # APP999 is not in allowed set - should fail (doesn't matter if excluded)
    assert rules.should_include(rp_excluded) is False

    # APP005 is not in allowed set - should fail
    assert rules.should_include(rp_not_in_allowed) is False
