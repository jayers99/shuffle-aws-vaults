"""Unit tests for migration result domain models."""

from datetime import datetime

import pytest

from shuffle_aws_vaults.domain.migration_result import (
    CopyOperation,
    MigrationBatch,
    MigrationStatus,
)


def test_copy_operation_creation() -> None:
    """Test creating a copy operation."""
    op = CopyOperation(
        source_recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-123",
        source_vault_name="source-vault",
        dest_vault_name="dest-vault",
    )

    assert op.status == MigrationStatus.PENDING
    assert op.started_at is None
    assert op.completed_at is None


def test_copy_operation_start() -> None:
    """Test starting a copy operation."""
    op = CopyOperation(
        source_recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-123",
        source_vault_name="source-vault",
        dest_vault_name="dest-vault",
    )

    op.start("copy-job-123")

    assert op.status == MigrationStatus.IN_PROGRESS
    assert op.copy_job_id == "copy-job-123"
    assert op.started_at is not None


def test_copy_operation_complete() -> None:
    """Test completing a copy operation."""
    op = CopyOperation(
        source_recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-123",
        source_vault_name="source-vault",
        dest_vault_name="dest-vault",
    )

    op.start("copy-job-123")
    op.complete()

    assert op.status == MigrationStatus.COMPLETED
    assert op.completed_at is not None


def test_copy_operation_fail() -> None:
    """Test failing a copy operation."""
    op = CopyOperation(
        source_recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-123",
        source_vault_name="source-vault",
        dest_vault_name="dest-vault",
    )

    op.start("copy-job-123")
    op.fail("Connection timeout")

    assert op.status == MigrationStatus.FAILED
    assert op.error_message == "Connection timeout"
    assert op.completed_at is not None


def test_copy_operation_skip() -> None:
    """Test skipping a copy operation."""
    op = CopyOperation(
        source_recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-123",
        source_vault_name="source-vault",
        dest_vault_name="dest-vault",
    )

    op.skip("Not copyable")

    assert op.status == MigrationStatus.SKIPPED
    assert op.error_message == "Not copyable"


def test_copy_operation_duration() -> None:
    """Test calculating operation duration."""
    op = CopyOperation(
        source_recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-123",
        source_vault_name="source-vault",
        dest_vault_name="dest-vault",
    )

    # No duration before start
    assert op.duration_seconds() is None

    op.start("copy-job-123")
    assert op.duration_seconds() is not None
    assert op.duration_seconds() >= 0  # type: ignore


def test_migration_batch_creation() -> None:
    """Test creating a migration batch."""
    batch = MigrationBatch(batch_id="batch-001")

    assert batch.batch_id == "batch-001"
    assert len(batch.operations) == 0
    assert batch.started_at is None


def test_migration_batch_add_operation() -> None:
    """Test adding operations to a batch."""
    batch = MigrationBatch(batch_id="batch-001")

    op = CopyOperation(
        source_recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-123",
        source_vault_name="source-vault",
        dest_vault_name="dest-vault",
    )

    batch.add_operation(op)
    assert len(batch.operations) == 1


def test_migration_batch_count_by_status() -> None:
    """Test counting operations by status."""
    batch = MigrationBatch(batch_id="batch-001")

    op1 = CopyOperation(
        source_recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-1",
        source_vault_name="source-vault",
        dest_vault_name="dest-vault",
    )
    op2 = CopyOperation(
        source_recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-2",
        source_vault_name="source-vault",
        dest_vault_name="dest-vault",
    )

    op1.start("job-1")
    op1.complete()
    op2.start("job-2")

    batch.add_operation(op1)
    batch.add_operation(op2)

    assert batch.count_by_status(MigrationStatus.COMPLETED) == 1
    assert batch.count_by_status(MigrationStatus.IN_PROGRESS) == 1
    assert batch.count_by_status(MigrationStatus.PENDING) == 0


def test_migration_batch_success_rate() -> None:
    """Test calculating batch success rate."""
    batch = MigrationBatch(batch_id="batch-001")

    op1 = CopyOperation(
        source_recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-1",
        source_vault_name="source-vault",
        dest_vault_name="dest-vault",
    )
    op2 = CopyOperation(
        source_recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-2",
        source_vault_name="source-vault",
        dest_vault_name="dest-vault",
    )
    op3 = CopyOperation(
        source_recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-3",
        source_vault_name="source-vault",
        dest_vault_name="dest-vault",
    )

    op1.start("job-1")
    op1.complete()
    op2.start("job-2")
    op2.complete()
    op3.start("job-3")
    op3.fail("Error")

    batch.add_operation(op1)
    batch.add_operation(op2)
    batch.add_operation(op3)

    assert batch.success_rate() == 66.67  # 2 out of 3


def test_migration_batch_is_complete() -> None:
    """Test checking if batch is complete."""
    batch = MigrationBatch(batch_id="batch-001")

    op1 = CopyOperation(
        source_recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-1",
        source_vault_name="source-vault",
        dest_vault_name="dest-vault",
    )
    op2 = CopyOperation(
        source_recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-2",
        source_vault_name="source-vault",
        dest_vault_name="dest-vault",
    )

    batch.add_operation(op1)
    batch.add_operation(op2)

    assert batch.is_complete() is False  # Both pending

    op1.start("job-1")
    assert batch.is_complete() is False  # One in progress

    op1.complete()
    op2.skip("Skipped")
    assert batch.is_complete() is True  # All finished
