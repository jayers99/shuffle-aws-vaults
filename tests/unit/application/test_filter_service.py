"""Unit tests for FilterService."""

from datetime import datetime, timezone

import pytest

from shuffle_aws_vaults.application.filter_service import FilterService
from shuffle_aws_vaults.domain.filter_rule import FilterCriteria, FilterRule, FilterRuleSet
from shuffle_aws_vaults.domain.recovery_point import RecoveryPoint


def test_filter_service_apply_filters() -> None:
    """Test applying filters to recovery points."""
    # Create recovery points with different resource types
    rp_ebs = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-ebs",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-1",
        resource_type="EBS",
        creation_date=datetime.now(tz=timezone.utc),
        completion_date=datetime.now(tz=timezone.utc),
        status="COMPLETED",
        size_bytes=10 * 1024**3,
        backup_job_id="job-1",
    )

    rp_rds = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-rds",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:rds:us-east-1:123456789012:db:mydb",
        resource_type="RDS",
        creation_date=datetime.now(tz=timezone.utc),
        completion_date=datetime.now(tz=timezone.utc),
        status="COMPLETED",
        size_bytes=20 * 1024**3,
        backup_job_id="job-2",
    )

    # Filter for EBS only
    rules = FilterRuleSet(
        rules=[FilterRule(FilterCriteria.RESOURCE_TYPE, "EBS", include=True)]
    )
    service = FilterService(rules)

    included, excluded = service.apply_filters([rp_ebs, rp_rds])

    assert len(included) == 1
    assert len(excluded) == 1
    assert included[0].resource_type == "EBS"
    assert excluded[0].resource_type == "RDS"


def test_filter_service_apmid_filtering() -> None:
    """Test filtering recovery points by APMID."""
    # Create recovery points with different APMIDs
    rp_app001 = RecoveryPoint(
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

    rp_app002 = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-2",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-2",
        resource_type="EBS",
        creation_date=datetime.now(tz=timezone.utc),
        completion_date=datetime.now(tz=timezone.utc),
        status="COMPLETED",
        size_bytes=15 * 1024**3,
        backup_job_id="job-2",
        metadata={"APMID": "APP002", "Environment": "Production"},
    )

    rp_app999 = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-3",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-3",
        resource_type="EBS",
        creation_date=datetime.now(tz=timezone.utc),
        completion_date=datetime.now(tz=timezone.utc),
        status="COMPLETED",
        size_bytes=5 * 1024**3,
        backup_job_id="job-3",
        metadata={"APMID": "APP999", "Environment": "Dev"},
    )

    rp_no_apmid = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-4",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-4",
        resource_type="EBS",
        creation_date=datetime.now(tz=timezone.utc),
        completion_date=datetime.now(tz=timezone.utc),
        status="COMPLETED",
        size_bytes=8 * 1024**3,
        backup_job_id="job-4",
        metadata={"Environment": "Production"},
    )

    # Filter for APP001 and APP002 only
    rules = FilterRuleSet(
        rules=[FilterRule(FilterCriteria.APMID_IN_SET, "APP001,APP002", include=True)]
    )
    service = FilterService(rules)

    included, excluded = service.apply_filters([rp_app001, rp_app002, rp_app999, rp_no_apmid])

    assert len(included) == 2
    assert len(excluded) == 2
    assert rp_app001 in included
    assert rp_app002 in included
    assert rp_app999 in excluded
    assert rp_no_apmid in excluded


def test_filter_service_get_summary() -> None:
    """Test getting filter summary statistics."""
    rp1 = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-1",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-1",
        resource_type="EBS",
        creation_date=datetime.now(tz=timezone.utc),
        completion_date=datetime.now(tz=timezone.utc),
        status="COMPLETED",
        size_bytes=10 * 1024**3,
        backup_job_id="job-1",
        metadata={"APMID": "APP001"},
    )

    rp2 = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-2",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-2",
        resource_type="RDS",
        creation_date=datetime.now(tz=timezone.utc),
        completion_date=datetime.now(tz=timezone.utc),
        status="COMPLETED",
        size_bytes=20 * 1024**3,
        backup_job_id="job-2",
        metadata={"APMID": "APP002"},
    )

    rules = FilterRuleSet(
        rules=[FilterRule(FilterCriteria.APMID_IN_SET, "APP001", include=True)]
    )
    service = FilterService(rules)

    summary = service.get_filter_summary([rp1, rp2])

    assert summary["total_count"] == 2
    assert summary["included_count"] == 1
    assert summary["excluded_count"] == 1
    assert summary["inclusion_rate_percent"] == 50.0
    assert summary["total_size_gb_included"] == 10.0
    assert summary["total_size_gb_excluded"] == 20.0


def test_filter_service_no_filters() -> None:
    """Test that empty filter set includes everything."""
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
    )

    rules = FilterRuleSet(rules=[])
    service = FilterService(rules)

    included, excluded = service.apply_filters([rp])

    assert len(included) == 1
    assert len(excluded) == 0


def test_filter_service_multiple_rules() -> None:
    """Test filtering with multiple rules (match all)."""
    rp_match = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-1",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-1",
        resource_type="EBS",
        creation_date=datetime.now(tz=timezone.utc),
        completion_date=datetime.now(tz=timezone.utc),
        status="COMPLETED",
        size_bytes=10 * 1024**3,
        backup_job_id="job-1",
        metadata={"APMID": "APP001"},
    )

    rp_no_match = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-2",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:rds:us-east-1:123456789012:db:mydb",
        resource_type="RDS",
        creation_date=datetime.now(tz=timezone.utc),
        completion_date=datetime.now(tz=timezone.utc),
        status="COMPLETED",
        size_bytes=20 * 1024**3,
        backup_job_id="job-2",
        metadata={"APMID": "APP001"},
    )

    # Both rules must match (EBS AND APP001)
    rules = FilterRuleSet(
        rules=[
            FilterRule(FilterCriteria.RESOURCE_TYPE, "EBS", include=True),
            FilterRule(FilterCriteria.APMID_IN_SET, "APP001", include=True),
        ],
        match_all=True,
    )
    service = FilterService(rules)

    included, excluded = service.apply_filters([rp_match, rp_no_match])

    assert len(included) == 1
    assert len(excluded) == 1
    assert included[0].resource_type == "EBS"
