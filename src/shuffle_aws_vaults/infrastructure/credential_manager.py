#!/usr/bin/env python3
"""
Credential manager for handling AWS credential expiration.

Manages credential lifecycle and handles expired token scenarios gracefully.
"""

import logging
import sys
import threading
import time
from functools import wraps
from typing import Any, Callable, TypeVar

import boto3
from botocore.exceptions import ClientError

__version__ = "0.1.0"
__author__ = "John Ayers"

logger = logging.getLogger(__name__)

T = TypeVar("T")


def file_info() -> dict[str, str]:
    """Return metadata about this module.

    Returns:
        Dictionary containing module metadata
    """
    return {
        "name": "credential_manager",
        "description": "Credential manager for handling AWS credential expiration",
        "version": __version__,
        "author": __author__,
        "last_updated": "2025-12-07",
    }


class CredentialManager:
    """Manages AWS credentials and handles expiration scenarios.

    This class is thread-safe for use in multi-threaded environments.
    """

    MAX_AUTH_FAILURES = 3
    RETRY_DELAYS = [1, 2, 4]  # Exponential backoff in seconds

    def __init__(self) -> None:
        """Initialize the credential manager."""
        self._sessions: dict[str, boto3.Session] = {}
        self._auth_failure_count = 0
        self._session_lock = threading.Lock()  # Protects session dict access
        self._refresh_lock = threading.Lock()  # Global lock for credential refresh

    def clear_sessions(self) -> None:
        """Clear all cached sessions to force credential reload.

        Thread-safe: acquires session lock before clearing.
        """
        logger.info("Clearing cached AWS sessions to refresh credentials")
        with self._session_lock:
            self._sessions.clear()

    def get_session(self, region: str) -> boto3.Session:
        """Get or create a boto3 session for a region.

        Thread-safe: acquires session lock before accessing dict.

        Args:
            region: AWS region

        Returns:
            boto3 Session
        """
        with self._session_lock:
            if region not in self._sessions:
                logger.debug(f"Creating new session for region {region}")
                self._sessions[region] = boto3.Session(region_name=region)
            return self._sessions[region]

    def _is_credential_error(self, error: ClientError) -> bool:
        """Check if error is credential-related.

        Args:
            error: ClientError from boto3

        Returns:
            True if error is credential-related
        """
        error_code = error.response.get("Error", {}).get("Code", "")
        return error_code in [
            "ExpiredToken",
            "ExpiredTokenException",
            "InvalidClientTokenId",
            "UnrecognizedClientException",
        ]

    def _wait_for_user_refresh(self) -> None:
        """Wait for user to refresh credentials and press a key."""
        print("\n" + "=" * 60)
        print("AWS credentials have expired multiple times.")
        print("Please refresh your credentials externally, then press Enter to continue...")
        print("=" * 60)
        sys.stdout.flush()

        try:
            input()
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled by user")
            sys.exit(1)

        logger.info("User pressed Enter, resuming with fresh credentials")
        self._auth_failure_count = 0

    def with_retry(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to wrap functions with credential retry logic.

        Thread-safe: uses global refresh lock to pause all workers during
        credential refresh operations.

        Args:
            func: Function to wrap

        Returns:
            Wrapped function with retry logic
        """

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            for attempt in range(len(self.RETRY_DELAYS) + 1):
                try:
                    result = func(*args, **kwargs)
                    # Success - reset failure count
                    if self._auth_failure_count > 0:
                        logger.info("Operation succeeded after credential refresh")
                        self._auth_failure_count = 0
                    return result

                except ClientError as e:
                    if not self._is_credential_error(e):
                        # Not a credential error, don't retry
                        raise

                    # Acquire global refresh lock to pause all workers
                    # Only one thread handles credential refresh at a time
                    with self._refresh_lock:
                        self._auth_failure_count += 1
                        logger.warning(
                            f"Credential error detected (attempt {attempt + 1}): {e.response['Error']['Code']}"
                        )

                        # Check if we've hit max failures
                        if self._auth_failure_count >= self.MAX_AUTH_FAILURES:
                            logger.warning(
                                f"Hit {self.MAX_AUTH_FAILURES} consecutive auth failures"
                            )
                            self._wait_for_user_refresh()
                            # Clear sessions to force fresh credentials
                            self.clear_sessions()
                            # Reset attempt counter to retry after user refresh
                            # This is safe because user has manually refreshed
                            continue

                        # Not max failures yet - clear sessions and retry with backoff
                        if attempt < len(self.RETRY_DELAYS):
                            delay = self.RETRY_DELAYS[attempt]
                            logger.info(f"Refreshing credentials and retrying in {delay}s...")
                            self.clear_sessions()
                            time.sleep(delay)
                        else:
                            # Out of retries
                            logger.error("Exhausted all retry attempts")
                            raise

            # Should never reach here, but just in case
            raise RuntimeError("Unexpected state in retry logic")

        return wrapper


# Global singleton instance
_credential_manager = CredentialManager()


def get_credential_manager() -> CredentialManager:
    """Get the global credential manager instance.

    Returns:
        Global CredentialManager instance
    """
    return _credential_manager


if __name__ == "__main__":
    # Example usage
    info = file_info()
    print(f"{info['name']} v{info['version']}")
