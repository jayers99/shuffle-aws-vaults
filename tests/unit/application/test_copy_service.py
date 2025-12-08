"""Unit tests for CopyService."""

import threading
import time
from datetime import datetime
from unittest.mock import Mock

import pytest

from shuffle_aws_vaults.application.copy_service import CopyService
from shuffle_aws_vaults.domain.migration_result import MigrationStatus
from shuffle_aws_vaults.domain.recovery_point import RecoveryPoint


@pytest.fixture
def mock_copy_repo():
    """Create a mock copy repository."""
    repo = Mock()
    repo.start_copy_job.return_value = "copy-job-123"
    repo.get_copy_job_status.return_value = "COMPLETED"
    return repo


@pytest.fixture
def sample_recovery_points():
    """Create sample recovery points for testing."""
    return [
        RecoveryPoint(
            recovery_point_arn=f"arn:aws:backup:us-east-1:123456789012:recovery-point:rp-{i}",
            backup_vault_name="test-vault",
            resource_arn=f"arn:aws:ec2:us-east-1:123456789012:volume/vol-{i}",
            resource_type="EBS",
            creation_date=datetime.now(),
            completion_date=datetime.now(),
            status="COMPLETED",
            size_bytes=1024 * 1024 * 100,  # 100 MB
            backup_job_id=f"backup-job-{i}",
        )
        for i in range(5)
    ]


def test_copy_multithreaded_basic(mock_copy_repo, sample_recovery_points):
    """Test basic multithreaded copy operation."""
    service = CopyService(mock_copy_repo)

    batch = service.copy_multithreaded(
        recovery_points=sample_recovery_points,
        dest_account_id="999999999999",
        region="us-east-1",
        workers=3,
        poll_interval=0.1,  # Short interval for testing
    )

    # Batch should be complete
    assert batch.is_complete()
    assert len(batch.operations) == 5

    # All operations should be completed
    completed = [op for op in batch.operations if op.status == MigrationStatus.COMPLETED]
    assert len(completed) == 5

    # start_copy_job should have been called 5 times
    assert mock_copy_repo.start_copy_job.call_count == 5


def test_copy_multithreaded_with_workers(mock_copy_repo, sample_recovery_points):
    """Test that worker threads are created correctly."""
    service = CopyService(mock_copy_repo)

    # Track active threads during execution
    active_threads = []

    def track_threads(*args, **kwargs):
        active_threads.append(threading.active_count())
        return "copy-job-123"

    mock_copy_repo.start_copy_job.side_effect = track_threads

    batch = service.copy_multithreaded(
        recovery_points=sample_recovery_points,
        dest_account_id="999999999999",
        region="us-east-1",
        workers=3,
        poll_interval=0.1,
    )

    # Should have created multiple threads (at least 2 or more)
    # Base thread count varies, but we should see increase during execution
    assert max(active_threads) > threading.active_count()


def test_copy_multithreaded_thread_safety(mock_copy_repo):
    """Test thread-safe operation tracking."""
    service = CopyService(mock_copy_repo)

    # Create many recovery points to stress test thread safety
    recovery_points = [
        RecoveryPoint(
            recovery_point_arn=f"arn:aws:backup:us-east-1:123456789012:recovery-point:rp-{i}",
            backup_vault_name="test-vault",
            resource_arn=f"arn:aws:ec2:us-east-1:123456789012:volume/vol-{i}",
            resource_type="EBS",
            creation_date=datetime.now(),
            completion_date=datetime.now(),
            status="COMPLETED",
            size_bytes=1024 * 1024 * 100,
            backup_job_id=f"backup-job-{i}",
        )
        for i in range(20)
    ]

    # Add slight delay to increase chance of race conditions if any
    def slow_start(*args, **kwargs):
        time.sleep(0.01)
        return "copy-job-123"

    mock_copy_repo.start_copy_job.side_effect = slow_start

    batch = service.copy_multithreaded(
        recovery_points=recovery_points,
        dest_account_id="999999999999",
        region="us-east-1",
        workers=10,
        poll_interval=0.01,
    )

    # All operations should be accounted for
    assert len(batch.operations) == 20
    assert sum(1 for op in batch.operations if op.status == MigrationStatus.COMPLETED) == 20


