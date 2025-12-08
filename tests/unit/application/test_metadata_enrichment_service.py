"""Unit tests for MetadataEnrichmentService."""

import logging
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from shuffle_aws_vaults.application.metadata_enrichment_service import (
    MetadataEnrichmentService,
)
from shuffle_aws_vaults.domain.recovery_point import RecoveryPoint


def test_enrich_recovery_point_with_metadata() -> None:
    """Test enriching a recovery point with metadata."""
    # Arrange
    rp = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-1",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-1",
        resource_type="EBS",
        creation_date=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        completion_date=datetime(2025, 1, 1, 13, 0, 0, tzinfo=timezone.utc),
        status="COMPLETED",
        size_bytes=10 * 1024**3,
        backup_job_id="job-1",
    )

    mock_repo = Mock()
    mock_repo.get_metadata_for_resource.return_value = {
        "APMID": "APP001",
        "Environment": "Production",
    }

    service = MetadataEnrichmentService(mock_repo)

    # Act
    enriched = service.enrich_recovery_point(rp)

    # Assert
    assert enriched.get_metadata("APMID") == "APP001"
    assert enriched.get_metadata("Environment") == "Production"
    mock_repo.get_metadata_for_resource.assert_called_once_with(
        "arn:aws:ec2:us-east-1:123456789012:volume/vol-1"
    )


def test_enrich_recovery_point_no_metadata_found() -> None:
    """Test enriching when no metadata exists for resource."""
    # Arrange
    rp = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-2",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-2",
        resource_type="EBS",
        creation_date=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        completion_date=datetime(2025, 1, 1, 13, 0, 0, tzinfo=timezone.utc),
        status="COMPLETED",
        size_bytes=10 * 1024**3,
        backup_job_id="job-2",
    )

    mock_repo = Mock()
    mock_repo.get_metadata_for_resource.return_value = None

    service = MetadataEnrichmentService(mock_repo)

    # Act
    enriched = service.enrich_recovery_point(rp)

    # Assert
    assert enriched.metadata == {}  # No metadata added
    assert enriched is rp  # Same object returned


def test_enrich_multiple_recovery_points() -> None:
    """Test enriching multiple recovery points."""
    # Arrange
    rp1 = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-1",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-1",
        resource_type="EBS",
        creation_date=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        completion_date=datetime(2025, 1, 1, 13, 0, 0, tzinfo=timezone.utc),
        status="COMPLETED",
        size_bytes=10 * 1024**3,
        backup_job_id="job-1",
    )

    rp2 = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-2",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:rds:us-east-1:123456789012:db:mydb",
        resource_type="RDS",
        creation_date=datetime(2025, 1, 2, 12, 0, 0, tzinfo=timezone.utc),
        completion_date=datetime(2025, 1, 2, 13, 0, 0, tzinfo=timezone.utc),
        status="COMPLETED",
        size_bytes=20 * 1024**3,
        backup_job_id="job-2",
    )

    mock_repo = Mock()

    def mock_get_metadata(resource_arn: str) -> dict[str, str] | None:
        if "vol-1" in resource_arn:
            return {"APMID": "APP001"}
        elif "mydb" in resource_arn:
            return {"APMID": "APP002"}
        return None

    mock_repo.get_metadata_for_resource.side_effect = mock_get_metadata

    service = MetadataEnrichmentService(mock_repo)

    # Act
    enriched_list = service.enrich_recovery_points([rp1, rp2])

    # Assert
    assert len(enriched_list) == 2
    assert enriched_list[0].get_metadata("APMID") == "APP001"
    assert enriched_list[1].get_metadata("APMID") == "APP002"


def test_get_enrichment_stats() -> None:
    """Test getting enrichment statistics."""
    # Arrange
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
    )

    rp2 = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-2",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-2",
        resource_type="EBS",
        creation_date=datetime.now(tz=timezone.utc),
        completion_date=datetime.now(tz=timezone.utc),
        status="COMPLETED",
        size_bytes=10 * 1024**3,
        backup_job_id="job-2",
    )

    rp3 = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-3",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-3",
        resource_type="EBS",
        creation_date=datetime.now(tz=timezone.utc),
        completion_date=datetime.now(tz=timezone.utc),
        status="COMPLETED",
        size_bytes=10 * 1024**3,
        backup_job_id="job-3",
    )

    mock_repo = Mock()

    def mock_get_metadata(resource_arn: str) -> dict[str, str] | None:
        if "vol-1" in resource_arn or "vol-2" in resource_arn:
            return {"APMID": "APP001"}
        return None  # vol-3 has no metadata

    mock_repo.get_metadata_for_resource.side_effect = mock_get_metadata

    service = MetadataEnrichmentService(mock_repo)

    # Act
    stats = service.get_enrichment_stats([rp1, rp2, rp3])

    # Assert
    assert stats["total_count"] == 3
    assert stats["enriched_count"] == 2
    assert stats["missing_count"] == 1


def test_enrich_recovery_point_logs_warning_for_missing_metadata(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that a warning is logged when metadata is missing."""
    # Arrange
    rp = RecoveryPoint(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:rp-missing",
        backup_vault_name="test-vault",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:volume/vol-missing",
        resource_type="EBS",
        creation_date=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        completion_date=datetime(2025, 1, 1, 13, 0, 0, tzinfo=timezone.utc),
        status="COMPLETED",
        size_bytes=10 * 1024**3,
        backup_job_id="job-missing",
    )

    mock_repo = Mock()
    mock_repo.get_metadata_for_resource.return_value = None

    service = MetadataEnrichmentService(mock_repo)

    # Act
    with caplog.at_level(logging.WARNING):
        enriched = service.enrich_recovery_point(rp)

    # Assert
    assert enriched is rp  # Same object returned
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert "No metadata found" in caplog.records[0].message
    assert "vol-missing" in caplog.records[0].message
    assert "rp-missing" in caplog.records[0].message
