"""Unit tests for RecoveryPoint domain model."""

from datetime import datetime, timedelta, timezone

import pytest

from shuffle_aws_vaults.domain.recovery_point import RecoveryPoint


def test_recovery_point_creation(sample_recovery_point: RecoveryPoint) -> None:
    """Test creating a recovery point."""
    assert sample_recovery_point.recovery_point_arn.startswith("arn:aws:backup")
    assert sample_recovery_point.backup_vault_name == "test-vault"
    assert sample_recovery_point.resource_type == "EBS"


def test_is_completed(sample_recovery_point: RecoveryPoint) -> None:
    """Test is_completed method."""
    assert sample_recovery_point.is_completed() is True

    incomplete = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-124",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-124",
        resource_type="EBS",
        creation_date=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        completion_date=None,
        status="PARTIAL",
        size_bytes=5 * 1024**3,
        backup_job_id="job-124",
    )
    assert incomplete.is_completed() is False


def test_is_copyable(sample_recovery_point: RecoveryPoint) -> None:
    """Test is_copyable method."""
    assert sample_recovery_point.is_copyable() is True

    # Not completed
    not_completed = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-125",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-125",
        resource_type="EBS",
        creation_date=datetime.now(tz=timezone.utc),
        completion_date=None,
        status="PARTIAL",
        size_bytes=5 * 1024**3,
        backup_job_id="job-125",
    )
    assert not_completed.is_copyable() is False

    # Completed but no completion date
    no_completion_date = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-126",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-126",
        resource_type="EBS",
        creation_date=datetime.now(tz=timezone.utc),
        completion_date=None,
        status="COMPLETED",
        size_bytes=5 * 1024**3,
        backup_job_id="job-126",
    )
    assert no_completion_date.is_copyable() is False


def test_age_days(sample_recovery_point: RecoveryPoint) -> None:
    """Test age_days calculation."""
    reference = datetime(2025, 1, 8, 12, 0, 0, tzinfo=timezone.utc)
    age = sample_recovery_point.age_days(reference)
    assert age == 7  # 7 days from Jan 1 to Jan 8


def test_size_gb(sample_recovery_point: RecoveryPoint) -> None:
    """Test size_gb conversion."""
    assert sample_recovery_point.size_gb() == 10.0


def test_recovery_point_immutability(sample_recovery_point: RecoveryPoint) -> None:
    """Test that recovery points are immutable."""
    with pytest.raises(AttributeError):
        sample_recovery_point.status = "FAILED"  # type: ignore
