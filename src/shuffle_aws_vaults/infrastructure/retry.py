#!/usr/bin/env python3
"""
Retry logic for handling transient AWS errors.

Provides exponential backoff retry decorator for AWS API calls.
"""

import logging
import time
from functools import wraps
from typing import Any, Callable, TypeVar

from botocore.exceptions import ClientError

__version__ = "0.1.0"
__author__ = "John Ayers"

logger = logging.getLogger(__name__)

# Type variable for generic function return type
T = TypeVar("T")


def file_info() -> dict[str, str]:
    """Return metadata about this module.

    Returns:
        Dictionary containing module metadata
    """
    return {
        "name": "retry",
        "description": "Retry logic for AWS operations",
        "version": __version__,
        "author": __author__,
        "last_updated": "2025-12-07",
    }


# AWS error codes that should trigger a retry
TRANSIENT_ERROR_CODES = {
    "Throttling",
    "ThrottlingException",
    "TooManyRequestsException",
    "RequestLimitExceeded",
    "ServiceUnavailable",
    "InternalError",
    "InternalFailure",
    "RequestTimeout",
    "RequestTimeoutException",
}


def is_transient_error(error: Exception) -> bool:
    """Check if an error is transient and should be retried.

    Args:
        error: The exception to check

    Returns:
        True if the error is transient and should be retried
    """
    if isinstance(error, ClientError):
        error_code = error.response.get("Error", {}).get("Code", "")
        return error_code in TRANSIENT_ERROR_CODES
    return False


def with_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to retry a function with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts (default: 3)
        initial_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        exponential_base: Base for exponential backoff (default: 2.0)

    Returns:
        Decorator function

    Example:
        @with_retry(max_attempts=5)
        def start_copy_job(...):
            # AWS API call that might fail transiently
            pass
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            attempt = 1
            delay = initial_delay

            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if not is_transient_error(e) or attempt == max_attempts:
                        # Non-transient error or final attempt - raise
                        raise

                    # Log the retry attempt
                    logger.warning(
                        f"Transient error in {func.__name__} (attempt {attempt}/{max_attempts}): {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )

                    time.sleep(delay)
                    attempt += 1
                    delay = min(delay * exponential_base, max_delay)

            # This should never be reached, but satisfy type checker
            raise RuntimeError(f"Failed after {max_attempts} attempts")

        return wrapper

    return decorator


if __name__ == "__main__":
    # Example usage
    info = file_info()
    print(f"{info['name']} v{info['version']}")
