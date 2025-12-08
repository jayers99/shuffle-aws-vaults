#!/usr/bin/env python3
"""
CLI entry point for shuffle-aws-vaults.

Provides command-line interface for migrating AWS Backup recovery points between accounts
with filtering and progress tracking capabilities.
"""

import argparse
import json
import sys
from typing import NoReturn

from shuffle_aws_vaults.application.list_service import ListService
from shuffle_aws_vaults.infrastructure.aws_backup_repository import AWSBackupRepository
from shuffle_aws_vaults.infrastructure.logger import setup_logger

__version__ = "0.1.0"
__author__ = "John Ayers"


def file_info() -> dict[str, str]:
    """Return metadata about this module.

    Returns:
        Dictionary containing module metadata
    """
    return {
        "name": "cli",
        "description": "Command-line interface for shuffle-aws-vaults",
        "version": __version__,
        "author": __author__,
        "last_updated": "2025-12-07",
    }


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog="shuffle-aws-vaults",
        description="Migrate AWS Backup recovery points between accounts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region (default: us-east-1)",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # list command
    list_parser = subparsers.add_parser(
        "list",
        help="List vaults and recovery points in source account",
    )
    list_parser.add_argument(
        "--source-account",
        required=True,
        help="Source AWS account ID",
    )
    list_parser.add_argument(
        "--vault",
        help="Specific vault name (optional, lists all if not specified)",
    )

    # filter command
    filter_parser = subparsers.add_parser(
        "filter",
        help="Apply filter rules to recovery points",
    )
    filter_parser.add_argument(
        "--config",
        required=True,
        help="Path to filter configuration file",
    )
    filter_parser.add_argument(
        "--source-account",
        required=True,
        help="Source AWS account ID",
    )

    # copy command
    copy_parser = subparsers.add_parser(
        "copy",
        help="Copy recovery points to destination account",
    )
    copy_parser.add_argument(
        "--source-account",
        required=True,
        help="Source AWS account ID",
    )
    copy_parser.add_argument(
        "--dest-account",
        required=True,
        help="Destination AWS account ID",
    )
    copy_parser.add_argument(
        "--config",
        help="Path to filter configuration file (optional)",
    )
    copy_parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of recovery points to copy in parallel (default: 10)",
    )

    # verify command
    verify_parser = subparsers.add_parser(
        "verify",
        help="Verify successful migration",
    )
    verify_parser.add_argument(
        "--source-account",
        required=True,
        help="Source AWS account ID",
    )
    verify_parser.add_argument(
        "--dest-account",
        required=True,
        help="Destination AWS account ID",
    )

    return parser


def cmd_list(args: argparse.Namespace) -> int:
    """Execute list command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    logger = setup_logger(verbose=args.verbose)

    logger.info(f"Listing vaults in account {args.source_account} (region: {args.region})")
    if args.vault:
        logger.info(f"  Filtering for vault: {args.vault}")
    if args.dry_run:
        logger.info("  [DRY RUN]")
        return 0

    try:
        # Create repository and service
        backup_repo = AWSBackupRepository(account_id=args.source_account)
        list_service = ListService(backup_repo, dry_run=args.dry_run)

        # List vaults
        if args.vault:
            # List recovery points for specific vault
            logger.info(f"Listing recovery points in vault: {args.vault}")
            recovery_points = list_service.list_vault_recovery_points(
                args.vault, args.region
            )

            logger.info(f"Found {len(recovery_points)} recovery points")

            # Display recovery points
            if args.output == "json":
                output_data = [
                    {
                        "recovery_point_arn": rp.recovery_point_arn,
                        "vault_name": rp.backup_vault_name,
                        "resource_arn": rp.resource_arn,
                        "resource_type": rp.resource_type,
                        "creation_date": rp.creation_date.isoformat(),
                        "status": rp.status,
                        "size_gb": rp.size_gb(),
                    }
                    for rp in recovery_points
                ]
                print(json.dumps(output_data, indent=2))
            else:
                for rp in recovery_points:
                    print(f"Recovery Point: {rp.recovery_point_arn}")
                    print(f"  Vault: {rp.backup_vault_name}")
                    print(f"  Resource: {rp.resource_arn}")
                    print(f"  Type: {rp.resource_type}")
                    print(f"  Created: {rp.creation_date}")
                    print(f"  Status: {rp.status}")
                    print(f"  Size: {rp.size_gb()} GB")
                    print()
        else:
            # List all vaults
            logger.info("Listing all vaults...")
            vaults = list_service.list_all_vaults(args.region)

            logger.info(f"Found {len(vaults)} vaults")

            # Display vaults
            if args.output == "json":
                summary = list_service.get_vault_summary(args.region)
                output_data = {
                    "vaults": [
                        {
                            "name": vault.name,
                            "arn": vault.arn,
                            "region": vault.region,
                            "recovery_point_count": vault.recovery_point_count,
                            "encrypted": vault.is_encrypted(),
                            "encryption_key_arn": vault.encryption_key_arn,
                        }
                        for vault in vaults
                    ],
                    "summary": summary,
                }
                print(json.dumps(output_data, indent=2))
            else:
                for vault in vaults:
                    print(f"Vault: {vault.name}")
                    print(f"  ARN: {vault.arn}")
                    print(f"  Region: {vault.region}")
                    print(f"  Recovery Points: {vault.recovery_point_count}")
                    if vault.is_encrypted():
                        print(f"  Encryption: {vault.encryption_key_arn}")
                    print()

                # Display summary
                summary = list_service.get_vault_summary(args.region)
                print("Summary:")
                print(f"  Total Vaults: {summary['vault_count']}")
                print(f"  Total Recovery Points: {summary['total_recovery_points']}")
                print(f"  Encrypted Vaults: {summary['encrypted_vaults']}")
                print(f"  Empty Vaults: {summary['empty_vaults']}")

        return 0

    except Exception as e:
        logger.error(f"Error listing vaults: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def cmd_filter(args: argparse.Namespace) -> int:
    """Execute filter command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    print(f"Applying filters from {args.config}")
    print(f"  Source account: {args.source_account}")
    if args.dry_run:
        print("  [DRY RUN]")
    # TODO: Implement actual filtering logic
    return 0


def cmd_copy(args: argparse.Namespace) -> int:
    """Execute copy command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    print(f"Copying recovery points:")
    print(f"  Source: {args.source_account}")
    print(f"  Destination: {args.dest_account}")
    print(f"  Batch size: {args.batch_size}")
    if args.config:
        print(f"  Filter config: {args.config}")
    if args.dry_run:
        print("  [DRY RUN]")
    # TODO: Implement actual copy logic
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Execute verify command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    print(f"Verifying migration:")
    print(f"  Source: {args.source_account}")
    print(f"  Destination: {args.dest_account}")
    # TODO: Implement actual verification logic
    return 0


def main() -> NoReturn:
    """Main entry point for the CLI.

    Parses arguments and dispatches to appropriate command handler.
    """
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Dispatch to command handlers
    commands = {
        "list": cmd_list,
        "filter": cmd_filter,
        "copy": cmd_copy,
        "verify": cmd_verify,
    }

    exit_code = commands[args.command](args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
