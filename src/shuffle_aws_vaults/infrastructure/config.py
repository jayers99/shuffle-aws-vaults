#!/usr/bin/env python3
"""
Configuration management for shuffle-aws-vaults.

Handles loading and validation of configuration from environment and files.
"""

import os
from dataclasses import dataclass
from typing import Optional

__version__ = "0.1.0"
__author__ = "John Ayers"


def file_info() -> dict[str, str]:
    """Return metadata about this module.

    Returns:
        Dictionary containing module metadata
    """
    return {
        "name": "config",
        "description": "Configuration management",
        "version": __version__,
        "author": __author__,
        "last_updated": "2025-12-07",
    }


@dataclass
class AWSConfig:
    """AWS configuration settings.

    Attributes:
        source_account_id: Source AWS account ID
        dest_account_id: Destination AWS account ID
        source_role_arn: IAM role ARN for source account (optional)
        dest_role_arn: IAM role ARN for dest account (optional)
        region: Default AWS region
        dry_run: Whether to run in dry-run mode
        batch_size: Number of concurrent operations
    """

    source_account_id: str
    dest_account_id: str
    source_role_arn: Optional[str] = None
    dest_role_arn: Optional[str] = None
    region: str = "us-east-1"
    dry_run: bool = False
    batch_size: int = 10

    @classmethod
    def from_env(cls) -> "AWSConfig":
        """Load configuration from environment variables.

        Returns:
            AWSConfig instance

        Raises:
            ValueError: If required environment variables are missing
        """
        source_account = os.getenv("AWS_SOURCE_ACCOUNT_ID")
        dest_account = os.getenv("AWS_DEST_ACCOUNT_ID")

        if not source_account or not dest_account:
            raise ValueError(
                "AWS_SOURCE_ACCOUNT_ID and AWS_DEST_ACCOUNT_ID must be set"
            )

        return cls(
            source_account_id=source_account,
            dest_account_id=dest_account,
            source_role_arn=os.getenv("AWS_SOURCE_ROLE_ARN"),
            dest_role_arn=os.getenv("AWS_DEST_ROLE_ARN"),
            region=os.getenv("AWS_REGION", "us-east-1"),
            dry_run=os.getenv("DRY_RUN", "false").lower() == "true",
            batch_size=int(os.getenv("BATCH_SIZE", "10")),
        )


if __name__ == "__main__":
    # Example usage
    info = file_info()
    print(f"{info['name']} v{info['version']}")
