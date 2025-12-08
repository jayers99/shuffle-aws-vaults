"""Unit tests for CLI module."""

import pytest

from shuffle_aws_vaults.cli import create_parser, file_info


def test_file_info() -> None:
    """Test file_info function returns expected metadata."""
    info = file_info()
    assert info["name"] == "cli"
    assert info["version"] == "0.1.0"
    assert info["author"] == "John Ayers"


def test_parser_creation() -> None:
    """Test parser creation."""
    parser = create_parser()
    assert parser.prog == "shuffle-aws-vaults"


def test_parser_version() -> None:
    """Test version flag."""
    parser = create_parser()

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--version"])

    assert exc_info.value.code == 0


def test_parser_list_command() -> None:
    """Test list command parsing."""
    parser = create_parser()
    args = parser.parse_args(
        [
            "--region",
            "us-west-2",
            "list",
            "--source-account",
            "123456789012",
        ]
    )

    assert args.command == "list"
    assert args.source_account == "123456789012"
    assert args.region == "us-west-2"


def test_parser_list_command_with_vault() -> None:
    """Test list command with specific vault."""
    parser = create_parser()
    args = parser.parse_args(
        [
            "list",
            "--source-account",
            "123456789012",
            "--vault",
            "my-vault",
        ]
    )

    assert args.vault == "my-vault"


def test_parser_filter_command() -> None:
    """Test filter command parsing."""
    parser = create_parser()
    args = parser.parse_args(
        [
            "filter",
            "--source-account",
            "123456789012",
            "--vault",
            "test-vault",
            "--allowed-apmids",
            "APP001,APP002",
            "--metadata-csv",
            "metadata.csv",
        ]
    )

    assert args.command == "filter"
    assert args.source_account == "123456789012"
    assert args.vault == "test-vault"
    assert args.allowed_apmids == "APP001,APP002"
    assert args.metadata_csv == "metadata.csv"


def test_parser_copy_command() -> None:
    """Test copy command parsing."""
    parser = create_parser()
    args = parser.parse_args(
        [
            "copy",
            "--source-account",
            "111111111111",
            "--dest-account",
            "222222222222",
            "--vault",
            "test-vault",
            "--poll-interval",
            "60",
        ]
    )

    assert args.command == "copy"
    assert args.source_account == "111111111111"
    assert args.dest_account == "222222222222"
    assert args.vault == "test-vault"
    assert args.poll_interval == 60


def test_parser_copy_command_with_resume_flags() -> None:
    """Test copy command with resume/reset flags."""
    parser = create_parser()

    # Test with --resume flag
    args_resume = parser.parse_args(
        [
            "copy",
            "--source-account",
            "111111111111",
            "--dest-account",
            "222222222222",
            "--vault",
            "test-vault",
            "--resume",
        ]
    )
    assert args_resume.resume is True
    assert args_resume.reset is False

    # Test with --reset flag
    args_reset = parser.parse_args(
        [
            "copy",
            "--source-account",
            "111111111111",
            "--dest-account",
            "222222222222",
            "--vault",
            "test-vault",
            "--reset",
        ]
    )
    assert args_reset.resume is False
    assert args_reset.reset is True

    # Test with --state-file
    args_state = parser.parse_args(
        [
            "copy",
            "--source-account",
            "111111111111",
            "--dest-account",
            "222222222222",
            "--vault",
            "test-vault",
            "--state-file",
            "/tmp/my-state.json",
        ]
    )
    assert args_state.state_file == "/tmp/my-state.json"


def test_parser_verify_command() -> None:
    """Test verify command parsing."""
    parser = create_parser()
    args = parser.parse_args(
        [
            "verify",
            "--source-account",
            "111111111111",
            "--dest-account",
            "222222222222",
        ]
    )

    assert args.command == "verify"
    assert args.source_account == "111111111111"
    assert args.dest_account == "222222222222"


def test_parser_dry_run_flag() -> None:
    """Test dry-run flag."""
    parser = create_parser()
    args = parser.parse_args(
        [
            "--dry-run",
            "list",
            "--source-account",
            "123456789012",
        ]
    )

    assert args.dry_run is True


def test_parser_verbose_flag() -> None:
    """Test verbose flag."""
    parser = create_parser()
    args = parser.parse_args(
        [
            "-v",
            "list",
            "--source-account",
            "123456789012",
        ]
    )

    assert args.verbose is True


def test_parser_copy_command_with_workers() -> None:
    """Test copy command with workers flag."""
    parser = create_parser()
    args = parser.parse_args(
        [
            "copy",
            "--source-account",
            "111111111111",
            "--dest-account",
            "222222222222",
            "--vault",
            "test-vault",
            "--workers",
            "10",
        ]
    )

    assert args.workers == 10


def test_parser_copy_command_with_max_runtime() -> None:
    """Test copy command with max-runtime-minutes flag."""
    parser = create_parser()
    args = parser.parse_args(
        [
            "copy",
            "--source-account",
            "111111111111",
            "--dest-account",
            "222222222222",
            "--vault",
            "test-vault",
            "--max-runtime-minutes",
            "120",
        ]
    )

    assert args.max_runtime_minutes == 120


def test_parser_copy_command_workers_validation() -> None:
    """Test that workers flag rejects invalid values."""
    parser = create_parser()

    # Test zero workers (invalid)
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "copy",
                "--source-account",
                "111111111111",
                "--dest-account",
                "222222222222",
                "--vault",
                "test-vault",
                "--workers",
                "0",
            ]
        )

    # Test negative workers (invalid)
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "copy",
                "--source-account",
                "111111111111",
                "--dest-account",
                "222222222222",
                "--vault",
                "test-vault",
                "--workers",
                "-5",
            ]
        )


def test_parser_copy_command_max_runtime_validation() -> None:
    """Test that max-runtime-minutes flag rejects invalid values."""
    parser = create_parser()

    # Test zero minutes (invalid)
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "copy",
                "--source-account",
                "111111111111",
                "--dest-account",
                "222222222222",
                "--vault",
                "test-vault",
                "--max-runtime-minutes",
                "0",
            ]
        )

    # Test negative minutes (invalid)
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "copy",
                "--source-account",
                "111111111111",
                "--dest-account",
                "222222222222",
                "--vault",
                "test-vault",
                "--max-runtime-minutes",
                "-30",
            ]
        )


def test_parser_copy_command_with_summary_output() -> None:
    """Test copy command with summary output flag."""
    parser = create_parser()
    args = parser.parse_args(
        [
            "copy",
            "--source-account",
            "111111111111",
            "--dest-account",
            "222222222222",
            "--vault",
            "test-vault",
            "--summary-output",
            "/path/to/summary.json",
        ]
    )

    assert args.summary_output == "/path/to/summary.json"
