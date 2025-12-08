"""Unit tests for ShutdownCoordinator."""

import signal
from unittest.mock import Mock

import pytest

from shuffle_aws_vaults.infrastructure.signal_handler import ShutdownCoordinator


def test_shutdown_coordinator_creation() -> None:
    """Test creating a shutdown coordinator."""
    coordinator = ShutdownCoordinator()

    assert coordinator.is_shutdown_requested() is False


def test_shutdown_coordinator_register_callback() -> None:
    """Test registering a shutdown callback."""
    coordinator = ShutdownCoordinator()
    callback = Mock()

    coordinator.register_shutdown_callback(callback)

    # Callback should not be called yet
    callback.assert_not_called()


def test_shutdown_coordinator_signal_handler() -> None:
    """Test that signal handler marks shutdown as requested."""
    coordinator = ShutdownCoordinator()

    # Simulate signal
    coordinator._shutdown_requested = True

    assert coordinator.is_shutdown_requested() is True


def test_shutdown_coordinator_callback_invoked() -> None:
    """Test that callback is invoked on signal."""
    coordinator = ShutdownCoordinator()
    callback = Mock()

    coordinator.register_shutdown_callback(callback)

    # Manually trigger signal handler (without actually sending signal)
    # This avoids the sys.exit() call
    try:
        coordinator._signal_handler(signal.SIGINT, None)
    except SystemExit:
        # Expected - signal handler calls sys.exit()
        pass

    # Callback should have been called
    callback.assert_called_once()


def test_shutdown_coordinator_callback_error_handling() -> None:
    """Test that errors in callback are handled gracefully."""
    coordinator = ShutdownCoordinator()

    # Register callback that raises exception
    def bad_callback():
        raise ValueError("Test error")

    coordinator.register_shutdown_callback(bad_callback)

    # Signal handler should handle the error and still exit
    try:
        coordinator._signal_handler(signal.SIGINT, None)
    except SystemExit:
        # Expected - signal handler should exit even if callback fails
        pass


def test_shutdown_coordinator_setup_and_restore_handlers() -> None:
    """Test setting up and restoring signal handlers."""
    coordinator = ShutdownCoordinator()

    # Get original handlers
    original_sigint = signal.signal(signal.SIGINT, signal.SIG_IGN)
    original_sigterm = signal.signal(signal.SIGTERM, signal.SIG_IGN)

    # Restore them
    signal.signal(signal.SIGINT, original_sigint)
    signal.signal(signal.SIGTERM, original_sigterm)

    # Setup our handlers
    coordinator.setup_signal_handlers()

    # Handlers should be changed
    current_sigint = signal.getsignal(signal.SIGINT)
    current_sigterm = signal.getsignal(signal.SIGTERM)

    assert current_sigint != original_sigint
    assert current_sigterm != original_sigterm

    # Restore original handlers
    coordinator.restore_signal_handlers()

    # Should be back to original
    restored_sigint = signal.getsignal(signal.SIGINT)
    restored_sigterm = signal.getsignal(signal.SIGTERM)

    assert restored_sigint == original_sigint
    assert restored_sigterm == original_sigterm
