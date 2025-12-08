"""Unit tests for state domain models."""

from datetime import datetime, timezone

import pytest

from shuffle_aws_vaults.domain.state import (
    CopyOperation,
    CopyState,
    InventoryState,
    RecoveryPointRef,
)


def test_recovery_point_ref_creation() -> None:
    """Test creating a recovery point reference."""
    ref = RecoveryPointRef(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-1",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-1",
        vault_name="test-vault",
        size_bytes=10 * 1024**3,
    )

    assert ref.recovery_point_arn.startswith("arn:aws:backup")
    assert ref.vault_name == "test-vault"
    assert ref.size_bytes == 10 * 1024**3


def test_inventory_state_creation() -> None:
    """Test creating an inventory state."""
    state = InventoryState(vault_name="test-vault")

    assert state.vault_name == "test-vault"
    assert state.total_count == 0
    assert state.total_size_bytes == 0
    assert len(state.recovery_points) == 0


def test_inventory_state_add_recovery_point() -> None:
    """Test adding recovery points to inventory."""
    state = InventoryState(vault_name="test-vault")

    ref1 = RecoveryPointRef(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-1",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-1",
        vault_name="test-vault",
        size_bytes=10 * 1024**3,
    )

    ref2 = RecoveryPointRef(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-2",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-2",
        vault_name="test-vault",
        size_bytes=20 * 1024**3,
    )

    state.add_recovery_point(ref1)
    state.add_recovery_point(ref2)

    assert state.total_count == 2
    assert state.total_size_bytes == 30 * 1024**3
    assert len(state.recovery_points) == 2


def test_copy_operation_creation() -> None:
    """Test creating a copy operation."""
    op = CopyOperation(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-1",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-1",
    )

    assert op.status == "pending"
    assert op.started_at is None
    assert op.completed_at is None
    assert op.error_message is None


def test_copy_state_creation() -> None:
    """Test creating a copy state."""
    state = CopyState(
        source_account="111111111111",
        dest_account="222222222222",
        vault_name="test-vault",
    )

    assert state.source_account == "111111111111"
    assert state.dest_account == "222222222222"
    assert state.vault_name == "test-vault"
    assert state.schema_version == "1.0"
    assert len(state.operations) == 0


def test_copy_state_add_operation() -> None:
    """Test adding operations to copy state."""
    state = CopyState(
        source_account="111111111111",
        dest_account="222222222222",
        vault_name="test-vault",
    )

    op = CopyOperation(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-1",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-1",
    )

    state.add_operation(op)

    assert len(state.operations) == 1
    assert state.operations[0].status == "pending"


def test_copy_state_get_operation() -> None:
    """Test getting a copy operation by ARN."""
    state = CopyState(
        source_account="111111111111",
        dest_account="222222222222",
        vault_name="test-vault",
    )

    op1 = CopyOperation(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-1",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-1",
    )

    op2 = CopyOperation(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-2",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-2",
        status="completed",
    )

    state.add_operation(op1)
    state.add_operation(op2)

    found_op = state.get_operation("arn:aws:backup:us-east-1:123456789012:recovery-point:rp-2")
    assert found_op is not None
    assert found_op.status == "completed"

    missing_op = state.get_operation("arn:aws:backup:us-east-1:123456789012:recovery-point:rp-999")
    assert missing_op is None


def test_copy_state_count_by_status() -> None:
    """Test counting operations by status."""
    state = CopyState(
        source_account="111111111111",
        dest_account="222222222222",
        vault_name="test-vault",
    )

    state.add_operation(
        CopyOperation(
            recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-1",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-1",
            status="pending",
        )
    )

    state.add_operation(
        CopyOperation(
            recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-2",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-2",
            status="completed",
        )
    )

    state.add_operation(
        CopyOperation(
            recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-3",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-3",
            status="completed",
        )
    )

    assert state.count_by_status("pending") == 1
    assert state.count_by_status("completed") == 2
    assert state.count_by_status("failed") == 0


def test_copy_state_get_pending_operations() -> None:
    """Test getting pending operations."""
    state = CopyState(
        source_account="111111111111",
        dest_account="222222222222",
        vault_name="test-vault",
    )

    state.add_operation(
        CopyOperation(
            recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-1",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-1",
            status="pending",
        )
    )

    state.add_operation(
        CopyOperation(
            recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-2",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-2",
            status="completed",
        )
    )

    pending = state.get_pending_operations()
    assert len(pending) == 1
    assert pending[0].status == "pending"


def test_copy_state_get_failed_operations() -> None:
    """Test getting failed operations."""
    state = CopyState(
        source_account="111111111111",
        dest_account="222222222222",
        vault_name="test-vault",
    )

    state.add_operation(
        CopyOperation(
            recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-1",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-1",
            status="failed",
            error_message="Connection timeout",
        )
    )

    state.add_operation(
        CopyOperation(
            recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-2",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-2",
            status="completed",
        )
    )

    failed = state.get_failed_operations()
    assert len(failed) == 1
    assert failed[0].status == "failed"
    assert failed[0].error_message == "Connection timeout"


def test_copy_state_is_complete() -> None:
    """Test checking if copy state is complete."""
    state = CopyState(
        source_account="111111111111",
        dest_account="222222222222",
        vault_name="test-vault",
    )

    # Empty state is complete
    assert state.is_complete() is True

    # Add pending operation - not complete
    state.add_operation(
        CopyOperation(
            recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-1",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-1",
            status="pending",
        )
    )
    assert state.is_complete() is False

    # Mark as completed - now complete
    state.operations[0].status = "completed"
    assert state.is_complete() is True

    # Add failed operation - still complete (failed is terminal)
    state.add_operation(
        CopyOperation(
            recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-2",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-2",
            status="failed",
        )
    )
    assert state.is_complete() is True
