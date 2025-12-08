"""Unit tests for StateRepository."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from shuffle_aws_vaults.domain.state import (
    CopyOperation,
    CopyState,
    InventoryState,
    RecoveryPointRef,
)
from shuffle_aws_vaults.infrastructure.state_repository import StateRepository


def test_save_and_load_copy_state(tmp_path: Path) -> None:
    """Test saving and loading copy state."""
    state_file = tmp_path / "test-state.json"
    repo = StateRepository(str(state_file))

    # Create copy state
    state = CopyState(
        source_account="111111111111",
        dest_account="222222222222",
        vault_name="test-vault",
    )

    state.add_operation(
        CopyOperation(
            recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-1",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-1",
            status="completed",
        )
    )

    # Save state
    repo.save_copy_state(state)

    # Verify file exists
    assert state_file.exists()

    # Load state
    loaded_state = repo.load_copy_state()

    assert loaded_state is not None
    assert loaded_state.source_account == "111111111111"
    assert loaded_state.dest_account == "222222222222"
    assert loaded_state.vault_name == "test-vault"
    assert len(loaded_state.operations) == 1
    assert loaded_state.operations[0].status == "completed"


def test_save_copy_state_with_timestamps(tmp_path: Path) -> None:
    """Test that save updates timestamp."""
    state_file = tmp_path / "test-state.json"
    repo = StateRepository(str(state_file))

    state = CopyState(
        source_account="111111111111",
        dest_account="222222222222",
        vault_name="test-vault",
    )

    original_timestamp = state.timestamp

    # Save state (should update timestamp)
    repo.save_copy_state(state)

    # Timestamp should be updated
    assert state.timestamp >= original_timestamp


def test_save_copy_state_atomic_write(tmp_path: Path) -> None:
    """Test that save uses atomic writes."""
    state_file = tmp_path / "test-state.json"
    repo = StateRepository(str(state_file))

    state = CopyState(
        source_account="111111111111",
        dest_account="222222222222",
        vault_name="test-vault",
    )

    # Save state
    repo.save_copy_state(state)

    # Temp file should not exist after successful save
    temp_file = state_file.with_suffix(".tmp")
    assert not temp_file.exists()

    # State file should exist
    assert state_file.exists()


def test_load_copy_state_nonexistent_file(tmp_path: Path) -> None:
    """Test loading from nonexistent file returns None."""
    state_file = tmp_path / "nonexistent.json"
    repo = StateRepository(str(state_file))

    loaded_state = repo.load_copy_state()
    assert loaded_state is None


def test_load_copy_state_with_operations(tmp_path: Path) -> None:
    """Test loading state with multiple operations."""
    state_file = tmp_path / "test-state.json"
    repo = StateRepository(str(state_file))

    state = CopyState(
        source_account="111111111111",
        dest_account="222222222222",
        vault_name="test-vault",
    )

    # Add operations with different statuses
    state.add_operation(
        CopyOperation(
            recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-1",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-1",
            status="completed",
            started_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            completed_at=datetime(2025, 1, 1, 13, 0, 0, tzinfo=timezone.utc),
        )
    )

    state.add_operation(
        CopyOperation(
            recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-2",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-2",
            status="failed",
            error_message="Connection timeout",
        )
    )

    # Save and load
    repo.save_copy_state(state)
    loaded_state = repo.load_copy_state()

    assert loaded_state is not None
    assert len(loaded_state.operations) == 2
    assert loaded_state.operations[0].status == "completed"
    assert loaded_state.operations[0].started_at is not None
    assert loaded_state.operations[1].status == "failed"
    assert loaded_state.operations[1].error_message == "Connection timeout"


def test_save_and_load_inventory_state(tmp_path: Path) -> None:
    """Test saving and loading inventory state."""
    state_file = tmp_path / "inventory.json"
    repo = StateRepository(str(state_file))

    # Create inventory state
    state = InventoryState(vault_name="test-vault")

    state.add_recovery_point(
        RecoveryPointRef(
            recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-1",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-1",
            vault_name="test-vault",
            size_bytes=10 * 1024**3,
        )
    )

    # Save state
    repo.save_inventory_state(state)

    # Verify file exists
    assert state_file.exists()

    # Load state
    loaded_state = repo.load_inventory_state()

    assert loaded_state is not None
    assert loaded_state.vault_name == "test-vault"
    assert loaded_state.total_count == 1
    assert loaded_state.total_size_bytes == 10 * 1024**3
    assert len(loaded_state.recovery_points) == 1


def test_delete_state(tmp_path: Path) -> None:
    """Test deleting state file."""
    state_file = tmp_path / "test-state.json"
    repo = StateRepository(str(state_file))

    # Create and save state
    state = CopyState(
        source_account="111111111111",
        dest_account="222222222222",
        vault_name="test-vault",
    )
    repo.save_copy_state(state)

    # Verify file exists
    assert state_file.exists()

    # Delete state
    repo.delete_state()

    # Verify file is gone
    assert not state_file.exists()


def test_delete_nonexistent_state(tmp_path: Path) -> None:
    """Test deleting nonexistent state file doesn't error."""
    state_file = tmp_path / "nonexistent.json"
    repo = StateRepository(str(state_file))

    # Should not raise
    repo.delete_state()


def test_load_copy_state_unsupported_schema_version(tmp_path: Path) -> None:
    """Test loading state with unsupported schema version raises error."""
    state_file = tmp_path / "bad-schema.json"

    # Create state file with unsupported schema version
    state_dict = {
        "source_account": "111111111111",
        "dest_account": "222222222222",
        "vault_name": "test-vault",
        "schema_version": "99.0",  # Unsupported version
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "operations": [],
    }

    with open(state_file, "w") as f:
        json.dump(state_dict, f)

    repo = StateRepository(str(state_file))

    # Should raise ValueError
    with pytest.raises(ValueError, match="Unsupported schema version"):
        repo.load_copy_state()


def test_save_copy_state_creates_valid_json(tmp_path: Path) -> None:
    """Test that saved state is valid JSON."""
    state_file = tmp_path / "test-state.json"
    repo = StateRepository(str(state_file))

    state = CopyState(
        source_account="111111111111",
        dest_account="222222222222",
        vault_name="test-vault",
    )

    repo.save_copy_state(state)

    # Read and parse JSON
    with open(state_file, "r") as f:
        data = json.load(f)

    # Verify structure
    assert "source_account" in data
    assert "dest_account" in data
    assert "vault_name" in data
    assert "schema_version" in data
    assert "timestamp" in data
    assert "operations" in data
    assert data["schema_version"] == "1.0"


def test_load_inventory_state_nonexistent_file(tmp_path: Path) -> None:
    """Test loading inventory from nonexistent file returns None."""
    state_file = tmp_path / "nonexistent.json"
    repo = StateRepository(str(state_file))

    loaded_state = repo.load_inventory_state()
    assert loaded_state is None
