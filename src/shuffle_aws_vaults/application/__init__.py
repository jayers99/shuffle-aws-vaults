#!/usr/bin/env python3
"""
Application layer for shuffle-aws-vaults.

Orchestrates use cases and workflows by coordinating domain logic
and infrastructure operations.
"""

__version__ = "0.1.0"
__author__ = "John Ayers"


def file_info() -> dict[str, str]:
    """Return metadata about this module.

    Returns:
        Dictionary containing module metadata
    """
    return {
        "name": "application.__init__",
        "description": "Application layer initialization",
        "version": __version__,
        "author": __author__,
        "last_updated": "2025-12-07",
    }
