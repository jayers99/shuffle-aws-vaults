#!/usr/bin/env python3
"""
Repository for persisting state to disk.

Provides atomic file operations for saving and loading migration state.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from shuffle_aws_vaults.domain.state import (
    CopyOperation,
    CopyState,
    InventoryState,
    RecoveryPointRef,
)

__version__ = "0.1.0"
__author__ = "John Ayers"


def file_info() -> dict[str, str]:
    """Return metadata about this module.

    Returns:
        Dictionary containing module metadata
    """
    return {
        "name": "state_repository",
        "description": "Repository for state persistence",
        "version": __version__,
        "author": __author__,
        "last_updated": "2025-12-07",
    }


class StateRepository:
    """Repository for persisting state to JSON files."""

    SUPPORTED_SCHEMA_VERSIONS = ["1.0"]

    def __init__(self, state_file_path: str = ".shuffle-state.json") -> None:
        """Initialize the state repository.

        Args:
            state_file_path: Path to the state file
        """
        self.state_file_path = Path(state_file_path)

    def save_copy_state(self, state: CopyState) -> None:
        """Save copy state to disk atomically.

        Args:
            state: Copy state to save
        """
        # Update timestamp
        state.timestamp = datetime.now(datetime.now().astimezone().tzinfo)

        # Serialize to JSON
        state_dict = self._copy_state_to_dict(state)

        # Write atomically (temp file + rename)
        temp_file = self.state_file_path.with_suffix(".tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(state_dict, f, indent=2, default=str)

            # Atomic rename
            temp_file.replace(self.state_file_path)
        except Exception:
            # Clean up temp file on error
            if temp_file.exists():
                temp_file.unlink()
            raise

    def load_copy_state(self) -> CopyState | None:
        """Load copy state from disk.

        Returns:
            Copy state if file exists and is valid, None otherwise

        Raises:
            ValueError: If state file has unsupported schema version
        """
        if not self.state_file_path.exists():
            return None

        with open(self.state_file_path, encoding="utf-8") as f:
            state_dict = json.load(f)

        # Validate schema version
        schema_version = state_dict.get("schema_version", "1.0")
        if schema_version not in self.SUPPORTED_SCHEMA_VERSIONS:
            raise ValueError(
                f"Unsupported schema version: {schema_version}. "
                f"Supported versions: {self.SUPPORTED_SCHEMA_VERSIONS}"
            )

        # Deserialize from dict
        return self._dict_to_copy_state(state_dict)

    def save_inventory_state(self, state: InventoryState) -> None:
        """Save inventory state to disk atomically.

        Args:
            state: Inventory state to save
        """
        # Update timestamp
        state.timestamp = datetime.now(datetime.now().astimezone().tzinfo)

        # Serialize to JSON
        state_dict = self._inventory_state_to_dict(state)

        # Write atomically (temp file + rename)
        temp_file = self.state_file_path.with_suffix(".tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(state_dict, f, indent=2, default=str)

            # Atomic rename
            temp_file.replace(self.state_file_path)
        except Exception:
            # Clean up temp file on error
            if temp_file.exists():
                temp_file.unlink()
            raise

    def load_inventory_state(self) -> InventoryState | None:
        """Load inventory state from disk.

        Returns:
            Inventory state if file exists, None otherwise
        """
        if not self.state_file_path.exists():
            return None

        with open(self.state_file_path, encoding="utf-8") as f:
            state_dict = json.load(f)

        # Deserialize from dict
        return self._dict_to_inventory_state(state_dict)

    def delete_state(self) -> None:
        """Delete the state file if it exists."""
        if self.state_file_path.exists():
            self.state_file_path.unlink()

    def _copy_state_to_dict(self, state: CopyState) -> dict[str, Any]:
        """Convert CopyState to dictionary for JSON serialization.

        Args:
            state: Copy state to convert

        Returns:
            Dictionary representation
        """
        return {
            "source_account": state.source_account,
            "dest_account": state.dest_account,
            "vault_name": state.vault_name,
            "schema_version": state.schema_version,
            "timestamp": state.timestamp.isoformat(),
            "operations": [
                {
                    "recovery_point_arn": op.recovery_point_arn,
                    "resource_arn": op.resource_arn,
                    "status": op.status,
                    "started_at": op.started_at.isoformat() if op.started_at else None,
                    "completed_at": op.completed_at.isoformat() if op.completed_at else None,
                    "error_message": op.error_message,
                }
                for op in state.operations
            ],
        }

    def _dict_to_copy_state(self, state_dict: dict[str, Any]) -> CopyState:
        """Convert dictionary to CopyState.

        Args:
            state_dict: Dictionary representation

        Returns:
            CopyState instance
        """
        operations = [
            CopyOperation(
                recovery_point_arn=op["recovery_point_arn"],
                resource_arn=op["resource_arn"],
                status=op["status"],
                started_at=datetime.fromisoformat(op["started_at"]) if op["started_at"] else None,
                completed_at=(
                    datetime.fromisoformat(op["completed_at"]) if op["completed_at"] else None
                ),
                error_message=op.get("error_message"),
            )
            for op in state_dict["operations"]
        ]

        return CopyState(
            source_account=state_dict["source_account"],
            dest_account=state_dict["dest_account"],
            vault_name=state_dict["vault_name"],
            operations=operations,
            schema_version=state_dict.get("schema_version", "1.0"),
            timestamp=datetime.fromisoformat(state_dict["timestamp"]),
        )

    def _inventory_state_to_dict(self, state: InventoryState) -> dict[str, Any]:
        """Convert InventoryState to dictionary for JSON serialization.

        Args:
            state: Inventory state to convert

        Returns:
            Dictionary representation
        """
        return {
            "vault_name": state.vault_name,
            "total_count": state.total_count,
            "total_size_bytes": state.total_size_bytes,
            "timestamp": state.timestamp.isoformat(),
            "recovery_points": [
                {
                    "recovery_point_arn": ref.recovery_point_arn,
                    "resource_arn": ref.resource_arn,
                    "vault_name": ref.vault_name,
                    "size_bytes": ref.size_bytes,
                }
                for ref in state.recovery_points
            ],
        }

    def _dict_to_inventory_state(self, state_dict: dict[str, Any]) -> InventoryState:
        """Convert dictionary to InventoryState.

        Args:
            state_dict: Dictionary representation

        Returns:
            InventoryState instance
        """
        recovery_points = [
            RecoveryPointRef(
                recovery_point_arn=ref["recovery_point_arn"],
                resource_arn=ref["resource_arn"],
                vault_name=ref["vault_name"],
                size_bytes=ref["size_bytes"],
            )
            for ref in state_dict["recovery_points"]
        ]

        return InventoryState(
            vault_name=state_dict["vault_name"],
            recovery_points=recovery_points,
            total_count=state_dict["total_count"],
            total_size_bytes=state_dict["total_size_bytes"],
            timestamp=datetime.fromisoformat(state_dict["timestamp"]),
        )


if __name__ == "__main__":
    # Example usage
    info = file_info()
    print(f"{info['name']} v{info['version']}")