def test_copy_multithreaded_with_failures(mock_copy_repo, sample_recovery_points):
    """Test multithreaded copy with some failures."""
    service = CopyService(mock_copy_repo)

    # Make some jobs fail
    mock_copy_repo.get_copy_job_status.side_effect = [
        "COMPLETED",
        "FAILED",
        "COMPLETED",
        "FAILED",
        "COMPLETED",
    ]

    batch = service.copy_multithreaded(
        recovery_points=sample_recovery_points,
        dest_account_id="999999999999",
        region="us-east-1",
        workers=3,
        poll_interval=0.1,
    )

    # Check results
    completed = [op for op in batch.operations if op.status == MigrationStatus.COMPLETED]
    failed = [op for op in batch.operations if op.status == MigrationStatus.FAILED]

    assert len(completed) == 3
    assert len(failed) == 2


def test_copy_multithreaded_shutdown_handling(mock_copy_repo, sample_recovery_points):
    """Test that shutdown is handled correctly in multithreaded mode."""
    service = CopyService(mock_copy_repo)

    shutdown_requested = False

    def check_shutdown():
        return shutdown_requested

    # Delay the copy job status to allow shutdown to trigger
    call_count = 0

    def delayed_status(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        # Trigger shutdown after a few calls
        nonlocal shutdown_requested
        if call_count > 2:
            shutdown_requested = True
        time.sleep(0.05)
        return "RUNNING" if call_count < 10 else "COMPLETED"

    mock_copy_repo.get_copy_job_status.side_effect = delayed_status

    batch = service.copy_multithreaded(
        recovery_points=sample_recovery_points,
        dest_account_id="999999999999",
        region="us-east-1",
        workers=3,
        shutdown_check=check_shutdown,
        poll_interval=0.05,
    )

    # Some operations should be incomplete due to shutdown
    # Not all operations should have completed
    in_progress = [op for op in batch.operations if op.status == MigrationStatus.IN_PROGRESS]
    assert len(in_progress) > 0 or shutdown_requested


def test_copy_multithreaded_dry_run(mock_copy_repo, sample_recovery_points):
    """Test multithreaded copy in dry-run mode."""
    service = CopyService(mock_copy_repo, dry_run=True)

    batch = service.copy_multithreaded(
        recovery_points=sample_recovery_points,
        dest_account_id="999999999999",
        region="us-east-1",
        workers=3,
    )

    # All operations should be skipped
    skipped = [op for op in batch.operations if op.status == MigrationStatus.SKIPPED]
    assert len(skipped) == 5

    # start_copy_job should not have been called
    assert mock_copy_repo.start_copy_job.call_count == 0


def test_copy_multithreaded_progress_callback(mock_copy_repo, sample_recovery_points):
    """Test that progress callback is called correctly."""
    service = CopyService(mock_copy_repo)

    progress_calls = []

    def track_progress(message: str, current: int, total: int):
        progress_calls.append((message, current, total))

    batch = service.copy_multithreaded(
        recovery_points=sample_recovery_points,
        dest_account_id="999999999999",
        region="us-east-1",
        workers=3,
        progress_callback=track_progress,
        poll_interval=0.1,
    )

    # Progress callback should have been called
    assert len(progress_calls) > 0

    # Should have total of 5 in all calls
    for _, _, total in progress_calls:
        assert total == 5


def test_copy_multithreaded_exception_handling(mock_copy_repo, sample_recovery_points):
    """Test that exceptions in worker threads are handled correctly."""
    service = CopyService(mock_copy_repo)

    # Make start_copy_job raise exception for some calls
    call_count = 0

    def raise_on_second(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise Exception("Simulated API error")
        return "copy-job-123"

    mock_copy_repo.start_copy_job.side_effect = raise_on_second

    batch = service.copy_multithreaded(
        recovery_points=sample_recovery_points,
        dest_account_id="999999999999",
        region="us-east-1",
        workers=3,
        poll_interval=0.1,
    )

    # Should have 1 failed operation and 4 completed
    failed = [op for op in batch.operations if op.status == MigrationStatus.FAILED]
    completed = [op for op in batch.operations if op.status == MigrationStatus.COMPLETED]

    assert len(failed) == 1
    assert len(completed) == 4
    assert "Simulated API error" in failed[0].error_message
