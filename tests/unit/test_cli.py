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
    args = parser.parse_args([
        "--region", "us-west-2",
        "list",
        "--source-account", "123456789012",
    ])

    assert args.command == "list"
    assert args.source_account == "123456789012"
    assert args.region == "us-west-2"


def test_parser_list_command_with_vault() -> None:
    """Test list command with specific vault."""
    parser = create_parser()
    args = parser.parse_args([
        "list",
        "--source-account", "123456789012",
        "--vault", "my-vault",
    ])

    assert args.vault == "my-vault"


def test_parser_filter_command() -> None:
    """Test filter command parsing."""
    parser = create_parser()
    args = parser.parse_args([
        "filter",
        "--source-account", "123456789012",
        "--config", "filter.yaml",
    ])

    assert args.command == "filter"
    assert args.source_account == "123456789012"
    assert args.config == "filter.yaml"


def test_parser_copy_command() -> None:
    """Test copy command parsing."""
    parser = create_parser()
    args = parser.parse_args([
        "copy",
        "--source-account", "111111111111",
        "--dest-account", "222222222222",
        "--batch-size", "20",
    ])

    assert args.command == "copy"
    assert args.source_account == "111111111111"
    assert args.dest_account == "222222222222"
    assert args.batch_size == 20


def test_parser_verify_command() -> None:
    """Test verify command parsing."""
    parser = create_parser()
    args = parser.parse_args([
        "verify",
        "--source-account", "111111111111",
        "--dest-account", "222222222222",
    ])

    assert args.command == "verify"
    assert args.source_account == "111111111111"
    assert args.dest_account == "222222222222"


def test_parser_dry_run_flag() -> None:
    """Test dry-run flag."""
    parser = create_parser()
    args = parser.parse_args([
        "--dry-run",
        "list",
        "--source-account", "123456789012",
    ])

    assert args.dry_run is True


def test_parser_verbose_flag() -> None:
    """Test verbose flag."""
    parser = create_parser()
    args = parser.parse_args([
        "-v",
        "list",
        "--source-account", "123456789012",
    ])

    assert args.verbose is True
