#!/usr/bin/env python3
"""
Domain layer for shuffle-aws-vaults.

Contains pure business logic with no external dependencies.
All domain objects are deterministic and testable without cloud infrastructure.
"""

__version__ = "0.1.0"
__author__ = "John Ayers"


def file_info() -> dict[str, str]:
    """Return metadata about this module.

    Returns:
        Dictionary containing module metadata
    """
    return {
        "name": "domain.__init__",
        "description": "Domain layer initialization",
        "version": __version__,
        "author": __author__,
        "last_updated": "2025-12-07",
    }
