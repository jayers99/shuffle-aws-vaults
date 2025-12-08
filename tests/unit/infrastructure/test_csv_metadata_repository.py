"""Unit tests for CSVMetadataRepository."""

import time
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


def test_progress_callback(tmp_path: Path) -> None:
    """Test that progress callback is called during loading."""
    # Arrange
    csv_file = tmp_path / "metadata.csv"

    # Create CSV with enough rows to trigger multiple progress updates
    # PROGRESS_INTERVAL is 10000, so we need > 10000 rows
    rows = ["resourceArn,APMID"]
    for i in range(15000):
        rows.append(f"arn:aws:ec2:us-east-1:123456789012:volume/vol-{i},APP{i:05d}")

    csv_file.write_text("\n".join(rows))

    progress_calls = []

    def progress_callback(row_count: int) -> None:
        progress_calls.append(row_count)

    repo = CSVMetadataRepository(str(csv_file), progress_callback=progress_callback)

    # Act
    metadata = repo.load_metadata()

    # Assert
    assert len(metadata) == 15000
    # Should have at least 2 progress callbacks (at 10000 and at completion)
    assert len(progress_calls) >= 2
    # First callback should be around 10000
    assert 10000 in progress_calls
    # Final callback should be total rows
    assert 15000 in progress_calls


def test_row_count_property(tmp_path: Path) -> None:
    """Test row_count property."""
    # Arrange
    csv_file = tmp_path / "metadata.csv"
    csv_file.write_text(
        "resourceArn,APMID\n"
        "arn:aws:ec2:us-east-1:123456789012:volume/vol-1,APP001\n"
        "arn:aws:ec2:us-east-1:123456789012:volume/vol-2,APP002\n"
        "arn:aws:ec2:us-east-1:123456789012:volume/vol-3,APP003\n"
    )

    repo = CSVMetadataRepository(str(csv_file))

    # Assert before loading
    assert repo.row_count == 0

    # Act
    repo.load_metadata()

    # Assert after loading
    assert repo.row_count == 3


def test_is_loaded_property(tmp_path: Path) -> None:
    """Test is_loaded property."""
    # Arrange
    csv_file = tmp_path / "metadata.csv"
    csv_file.write_text("resourceArn,APMID\narn:aws:ec2:us-east-1:123456789012:volume/vol-1,APP001\n")

    repo = CSVMetadataRepository(str(csv_file))

    # Assert before loading
    assert repo.is_loaded is False

    # Act
    repo.load_metadata()

    # Assert after loading
    assert repo.is_loaded is True


def test_row_count_excludes_empty_resource_arns(tmp_path: Path) -> None:
    """Test that row_count only counts rows with resourceArn."""
    # Arrange
    csv_file = tmp_path / "metadata.csv"
    csv_file.write_text(
        "resourceArn,APMID\n"
        "arn:aws:ec2:us-east-1:123456789012:volume/vol-1,APP001\n"
        ",APP002\n"  # Empty resourceArn
        "arn:aws:ec2:us-east-1:123456789012:volume/vol-2,APP003\n"
        "   ,APP004\n"  # Whitespace-only resourceArn
    )

    repo = CSVMetadataRepository(str(csv_file))

    # Act
    repo.load_metadata()

    # Assert
    assert repo.row_count == 2  # Only 2 valid rows with resourceArn


def test_large_csv_performance_benchmark(tmp_path: Path) -> None:
    """Benchmark test: loading 100K rows should be fast.

    Note: Full 1M row benchmark would be too slow for regular test runs.
    This tests 100K rows which should complete in < 2 seconds.
    """
    # Arrange
    csv_file = tmp_path / "large_metadata.csv"

    # Generate 100,000 rows
    rows = ["resourceArn,APMID,Environment,Owner"]
    for i in range(100000):
        rows.append(
            f"arn:aws:ec2:us-east-1:123456789012:volume/vol-{i},"
            f"APP{i % 100:03d},{'Prod' if i % 2 == 0 else 'Dev'},"
            f"team{i % 10}"
        )

    csv_file.write_text("\n".join(rows))

    repo = CSVMetadataRepository(str(csv_file))

    # Act
    start_time = time.time()
    metadata = repo.load_metadata()
    elapsed = time.time() - start_time

    # Assert
    assert len(metadata) == 100000
    # Should load 100K rows in under 2 seconds
    # (this leaves margin for slow CI environments, 1M rows should be < 20s)
    assert elapsed < 2.0, f"CSV loading took {elapsed:.2f}s, expected < 2.0s"

    # Verify O(1) lookup performance
    lookup_start = time.time()
    result = repo.get_metadata_for_resource("arn:aws:ec2:us-east-1:123456789012:volume/vol-50000")
    lookup_elapsed = time.time() - lookup_start

    assert result is not None
    assert result["APMID"] == "APP000"
    # Lookup should be instant (< 1ms)
    assert lookup_elapsed < 0.001, f"Lookup took {lookup_elapsed:.4f}s, expected < 0.001s"


def test_progress_callback_not_required(tmp_path: Path) -> None:
    """Test that progress callback is optional."""
    # Arrange
    csv_file = tmp_path / "metadata.csv"
    csv_file.write_text("resourceArn,APMID\narn:aws:ec2:us-east-1:123456789012:volume/vol-1,APP001\n")

    # Act - no progress_callback provided
    repo = CSVMetadataRepository(str(csv_file))
    metadata = repo.load_metadata()

    # Assert
    assert len(metadata) == 1
