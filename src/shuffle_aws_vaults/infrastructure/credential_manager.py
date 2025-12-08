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

    Lock Ordering:
        To avoid deadlocks, locks must always be acquired in this order:
        1. _refresh_lock (global credential refresh)
        2. _session_lock (session dictionary access)

        Never acquire _refresh_lock while holding _session_lock.
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

    def _is_transient_error(self, error: ClientError) -> bool:
        """Check if error is transient and should be retried.

        Args:
            error: ClientError from boto3

        Returns:
            True if error is transient (throttling, timeouts, service unavailable)
        """
        error_code = error.response.get("Error", {}).get("Code", "")
        return error_code in [
            "Throttling",
            "ThrottlingException",
            "TooManyRequestsException",
            "RequestLimitExceeded",
            "ServiceUnavailable",
            "InternalError",
            "InternalFailure",
            "RequestTimeout",
            "RequestTimeoutException",
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
        """Decorator to wrap functions with credential and transient error retry logic.

        Handles two types of errors:
        1. Transient AWS errors (throttling, timeouts, service unavailable): retries with
           exponential backoff up to 3 attempts
        2. Credential errors: refreshes credentials and retries, with user prompt after
           MAX_AUTH_FAILURES consecutive failures

        Thread-safe: uses global refresh lock to pause all workers during
        credential refresh operations.

        Args:
            func: Function to wrap

        Returns:
            Wrapped function with retry logic
        """

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Transient error retry parameters
            max_transient_attempts = 3
            initial_delay = 1.0
            max_delay = 60.0
            exponential_base = 2.0

            transient_attempt = 0
            transient_delay = initial_delay

            # Outer loop for transient error retries
            while transient_attempt < max_transient_attempts:
                try:
                    # Inner loop for credential error retries
                    for cred_attempt in range(len(self.RETRY_DELAYS) + 1):
                        try:
                            result = func(*args, **kwargs)
                            # Success - reset failure count
                            if self._auth_failure_count > 0:
                                logger.info("Operation succeeded after credential refresh")
                                self._auth_failure_count = 0
                            return result

                        except ClientError as e:
                            if not self._is_credential_error(e):
                                # Not a credential error, propagate to outer try/except
                                raise

                            # Acquire global refresh lock to pause all workers
                            # Only one thread handles credential refresh at a time
                            with self._refresh_lock:
                                self._auth_failure_count += 1
                                logger.warning(
                                    f"Credential error detected (attempt {cred_attempt + 1}): {e.response['Error']['Code']}"
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
                                if cred_attempt < len(self.RETRY_DELAYS):
                                    delay = self.RETRY_DELAYS[cred_attempt]
                                    logger.info(f"Refreshing credentials and retrying in {delay}s...")
                                    self.clear_sessions()
                                    time.sleep(delay)
                                else:
                                    # Out of retries
                                    logger.error("Exhausted all retry attempts")
                                    raise

                    # Should never reach here
                    raise RuntimeError("Unexpected state in credential retry logic")

                except ClientError as e:
                    # Check if it's a transient error
                    if not self._is_transient_error(e):
                        # Not transient, not credential - don't retry
                        raise

                    transient_attempt += 1
                    if transient_attempt >= max_transient_attempts:
                        # Out of transient retries
                        logger.error(f"Failed after {max_transient_attempts} transient error retries")
                        raise

                    # Log and retry with exponential backoff
                    logger.warning(
                        f"Transient error in {func.__name__} (attempt {transient_attempt}/{max_transient_attempts}): "
                        f"{e.response['Error']['Code']}. Retrying in {transient_delay:.1f}s..."
                    )
                    time.sleep(transient_delay)
                    transient_delay = min(transient_delay * exponential_base, max_delay)

            # Should never reach here
            raise RuntimeError("Unexpected state in transient retry logic")

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
