#!/usr/bin/env python3
"""
Summary report domain model for copy operations.

Provides structured summary data with statistics and failure details.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

__version__ = "0.1.0"
__author__ = "John Ayers"


def file_info() -> dict[str, str]:
    """Return metadata about this module.

    Returns:
        Dictionary containing module metadata
    """
    return {
        "name": "summary_report",
        "description": "Summary report for copy operations",
        "version": __version__,
        "author": __author__,
        "last_updated": "2025-12-07",
    }


@dataclass
class FailureDetail:
    """Details about a failed operation.

    Attributes:
        recovery_point_arn: ARN of the recovery point that failed
        error_message: Error message describing the failure
        timestamp: When the failure occurred (optional)
    """

    recovery_point_arn: str
    error_message: str
    timestamp: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        return {
            "recovery_point_arn": self.recovery_point_arn,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


@dataclass
class SummaryReport:
    """Summary report for a copy operation.

    Attributes:
        total_items: Total number of items processed
        completed: Number of successfully completed items
        failed: Number of failed items
        skipped: Number of skipped items
        in_progress: Number of items still in progress
        duration_seconds: Total duration in seconds
        start_time: When the operation started
        end_time: When the operation ended
        failures: List of failure details
    """

    total_items: int
    completed: int
    failed: int
    skipped: int
    in_progress: int
    duration_seconds: float
    start_time: datetime
    end_time: datetime
    failures: list[FailureDetail] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate report data."""
        if self.total_items < 0:
            raise ValueError("total_items cannot be negative")
        if self.completed < 0:
            raise ValueError("completed cannot be negative")
        if self.failed < 0:
            raise ValueError("failed cannot be negative")
        if self.skipped < 0:
            raise ValueError("skipped cannot be negative")
        if self.in_progress < 0:
            raise ValueError("in_progress cannot be negative")
        if self.duration_seconds < 0:
            raise ValueError("duration_seconds cannot be negative")
        if self.end_time < self.start_time:
            raise ValueError("end_time cannot be before start_time")

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage.

        Returns:
            Success rate as percentage (0-100)
        """
        if self.total_items == 0:
            return 0.0
        return (self.completed / self.total_items) * 100

    @property
    def throughput_per_hour(self) -> float | None:
        """Calculate throughput in items per hour.

        Returns:
            Items per hour, or None if duration is too short (< 1 second)
        """
        if self.duration_seconds < 1.0:
            return None
        items_per_second = self.completed / self.duration_seconds
        return items_per_second * 3600

    def format_duration(self) -> str:
        """Format duration in human-readable format.

        Returns:
            Formatted duration string
        """
        duration = timedelta(seconds=self.duration_seconds)
        hours, remainder = divmod(duration.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if duration.days > 0:
            return f"{duration.days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        return {
            "total_items": self.total_items,
            "completed": self.completed,
            "failed": self.failed,
            "skipped": self.skipped,
            "in_progress": self.in_progress,
            "duration_seconds": self.duration_seconds,
            "duration_formatted": self.format_duration(),
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "success_rate": round(self.success_rate, 2),
            "throughput_per_hour": (
                round(self.throughput_per_hour, 2) if self.throughput_per_hour is not None else None
            ),
            "failures": [f.to_dict() for f in self.failures],
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string.

        Args:
            indent: Number of spaces for indentation (default: 2)

        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=indent)

    def save_to_file(self, file_path: str | Path) -> None:
        """Save summary report to JSON file.

        Args:
            file_path: Path to save the JSON file
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json())

    def format_console_summary(self) -> str:
        """Format summary for console display.

        Returns:
            Formatted multi-line summary string
        """
        lines = [
            "\n" + "=" * 60,
            "COPY OPERATION SUMMARY",
            "=" * 60,
            f"Total Items:      {self.total_items}",
            f"Completed:        {self.completed}",
            f"Failed:           {self.failed}",
            f"Skipped:          {self.skipped}",
            f"In Progress:      {self.in_progress}",
            "",
            f"Success Rate:     {self.success_rate:.1f}%",
            f"Duration:         {self.format_duration()}",
            (
                f"Throughput:       {self.throughput_per_hour:.1f} items/hour"
                if self.throughput_per_hour is not None
                else "Throughput:       N/A (duration too short)"
            ),
            "",
            f"Started:          {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Ended:            {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}",
        ]

        if self.failures:
            lines.extend(
                [
                    "",
                    f"FAILURES ({len(self.failures)}):",
                    "-" * 60,
                ]
            )
            for i, failure in enumerate(self.failures, 1):
                lines.append(f"{i}. {failure.recovery_point_arn}")
                lines.append(f"   Error: {failure.error_message}")
                if failure.timestamp:
                    lines.append(f"   Time: {failure.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

        lines.append("=" * 60)
        return "\n".join(lines)


if __name__ == "__main__":
    # Example usage
    info = file_info()
    print(f"{info['name']} v{info['version']}")
