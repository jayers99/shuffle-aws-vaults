"""Unit tests for ProgressTracker."""

import io
import time

from shuffle_aws_vaults.infrastructure.progress_tracker import ProgressSnapshot, ProgressTracker


def test_progress_tracker_creation() -> None:
    """Test creating a progress tracker."""
    tracker = ProgressTracker(total=100)

    assert tracker.total == 100
    assert tracker.completed == 0
    assert tracker.errors == 0
    assert len(tracker.snapshots) == 1


def test_increment_completed() -> None:
    """Test incrementing completed count."""
    tracker = ProgressTracker(total=10)

    tracker.increment_completed()
    assert tracker.completed == 1

    tracker.increment_completed("Test message")
    assert tracker.completed == 2


def test_increment_errors() -> None:
    """Test incrementing error count."""
    tracker = ProgressTracker(total=10)

    tracker.increment_errors()
    assert tracker.errors == 1

    tracker.increment_errors("Error message")
    assert tracker.errors == 2


def test_update() -> None:
    """Test direct update of counters."""
    tracker = ProgressTracker(total=100)

    tracker.update(completed=50, errors=5)
    assert tracker.completed == 50
    assert tracker.errors == 5

    tracker.update(completed=75)
    assert tracker.completed == 75
    assert tracker.errors == 5


def test_verbose_mode() -> None:
    """Test that verbose mode logs messages."""
    output = io.StringIO()
    tracker = ProgressTracker(total=10, output=output, verbose=True, refresh_interval=999)

    tracker.increment_completed("Item 1 completed")
    tracker.increment_completed("Item 2 completed")

    output_text = output.getvalue()
    assert "Item 1 completed" in output_text
    assert "Item 2 completed" in output_text


def test_verbose_mode_errors() -> None:
    """Test that verbose mode logs error messages."""
    output = io.StringIO()
    tracker = ProgressTracker(total=10, output=output, verbose=True, refresh_interval=999)

    tracker.increment_errors("Something went wrong")

    output_text = output.getvalue()
    assert "ERROR: Something went wrong" in output_text


def test_calculate_throughput() -> None:
    """Test throughput calculation."""
    tracker = ProgressTracker(total=100, window_size=10)

    # Not enough data yet (only 1 snapshot)
    assert tracker._calculate_throughput() is None

    # Simulate processing over time by replacing the initial snapshot and adding new ones
    now = time.time()
    tracker.snapshots.clear()
    tracker.snapshots.append(
        ProgressSnapshot(timestamp=now - 10, completed=0, total=100, errors=0)
    )
    tracker.snapshots.append(
        ProgressSnapshot(timestamp=now, completed=10, total=100, errors=0)
    )

    # Should calculate ~3600 items/hour (10 items in 10 seconds)
    throughput = tracker._calculate_throughput()
    assert throughput is not None
    assert 3500 < throughput < 3700  # Allow some tolerance


def test_calculate_eta() -> None:
    """Test ETA calculation."""
    tracker = ProgressTracker(total=100, window_size=10)

    # Not enough data yet
    assert tracker._calculate_eta() is None

    # Simulate processing 10 items in 10 seconds (rate: 1 item/sec)
    now = time.time()
    tracker.completed = 10  # Update completed count
    tracker.snapshots.clear()
    tracker.snapshots.append(
        ProgressSnapshot(timestamp=now - 10, completed=0, total=100, errors=0)
    )
    tracker.snapshots.append(
        ProgressSnapshot(timestamp=now, completed=10, total=100, errors=0)
    )

    # Remaining: 90 items at 1 item/sec = 90 seconds
    eta = tracker._calculate_eta()
    assert eta is not None
    assert 85 < eta.total_seconds() < 95  # Allow some tolerance


def test_format_duration() -> None:
    """Test duration formatting."""
    tracker = ProgressTracker(total=100)

    assert tracker._format_duration(30) == "30s"
    assert tracker._format_duration(90) == "1m 30s"
    assert tracker._format_duration(3661) == "1h 1m"
    assert tracker._format_duration(7265) == "2h 1m"


def test_format_progress_line() -> None:
    """Test progress line formatting."""
    tracker = ProgressTracker(total=100)
    tracker.completed = 50
    tracker.errors = 2

    # Add some throughput data
    now = time.time()
    tracker.snapshots.clear()
    tracker.snapshots.append(
        ProgressSnapshot(timestamp=now - 10, completed=0, total=100, errors=0)
    )
    tracker.snapshots.append(
        ProgressSnapshot(timestamp=now, completed=50, total=100, errors=2)
    )

    line = tracker._format_progress_line()

    assert "50/100" in line
    assert "50.0%" in line
    assert "items/hour" in line or "calculating" in line  # May show rate or "calculating..."
    assert "ETA:" in line
    assert "Elapsed:" in line
    assert "errors: 2" in line


def test_progress_line_no_errors() -> None:
    """Test progress line without errors."""
    tracker = ProgressTracker(total=100)
    tracker.completed = 50

    line = tracker._format_progress_line()

    assert "50/100" in line
    assert "errors" not in line


