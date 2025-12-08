"""Unit tests for SummaryReport domain model."""

import json
from datetime import datetime, timedelta
from pathlib import Path

from shuffle_aws_vaults.domain.summary_report import FailureDetail, SummaryReport


def test_failure_detail_creation() -> None:
    """Test creating a FailureDetail."""
    failure = FailureDetail(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:abcd-1234",
        error_message="Copy job failed: Access denied",
    )

    assert failure.recovery_point_arn == "arn:aws:backup:us-east-1:123456789012:recovery-point:abcd-1234"
    assert failure.error_message == "Copy job failed: Access denied"
    assert failure.timestamp is None


def test_failure_detail_with_timestamp() -> None:
    """Test FailureDetail with timestamp."""
    now = datetime.now()
    failure = FailureDetail(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:abcd-1234",
        error_message="Timeout",
        timestamp=now,
    )

    assert failure.timestamp == now


def test_failure_detail_to_dict() -> None:
    """Test converting FailureDetail to dictionary."""
    now = datetime.now()
    failure = FailureDetail(
        recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:abcd-1234",
        error_message="Error",
        timestamp=now,
    )

    data = failure.to_dict()
    assert data["recovery_point_arn"] == "arn:aws:backup:us-east-1:123456789012:recovery-point:abcd-1234"
    assert data["error_message"] == "Error"
    assert data["timestamp"] == now.isoformat()


def test_summary_report_creation() -> None:
    """Test creating a SummaryReport."""
    start = datetime.now()
    end = start + timedelta(minutes=30)

    report = SummaryReport(
        total_items=100,
        completed=95,
        failed=3,
        skipped=2,
        in_progress=0,
        duration_seconds=1800.0,
        start_time=start,
        end_time=end,
    )

    assert report.total_items == 100
    assert report.completed == 95
    assert report.failed == 3
    assert report.skipped == 2
    assert report.in_progress == 0
    assert report.duration_seconds == 1800.0


def test_summary_report_success_rate() -> None:
    """Test success rate calculation."""
    start = datetime.now()
    end = start + timedelta(minutes=10)

    report = SummaryReport(
        total_items=100,
        completed=80,
        failed=10,
        skipped=10,
        in_progress=0,
        duration_seconds=600.0,
        start_time=start,
        end_time=end,
    )

    assert report.success_rate == 80.0


def test_summary_report_success_rate_zero_items() -> None:
    """Test success rate with zero items."""
    start = datetime.now()
    end = start + timedelta(seconds=1)

    report = SummaryReport(
        total_items=0,
        completed=0,
        failed=0,
        skipped=0,
        in_progress=0,
        duration_seconds=1.0,
        start_time=start,
        end_time=end,
    )

    assert report.success_rate == 0.0


def test_summary_report_throughput() -> None:
    """Test throughput calculation."""
    start = datetime.now()
    end = start + timedelta(hours=1)

    # 100 items in 1 hour = 100 items/hour
    report = SummaryReport(
        total_items=100,
        completed=100,
        failed=0,
        skipped=0,
        in_progress=0,
        duration_seconds=3600.0,
        start_time=start,
        end_time=end,
    )

    assert report.throughput_per_hour == 100.0


def test_summary_report_throughput_short_duration() -> None:
    """Test throughput with very short duration."""
    start = datetime.now()
    end = start + timedelta(milliseconds=500)

    report = SummaryReport(
        total_items=10,
        completed=10,
        failed=0,
        skipped=0,
        in_progress=0,
        duration_seconds=0.5,
        start_time=start,
        end_time=end,
    )

    assert report.throughput_per_hour is None


def test_summary_report_format_duration() -> None:
    """Test duration formatting."""
    start = datetime.now()

    # Test seconds only
    report = SummaryReport(
        total_items=10,
        completed=10,
        failed=0,
        skipped=0,
        in_progress=0,
        duration_seconds=45.0,
        start_time=start,
        end_time=start + timedelta(seconds=45),
    )
    assert report.format_duration() == "45s"

    # Test minutes and seconds
    report.duration_seconds = 150.0
    assert report.format_duration() == "2m 30s"

    # Test hours and minutes
    report.duration_seconds = 3900.0
    assert report.format_duration() == "1h 5m"

    # Test days
    report.duration_seconds = 90000.0
    assert report.format_duration() == "1d 1h 0m"


