#!/usr/bin/env python3
"""
Infrastructure layer for shuffle-aws-vaults.

Handles AWS SDK calls, configuration, logging, and I/O operations.
"""

__version__ = "0.1.0"
__author__ = "John Ayers"


def file_info() -> dict[str, str]:
    """Return metadata about this module.

    Returns:
        Dictionary containing module metadata
    """
    return {
        "name": "infrastructure.__init__",
        "description": "Infrastructure layer initialization",
        "version": __version__,
        "author": __author__,
        "last_updated": "2025-12-07",
    }
