#!/usr/bin/env python3
"""
CSV metadata repository for loading external metadata.

Provides CSV file reading and parsing with resourceArn indexing.
"""

import csv
from pathlib import Path
from typing import Optional

__version__ = "0.1.0"
__author__ = "John Ayers"


def file_info() -> dict[str, str]:
    """Return metadata about this module.

    Returns:
        Dictionary containing module metadata
    """
    return {
        "name": "csv_metadata_repository",
        "description": "CSV metadata file loading and parsing",
        "version": __version__,
        "author": __author__,
        "last_updated": "2025-12-07",
    }


class CSVMetadataRepository:
    """Repository for loading metadata from CSV files."""

    def __init__(self, csv_path: str) -> None:
        """Initialize CSV metadata repository.

        Args:
            csv_path: Path to CSV file containing metadata
        """
        self.csv_path = Path(csv_path)
        self._metadata_cache: Optional[dict[str, dict[str, str]]] = None

    def load_metadata(self) -> dict[str, dict[str, str]]:
        """Load and parse CSV file, indexed by resourceArn.

        Returns:
            Dictionary mapping resourceArn to metadata dict

        Raises:
            FileNotFoundError: If CSV file doesn't exist
            ValueError: If CSV is malformed or missing resourceArn column
        """
        if self._metadata_cache is not None:
            return self._metadata_cache

        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_path}")

        metadata: dict[str, dict[str, str]] = {}

        with open(self.csv_path, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            if reader.fieldnames is None:
                raise ValueError(f"CSV file is empty: {self.csv_path}")

            if "resourceArn" not in reader.fieldnames:
                raise ValueError(
                    f"CSV file missing 'resourceArn' column. Found: {reader.fieldnames}"
                )

            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is 1)
                resource_arn = row.get("resourceArn", "").strip()

                if not resource_arn:
                    # Skip rows with empty resourceArn
                    continue

                # Store all fields from CSV row
                metadata[resource_arn] = {k: v for k, v in row.items() if v}

        self._metadata_cache = metadata
        return metadata

    def get_metadata_for_resource(self, resource_arn: str) -> Optional[dict[str, str]]:
        """Get metadata for a specific resource ARN.

        Args:
            resource_arn: AWS resource ARN to look up

        Returns:
            Metadata dict if found, None otherwise
        """
        metadata = self.load_metadata()
        return metadata.get(resource_arn)


if __name__ == "__main__":
    # Example usage
    info = file_info()
    print(f"{info['name']} v{info['version']}")
