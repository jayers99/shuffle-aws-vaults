#!/usr/bin/env python3
"""
Progress tracker for monitoring long-running operations.

Provides real-time progress updates with ETA calculation and throughput tracking.
"""

import sys
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, TextIO

__version__ = "0.1.0"
__author__ = "John Ayers"


def file_info() -> dict[str, str]:
    """Return metadata about this module.

    Returns:
        Dictionary containing module metadata
    """
    return {
        "name": "progress_tracker",
        "description": "Progress tracking with ETA and throughput",
        "version": __version__,
        "author": __author__,
        "last_updated": "2025-12-07",
    }


@dataclass
class ProgressSnapshot:
    """Snapshot of progress at a point in time.

    Attributes:
        timestamp: When this snapshot was taken
        completed: Number of completed items
        total: Total number of items
        errors: Number of errors encountered
    """

    timestamp: float
    completed: int
    total: int
    errors: int


class ProgressTracker:
    """Tracks progress and displays real-time updates.

    Calculates throughput, ETA, and displays progress to console.
    Thread-safe for use with multithreaded operations.
    """

    def __init__(
        self,
        total: int,
        output: TextIO = sys.stdout,
        refresh_interval: float = 5.0,
        window_size: int = 10,
        verbose: bool = False,
    ) -> None:
        """Initialize progress tracker.

        Args:
            total: Total number of items to process
            output: Output stream for progress display (default: stdout)
            refresh_interval: Seconds between progress updates (default: 5.0)
            window_size: Number of snapshots for rolling average (default: 10)
            verbose: Enable verbose per-item logging (default: False)
        """
        self.total = total
        self.output = output
        self.refresh_interval = refresh_interval
        self.window_size = window_size
        self.verbose = verbose

        self.completed = 0
        self.errors = 0
        self.start_time = time.time()
        self.last_update = self.start_time  # Initialize to start_time to prevent immediate refresh

        # Rolling window of progress snapshots for throughput calculation
        self.snapshots: deque[ProgressSnapshot] = deque(maxlen=window_size)
        self.snapshots.append(
            ProgressSnapshot(
                timestamp=self.start_time,
                completed=0,
                total=total,
                errors=0,
            )
        )

    def increment_completed(self, message: str | None = None) -> None:
        """Increment completed count and optionally log message.

        Args:
            message: Optional message to display in verbose mode
        """
        self.completed += 1

        if self.verbose and message:
            self._write_line(message)

        self._maybe_refresh()

    def increment_errors(self, message: str | None = None) -> None:
        """Increment error count and optionally log message.

        Args:
            message: Optional error message to display in verbose mode
        """
        self.errors += 1

        if self.verbose and message:
            self._write_line(f"ERROR: {message}")

        self._maybe_refresh()

    def update(self, completed: int | None = None, errors: int | None = None) -> None:
        """Update progress counters directly.

        Args:
            completed: Set completed count (optional)
            errors: Set error count (optional)
        """
        if completed is not None:
            self.completed = completed
        if errors is not None:
            self.errors = errors

        self._maybe_refresh()

    def _maybe_refresh(self) -> None:
        """Refresh display if enough time has passed."""
        now = time.time()
        if now - self.last_update >= self.refresh_interval:
            self.refresh()

    def refresh(self, force: bool = False) -> None:
        """Refresh progress display.

        Args:
            force: Force refresh even if interval hasn't elapsed
        """
        now = time.time()

        if not force and now - self.last_update < self.refresh_interval:
            return

        # Add snapshot for rolling average
        self.snapshots.append(
            ProgressSnapshot(
                timestamp=now,
                completed=self.completed,
                total=self.total,
                errors=self.errors,
            )
        )

        self.last_update = now
        self._display_progress()

    def _calculate_throughput(self) -> float | None:
        """Calculate rolling average throughput (items/hour).

        Returns:
            Throughput in items per hour, or None if insufficient data
        """
        if len(self.snapshots) < 2:
            return None

        oldest = self.snapshots[0]
        newest = self.snapshots[-1]

        time_delta = newest.timestamp - oldest.timestamp
        if time_delta < 1.0:  # Need at least 1 second of data
            return None

        items_delta = newest.completed - oldest.completed
        items_per_second = items_delta / time_delta
        items_per_hour = items_per_second * 3600

        return items_per_hour

    def _calculate_eta(self) -> timedelta | None:
        """Calculate estimated time to completion.

        Returns:
            Estimated time remaining, or None if cannot calculate
        """
        throughput = self._calculate_throughput()
        if not throughput or throughput <= 0:
            return None

        remaining = self.total - self.completed
        hours_remaining = remaining / throughput
        seconds_remaining = hours_remaining * 3600

        return timedelta(seconds=seconds_remaining)

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted string (e.g., "2h 15m", "45m 30s", "12s")
        """
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"

    def _display_progress(self) -> None:
        """Display current progress to output stream."""
        if not self.output.isatty():
            # Non-interactive mode, just print progress line
            self._write_line(self._format_progress_line())
            return

        # Interactive mode: use ANSI codes for same-line refresh
        # Clear line and move cursor to start
        self.output.write("\r\033[K")
        self.output.write(self._format_progress_line())
        self.output.flush()

    def _format_progress_line(self) -> str:
        """Format the progress line for display.

        Returns:
            Formatted progress string
        """
        elapsed = time.time() - self.start_time
        elapsed_str = self._format_duration(elapsed)

        # Completed/Total
        progress = f"{self.completed}/{self.total}"

        # Percentage
        percentage = (self.completed / self.total * 100) if self.total > 0 else 0

        # Throughput
        throughput = self._calculate_throughput()
        throughput_str = f"{throughput:.1f} items/hour" if throughput else "calculating..."

        # ETA
        eta = self._calculate_eta()
        eta_str = f"ETA: {self._format_duration(eta.total_seconds())}" if eta else "ETA: calculating..."

        # Errors
        error_str = f"errors: {self.errors}" if self.errors > 0 else ""

        parts = [
            f"Progress: {progress}",
            f"({percentage:.1f}%)",
            f"Rate: {throughput_str}",
            eta_str,
            f"Elapsed: {elapsed_str}",
        ]

        if error_str:
            parts.append(error_str)

        return " | ".join(parts)

    def _write_line(self, message: str) -> None:
        """Write a complete line to output.

        Args:
            message: Message to write
        """
        self.output.write(f"{message}\n")
        self.output.flush()

    def finish(self, final_message: Callable[[], str] | None = None) -> None:
        """Finish progress tracking and display final summary.

        Args:
            final_message: Optional callback to generate final message
        """
        # Force final refresh
        self.refresh(force=True)

        # Move to new line if in interactive mode
        if self.output.isatty():
            self.output.write("\n")

        # Display final summary
        elapsed = time.time() - self.start_time
        elapsed_str = self._format_duration(elapsed)

        if final_message:
            self._write_line(final_message())
        else:
            summary = (
                f"\nCompleted: {self.completed}/{self.total} "
                f"({self.completed / self.total * 100:.1f}%) "
                f"in {elapsed_str}"
            )
            if self.errors > 0:
                summary += f" | Errors: {self.errors}"
            self._write_line(summary)


if __name__ == "__main__":
    # Example usage
    info = file_info()
    print(f"{info['name']} v{info['version']}")
