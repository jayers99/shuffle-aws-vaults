"""Unit tests for CSVMetadataRepository."""

import tempfile
from pathlib import Path

import pytest

from shuffle_aws_vaults.infrastructure.csv_metadata_repository import CSVMetadataRepository


def test_load_metadata_simple_csv(tmp_path: Path) -> None:
    """Test loading metadata from a simple CSV file."""
    # Arrange
    csv_file = tmp_path / "metadata.csv"
    csv_file.write_text(
        "resourceArn,APMID,Environment\n"
        "arn:aws:ec2:us-east-1:123456789012:volume/vol-1,APP001,Production\n"
        "arn:aws:rds:us-east-1:123456789012:db:mydb,APP002,Development\n"
    )

    repo = CSVMetadataRepository(str(csv_file))

    # Act
    metadata = repo.load_metadata()

    # Assert
    assert len(metadata) == 2
    assert "arn:aws:ec2:us-east-1:123456789012:volume/vol-1" in metadata
    assert metadata["arn:aws:ec2:us-east-1:123456789012:volume/vol-1"]["APMID"] == "APP001"
    assert (
        metadata["arn:aws:ec2:us-east-1:123456789012:volume/vol-1"]["Environment"]
        == "Production"
    )


def test_load_metadata_caches_result(tmp_path: Path) -> None:
    """Test that load_metadata caches the result."""
    # Arrange
    csv_file = tmp_path / "metadata.csv"
    csv_file.write_text("resourceArn,APMID\narn:aws:ec2:us-east-1:123456789012:volume/vol-1,APP001\n")

    repo = CSVMetadataRepository(str(csv_file))

    # Act
    metadata1 = repo.load_metadata()
    metadata2 = repo.load_metadata()

    # Assert
    assert metadata1 is metadata2  # Same object reference (cached)


def test_get_metadata_for_resource(tmp_path: Path) -> None:
    """Test getting metadata for a specific resource."""
    # Arrange
    csv_file = tmp_path / "metadata.csv"
    csv_file.write_text(
        "resourceArn,APMID\n"
        "arn:aws:ec2:us-east-1:123456789012:volume/vol-1,APP001\n"
        "arn:aws:rds:us-east-1:123456789012:db:mydb,APP002\n"
    )

    repo = CSVMetadataRepository(str(csv_file))

    # Act
    metadata = repo.get_metadata_for_resource(
        "arn:aws:ec2:us-east-1:123456789012:volume/vol-1"
    )

    # Assert
    assert metadata is not None
    assert metadata["APMID"] == "APP001"


def test_get_metadata_for_missing_resource(tmp_path: Path) -> None:
    """Test getting metadata for a resource not in CSV."""
    # Arrange
    csv_file = tmp_path / "metadata.csv"
    csv_file.write_text("resourceArn,APMID\narn:aws:ec2:us-east-1:123456789012:volume/vol-1,APP001\n")

    repo = CSVMetadataRepository(str(csv_file))

    # Act
    metadata = repo.get_metadata_for_resource("arn:aws:ec2:us-east-1:999999999999:volume/vol-999")

    # Assert
    assert metadata is None


def test_load_metadata_file_not_found() -> None:
    """Test error handling when CSV file doesn't exist."""
    # Arrange
    repo = CSVMetadataRepository("/nonexistent/file.csv")

    # Act & Assert
    with pytest.raises(FileNotFoundError, match="CSV file not found"):
        repo.load_metadata()


def test_load_metadata_missing_resource_arn_column(tmp_path: Path) -> None:
    """Test error handling when resourceArn column is missing."""
    # Arrange
    csv_file = tmp_path / "metadata.csv"
    csv_file.write_text("APMID,Environment\nAPP001,Production\n")

    repo = CSVMetadataRepository(str(csv_file))

    # Act & Assert
    with pytest.raises(ValueError, match="missing 'resourceArn' column"):
        repo.load_metadata()


def test_load_metadata_skips_empty_resource_arn(tmp_path: Path) -> None:
    """Test that rows with empty resourceArn are skipped."""
    # Arrange
    csv_file = tmp_path / "metadata.csv"
    csv_file.write_text(
        "resourceArn,APMID\n"
        "arn:aws:ec2:us-east-1:123456789012:volume/vol-1,APP001\n"
        ",APP002\n"  # Empty resourceArn
        "   ,APP003\n"  # Whitespace-only resourceArn
    )

    repo = CSVMetadataRepository(str(csv_file))

    # Act
    metadata = repo.load_metadata()

    # Assert
    assert len(metadata) == 1  # Only one valid entry
    assert "arn:aws:ec2:us-east-1:123456789012:volume/vol-1" in metadata
