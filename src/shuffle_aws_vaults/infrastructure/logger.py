#!/usr/bin/env python3
"""
Logging configuration for shuffle-aws-vaults.

Provides structured logging with appropriate levels for CLI and library usage.
"""

import logging
import sys

__version__ = "0.1.0"
__author__ = "John Ayers"


def file_info() -> dict[str, str]:
    """Return metadata about this module.

    Returns:
        Dictionary containing module metadata
    """
    return {
        "name": "logger",
        "description": "Logging configuration",
        "version": __version__,
        "author": __author__,
        "last_updated": "2025-12-07",
    }


def setup_logger(name: str = "shuffle_aws_vaults", verbose: bool = False) -> logging.Logger:
    """Configure and return a logger instance.

    Args:
        name: Logger name
        verbose: If True, set level to DEBUG; otherwise INFO

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(logging.DEBUG if verbose else logging.INFO)

        # Console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG if verbose else logging.INFO)

        # Format: timestamp - name - level - message
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)

        logger.addHandler(handler)

    return logger


def log_operation(
    logger: logging.Logger,
    operation: str,
    details: dict[str, any] | None = None,
    level: int = logging.INFO,
) -> None:
    """Log an operation with structured details.

    Args:
        logger: Logger instance
        operation: Operation description
        details: Optional dictionary of details
        level: Logging level
    """
    message = f"{operation}"
    if details:
        detail_str = ", ".join(f"{k}={v}" for k, v in details.items())
        message = f"{message} ({detail_str})"

    logger.log(level, message)


if __name__ == "__main__":
    # Example usage
    info = file_info()
    print(f"{info['name']} v{info['version']}")
