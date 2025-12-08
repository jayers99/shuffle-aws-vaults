#!/usr/bin/env python3
"""
Signal handler for graceful shutdown.

Coordinates shutdown across operations when SIGINT or SIGTERM is received.
"""

import signal
import sys
from typing import Callable, Optional

__version__ = "0.1.0"
__author__ = "John Ayers"


def file_info() -> dict[str, str]:
    """Return metadata about this module.

    Returns:
        Dictionary containing module metadata
    """
    return {
        "name": "signal_handler",
        "description": "Signal handler for graceful shutdown",
        "version": __version__,
        "author": __author__,
        "last_updated": "2025-12-07",
    }


class ShutdownCoordinator:
    """Coordinates graceful shutdown on SIGINT/SIGTERM."""

    def __init__(self) -> None:
        """Initialize the shutdown coordinator."""
        self._shutdown_requested = False
        self._shutdown_callback: Optional[Callable[[], None]] = None
        self._original_sigint_handler = None
        self._original_sigterm_handler = None

    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested.

        Returns:
            True if shutdown was requested
        """
        return self._shutdown_requested

    def register_shutdown_callback(self, callback: Callable[[], None]) -> None:
        """Register a callback to be called on shutdown.

        Args:
            callback: Function to call when shutdown is requested
        """
        self._shutdown_callback = callback

    def setup_signal_handlers(self) -> None:
        """Setup signal handlers for SIGINT and SIGTERM."""
        # Store original handlers
        self._original_sigint_handler = signal.signal(signal.SIGINT, self._signal_handler)
        self._original_sigterm_handler = signal.signal(signal.SIGTERM, self._signal_handler)

    def restore_signal_handlers(self) -> None:
        """Restore original signal handlers."""
        if self._original_sigint_handler is not None:
            signal.signal(signal.SIGINT, self._original_sigint_handler)
        if self._original_sigterm_handler is not None:
            signal.signal(signal.SIGTERM, self._original_sigterm_handler)

    def _signal_handler(self, signum: int, frame) -> None:
        """Handle SIGINT and SIGTERM signals.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        # Mark shutdown as requested
        self._shutdown_requested = True

        # Print newline for clean output after Ctrl-C
        print("\nShutdown requested, saving state and exiting gracefully...")
        sys.stdout.flush()

        # Call shutdown callback if registered
        if self._shutdown_callback is not None:
            try:
                self._shutdown_callback()
            except Exception as e:
                print(f"Error during shutdown: {e}")
                sys.stdout.flush()

        # Restore original handlers
        self.restore_signal_handlers()

        # Exit cleanly
        sys.exit(0)


if __name__ == "__main__":
    # Example usage
    info = file_info()
    print(f"{info['name']} v{info['version']}")
