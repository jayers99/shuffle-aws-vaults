#!/usr/bin/env python3
"""
shuffle-aws-vaults: CLI tool to migrate AWS Backup recovery points between accounts.

This package provides functionality to copy recovery points from a source AWS account
to a destination account, replicating vault structures and applying configurable filters.
"""

__version__ = "0.1.0"
__author__ = "John Ayers"


def file_info() -> dict[str, str]:
    """Return metadata about this module.

    Returns:
        Dictionary containing module metadata
    """
    return {
        "name": "__init__",
        "description": "Package initialization for shuffle-aws-vaults",
        "version": __version__,
        "author": __author__,
        "last_updated": "2025-12-07",
    }