def test_refresh_interval() -> None:
    """Test that refresh respects interval."""
    output = io.StringIO()
    tracker = ProgressTracker(total=100, output=output, refresh_interval=0.5)

    tracker.increment_completed()
    time.sleep(0.1)  # Less than refresh interval
    tracker.increment_completed()

    # Should not have refreshed yet (interval not elapsed)
    # Only one snapshot (initial)
    assert len(tracker.snapshots) == 1

    time.sleep(0.5)  # Now past interval
    tracker.increment_completed()

    # Should have refreshed now
    assert len(tracker.snapshots) == 2


def test_force_refresh() -> None:
    """Test forcing refresh regardless of interval."""
    tracker = ProgressTracker(total=100, refresh_interval=999)

    tracker.increment_completed()
    assert len(tracker.snapshots) == 1

    tracker.refresh(force=True)
    assert len(tracker.snapshots) == 2


def test_non_interactive_output() -> None:
    """Test output in non-interactive mode."""
    output = io.StringIO()
    tracker = ProgressTracker(total=10, output=output, refresh_interval=0)

    tracker.increment_completed()
    tracker.refresh(force=True)

    output_text = output.getvalue()
    # Should have newlines in non-interactive mode
    assert "\n" in output_text or "Progress:" in output_text


def test_finish() -> None:
    """Test finishing progress tracking."""
    output = io.StringIO()
    tracker = ProgressTracker(total=100, output=output)
    tracker.completed = 100

    tracker.finish()

    output_text = output.getvalue()
    assert "100/100" in output_text
    assert "100.0%" in output_text


def test_finish_with_custom_message() -> None:
    """Test finishing with custom final message."""
    output = io.StringIO()
    tracker = ProgressTracker(total=100, output=output)
    tracker.completed = 75
    tracker.errors = 5

    def custom_message() -> str:
        return "Custom completion message!"

    tracker.finish(custom_message)

    output_text = output.getvalue()
    assert "Custom completion message!" in output_text


def test_progress_snapshot_creation() -> None:
    """Test creating a progress snapshot."""
    snapshot = ProgressSnapshot(
        timestamp=time.time(),
        completed=50,
        total=100,
        errors=2,
    )

    assert snapshot.completed == 50
    assert snapshot.total == 100
    assert snapshot.errors == 2
    assert snapshot.timestamp > 0


def test_rolling_window() -> None:
    """Test that rolling window limits snapshot count."""
    tracker = ProgressTracker(total=100, window_size=5)

    # Add 10 snapshots (tracker already has 1 initial snapshot)
    # With window_size=5, deque will only keep the last 5
    for i in range(10):
        tracker.snapshots.append(
            ProgressSnapshot(
                timestamp=time.time(),
                completed=i * 10,
                total=100,
                errors=0,
            )
        )

    # Should only keep 5 (window_size)
    assert len(tracker.snapshots) == 5


def test_runtime_limit_not_exceeded() -> None:
    """Test that runtime limit is not exceeded initially."""
    tracker = ProgressTracker(total=100, max_runtime_minutes=5)

    assert not tracker.is_runtime_limit_exceeded()


def test_runtime_limit_exceeded() -> None:
    """Test that runtime limit is exceeded after time passes."""
    tracker = ProgressTracker(total=100, max_runtime_minutes=1)

    # Simulate 61 seconds passing by adjusting start_time
    tracker.start_time = time.time() - 61

    assert tracker.is_runtime_limit_exceeded()


def test_runtime_limit_no_limit_set() -> None:
    """Test runtime limit behavior when no limit is set."""
    tracker = ProgressTracker(total=100)

    assert not tracker.is_runtime_limit_exceeded()
    assert tracker.get_time_remaining_in_window() is None


def test_get_time_remaining_in_window() -> None:
    """Test time remaining calculation."""
    tracker = ProgressTracker(total=100, max_runtime_minutes=10)

    # Should have close to 10 minutes (600 seconds) remaining
    time_remaining = tracker.get_time_remaining_in_window()
    assert time_remaining is not None
    assert 595 < time_remaining <= 600  # Allow small tolerance

    # Simulate 5 minutes passing
    tracker.start_time = time.time() - 300

    time_remaining = tracker.get_time_remaining_in_window()
    assert time_remaining is not None
    assert 295 < time_remaining <= 300


def test_get_time_remaining_never_negative() -> None:
    """Test that time remaining never goes negative."""
    tracker = ProgressTracker(total=100, max_runtime_minutes=1)

    # Simulate 2 minutes passing (limit exceeded)
    tracker.start_time = time.time() - 120

    time_remaining = tracker.get_time_remaining_in_window()
    assert time_remaining is not None
    assert time_remaining == 0


def test_progress_line_with_runtime_limit() -> None:
    """Test that progress line includes runtime window when limit is set."""
    tracker = ProgressTracker(total=100, max_runtime_minutes=10)
    tracker.completed = 50

    # Add some throughput data
    now = time.time()
    tracker.snapshots.clear()
    tracker.snapshots.append(
        ProgressSnapshot(timestamp=now - 10, completed=0, total=100, errors=0)
    )
    tracker.snapshots.append(
        ProgressSnapshot(timestamp=now, completed=50, total=100, errors=0)
    )

    line = tracker._format_progress_line()

    assert "50/100" in line
    assert "Window:" in line  # Runtime window should be shown


def test_progress_line_without_runtime_limit() -> None:
    """Test that progress line doesn't show window when no limit is set."""
    tracker = ProgressTracker(total=100)
    tracker.completed = 50

    line = tracker._format_progress_line()

    assert "50/100" in line
    assert "Window:" not in line  # No runtime window