def test_summary_report_with_failures() -> None:
    """Test SummaryReport with failure details."""
    start = datetime.now()
    end = start + timedelta(minutes=10)

    failures = [
        FailureDetail(
            recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:1",
            error_message="Access denied",
        ),
        FailureDetail(
            recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:2",
            error_message="Timeout",
        ),
    ]

    report = SummaryReport(
        total_items=100,
        completed=98,
        failed=2,
        skipped=0,
        in_progress=0,
        duration_seconds=600.0,
        start_time=start,
        end_time=end,
        failures=failures,
    )

    assert len(report.failures) == 2
    assert report.failures[0].error_message == "Access denied"
    assert report.failures[1].error_message == "Timeout"


def test_summary_report_to_dict() -> None:
    """Test converting SummaryReport to dictionary."""
    start = datetime.now()
    end = start + timedelta(minutes=30)

    report = SummaryReport(
        total_items=100,
        completed=95,
        failed=5,
        skipped=0,
        in_progress=0,
        duration_seconds=1800.0,
        start_time=start,
        end_time=end,
    )

    data = report.to_dict()
    assert data["total_items"] == 100
    assert data["completed"] == 95
    assert data["failed"] == 5
    assert data["success_rate"] == 95.0
    assert data["throughput_per_hour"] == 190.0
    assert "duration_formatted" in data
    assert data["failures"] == []


def test_summary_report_to_json() -> None:
    """Test converting SummaryReport to JSON."""
    start = datetime.now()
    end = start + timedelta(minutes=10)

    report = SummaryReport(
        total_items=50,
        completed=50,
        failed=0,
        skipped=0,
        in_progress=0,
        duration_seconds=600.0,
        start_time=start,
        end_time=end,
    )

    json_str = report.to_json()
    data = json.loads(json_str)

    assert data["total_items"] == 50
    assert data["completed"] == 50
    assert data["success_rate"] == 100.0


def test_summary_report_save_to_file(tmp_path: Path) -> None:
    """Test saving SummaryReport to JSON file."""
    start = datetime.now()
    end = start + timedelta(minutes=5)

    report = SummaryReport(
        total_items=25,
        completed=25,
        failed=0,
        skipped=0,
        in_progress=0,
        duration_seconds=300.0,
        start_time=start,
        end_time=end,
    )

    output_file = tmp_path / "summary.json"
    report.save_to_file(output_file)

    assert output_file.exists()

    # Load and verify
    data = json.loads(output_file.read_text())
    assert data["total_items"] == 25
    assert data["completed"] == 25


def test_summary_report_format_console_summary() -> None:
    """Test formatting summary for console."""
    start = datetime.now()
    end = start + timedelta(minutes=10)

    report = SummaryReport(
        total_items=100,
        completed=95,
        failed=5,
        skipped=0,
        in_progress=0,
        duration_seconds=600.0,
        start_time=start,
        end_time=end,
    )

    summary = report.format_console_summary()

    assert "COPY OPERATION SUMMARY" in summary
    assert "Total Items:      100" in summary
    assert "Completed:        95" in summary
    assert "Failed:           5" in summary
    assert "Success Rate:     95.0%" in summary
    assert "items/hour" in summary


def test_summary_report_console_summary_with_failures() -> None:
    """Test console summary includes failure details."""
    start = datetime.now()
    end = start + timedelta(minutes=10)

    failures = [
        FailureDetail(
            recovery_point_arn="arn:aws:backup:us-east-1:123456789012:recovery-point:1",
            error_message="Access denied",
        ),
    ]

    report = SummaryReport(
        total_items=100,
        completed=99,
        failed=1,
        skipped=0,
        in_progress=0,
        duration_seconds=600.0,
        start_time=start,
        end_time=end,
        failures=failures,
    )

    summary = report.format_console_summary()

    assert "FAILURES (1):" in summary
    assert "arn:aws:backup:us-east-1:123456789012:recovery-point:1" in summary
    assert "Access denied" in summary
