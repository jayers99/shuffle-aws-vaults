#!/usr/bin/env python3
"""
CSV metadata repository for loading external metadata.

Provides CSV file reading and parsing with resourceArn indexing.
Optimized for large CSV files (1M+ rows) with streaming parsing
and progress tracking.
"""

import csv
import logging
from pathlib import Path
from typing import Callable, Optional

__version__ = "0.1.0"
__author__ = "John Ayers"

logger = logging.getLogger(__name__)


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
    """Repository for loading metadata from CSV files.

    Optimized for large CSV files with:
    - Lazy loading (only loads when first accessed)
    - O(1) lookups via resourceArn index
    - Streaming row-by-row parsing for memory efficiency
    - Progress tracking for large files
    """

    # Report progress every N rows
    PROGRESS_INTERVAL = 10000

    def __init__(
        self, csv_path: str, progress_callback: Optional[Callable[[int], None]] = None
    ) -> None:
        """Initialize CSV metadata repository.

        Args:
            csv_path: Path to CSV file containing metadata
            progress_callback: Optional callback for progress updates (called with row count)
        """
        self.csv_path = Path(csv_path)
        self._metadata_cache: Optional[dict[str, dict[str, str]]] = None
        self._progress_callback = progress_callback
        self._total_rows: int = 0

    def load_metadata(self) -> dict[str, dict[str, str]]:
        """Load and parse CSV file, indexed by resourceArn.

        Uses streaming row-by-row parsing for memory efficiency.
        Reports progress every PROGRESS_INTERVAL rows for large files.

        Returns:
            Dictionary mapping resourceArn to metadata dict

        Raises:
            FileNotFoundError: If CSV file doesn't exist
            ValueError: If CSV is malformed or missing resourceArn column
        """
        # Return cached data if already loaded
        if self._metadata_cache is not None:
            logger.debug(f"Returning cached metadata ({self._total_rows} rows)")
            return self._metadata_cache

        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_path}")

        logger.info(f"Loading CSV metadata from: {self.csv_path}")

        metadata: dict[str, dict[str, str]] = {}
        rows_processed = 0
        rows_with_data = 0

        # Stream CSV file row by row
        with open(self.csv_path, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            if reader.fieldnames is None:
                raise ValueError(f"CSV file is empty: {self.csv_path}")

            if "resourceArn" not in reader.fieldnames:
                raise ValueError(
                    f"CSV file missing 'resourceArn' column. Found: {reader.fieldnames}"
                )

            for row in reader:
                rows_processed += 1

                # Report progress periodically
                if rows_processed % self.PROGRESS_INTERVAL == 0:
                    logger.info(f"Processed {rows_processed:,} CSV rows...")
                    if self._progress_callback:
                        self._progress_callback(rows_processed)

                resource_arn = row.get("resourceArn", "").strip()

                if not resource_arn:
                    # Skip rows with empty resourceArn
                    continue

                rows_with_data += 1

                # Store all non-empty fields from CSV row
                # Build dict incrementally to avoid storing entire row in memory
                metadata[resource_arn] = {k: v for k, v in row.items() if v}

        self._total_rows = rows_with_data
        self._metadata_cache = metadata

        logger.info(
            f"CSV loading complete: {rows_with_data:,} records indexed "
            f"from {rows_processed:,} total rows"
        )

        # Final progress callback
        if self._progress_callback:
            self._progress_callback(rows_processed)

        return metadata

    def get_metadata_for_resource(self, resource_arn: str) -> Optional[dict[str, str]]:
        """Get metadata for a specific resource ARN.

        O(1) lookup using resourceArn index.

        Args:
            resource_arn: AWS resource ARN to look up

        Returns:
            Metadata dict if found, None otherwise
        """
        # Lazy load metadata on first access
        metadata = self.load_metadata()
        return metadata.get(resource_arn)

    @property
    def row_count(self) -> int:
        """Get count of indexed rows.

        Returns:
            Number of rows with resourceArn in the loaded CSV, or 0 if not loaded
        """
        return self._total_rows

    @property
    def is_loaded(self) -> bool:
        """Check if CSV has been loaded into memory.

        Returns:
            True if CSV has been loaded, False otherwise
        """
        return self._metadata_cache is not None


if __name__ == "__main__":
    # Example usage
    info = file_info()
    print(f"{info['name']} v{info['version']}")
