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
from shuffle_aws_vaults.application.metadata_enrichment_service import (
    MetadataEnrichmentService,
)
from shuffle_aws_vaults.infrastructure.aws_backup_repository import AWSBackupRepository
from shuffle_aws_vaults.infrastructure.csv_metadata_repository import CSVMetadataRepository
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
    list_parser.add_argument(
        "--metadata-csv",
        help="Path to CSV file with metadata (keyed by resourceArn)",
    )

    # filter command
    filter_parser = subparsers.add_parser(
        "filter",
        help="Apply filter rules to recovery points",
    )
    filter_parser.add_argument(
        "--source-account",
        required=True,
        help="Source AWS account ID",
    )
    filter_parser.add_argument(
        "--vault",
        required=True,
        help="Vault name to filter recovery points from",
    )
    filter_parser.add_argument(
        "--allowed-apmids",
        help="Comma-separated list of allowed APMIDs (e.g., 'APP001,APP002')",
    )
    filter_parser.add_argument(
        "--metadata-csv",
        help="Path to CSV file with metadata (required if using --allowed-apmids)",
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
        "--vault",
        required=True,
        help="Vault name to copy recovery points from",
    )
    copy_parser.add_argument(
        "--config",
        help="Path to filter configuration file (optional)",
    )
    copy_parser.add_argument(
        "--poll-interval",
        type=int,
        default=30,
        help="Seconds between copy job status checks (default: 30)",
    )
    copy_parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from saved state (default behavior if state file exists)",
    )
    copy_parser.add_argument(
        "--reset",
        action="store_true",
        help="Ignore existing state and start fresh",
    )
    copy_parser.add_argument(
        "--state-file",
        default=".shuffle-state.json",
        help="Path to state file (default: .shuffle-state.json)",
    )
    copy_parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip IAM permission validation before starting copy",
    )
    copy_parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of concurrent worker threads (default: 1 for single-threaded)",
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

            # Enrich with CSV metadata if provided
            if args.metadata_csv:
                logger.info(f"Loading metadata from {args.metadata_csv}")
                csv_repo = CSVMetadataRepository(args.metadata_csv)
                enrichment_service = MetadataEnrichmentService(csv_repo)
                recovery_points = enrichment_service.enrich_recovery_points(recovery_points)

                stats = enrichment_service.get_enrichment_stats(recovery_points)
                logger.info(
                    f"Enriched {stats['enriched_count']}/{stats['total_count']} recovery points "
                    f"({stats['missing_count']} missing metadata)"
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
                        "metadata": rp.metadata if rp.metadata else None,
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
                    if rp.metadata:
                        print(f"  Metadata:")
                        for key, value in rp.metadata.items():
                            print(f"    {key}: {value}")
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
    from shuffle_aws_vaults.application.filter_service import FilterService
    from shuffle_aws_vaults.domain.filter_rule import FilterCriteria, FilterRule, FilterRuleSet

    logger = setup_logger(verbose=args.verbose)

    logger.info(
        f"Filtering recovery points from vault {args.vault} in account {args.source_account}"
    )

    # Validate that metadata-csv is provided if allowed-apmids is used
    if args.allowed_apmids and not args.metadata_csv:
        logger.error("--metadata-csv is required when using --allowed-apmids")
        return 1

    if args.dry_run:
        logger.info("  [DRY RUN]")
        return 0

    try:
        # Create repository and list service
        backup_repo = AWSBackupRepository(account_id=args.source_account)
        list_service = ListService(backup_repo, dry_run=args.dry_run)

        # List recovery points from vault
        logger.info(f"Loading recovery points from vault: {args.vault}")
        recovery_points = list_service.list_vault_recovery_points(args.vault, args.region)
        logger.info(f"Found {len(recovery_points)} recovery points")

        # Enrich with CSV metadata if provided
        if args.metadata_csv:
            logger.info(f"Loading metadata from {args.metadata_csv}")
            csv_repo = CSVMetadataRepository(args.metadata_csv)
            enrichment_service = MetadataEnrichmentService(csv_repo)
            recovery_points = enrichment_service.enrich_recovery_points(recovery_points)

            stats = enrichment_service.get_enrichment_stats(recovery_points)
            logger.info(
                f"Enriched {stats['enriched_count']}/{stats['total_count']} recovery points"
            )

        # Apply filters if specified
        if args.allowed_apmids:
            logger.info(f"Applying APMID filter: {args.allowed_apmids}")
            rules = FilterRuleSet(
                rules=[
                    FilterRule(FilterCriteria.APMID_IN_SET, args.allowed_apmids, include=True)
                ]
            )
            filter_service = FilterService(rules)

            # Get filter summary
            summary = filter_service.get_filter_summary(recovery_points)

            # Display summary
            print("\nFilter Summary:")
            print(f"  Total Recovery Points: {summary['total_count']}")
            print(f"  Included: {summary['included_count']}")
            print(f"  Excluded: {summary['excluded_count']}")
            print(f"  Inclusion Rate: {summary['inclusion_rate_percent']}%")
            print(f"  Total Size (Included): {summary['total_size_gb_included']} GB")
            print(f"  Total Size (Excluded): {summary['total_size_gb_excluded']} GB")

            # Display included recovery points if output is verbose
            if args.verbose:
                included, _ = filter_service.apply_filters(recovery_points)
                print("\nIncluded Recovery Points:")
                for rp in included:
                    print(f"  - {rp.recovery_point_arn}")
                    print(f"    APMID: {rp.get_metadata('APMID')}")
                    print(f"    Resource: {rp.resource_arn}")
                    print(f"    Size: {rp.size_gb()} GB")
        else:
            logger.info("No filters specified - showing all recovery points")
            print(f"\nTotal Recovery Points: {len(recovery_points)}")

        return 0

    except Exception as e:
        logger.error(f"Error filtering recovery points: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


def cmd_copy(args: argparse.Namespace) -> int:
    """Execute copy command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    from shuffle_aws_vaults.application.copy_service import CopyService
    from shuffle_aws_vaults.domain.state import CopyState
    from shuffle_aws_vaults.infrastructure.permission_validator import PermissionValidator
    from shuffle_aws_vaults.infrastructure.signal_handler import ShutdownCoordinator
    from shuffle_aws_vaults.infrastructure.state_repository import StateRepository

    logger = setup_logger(verbose=args.verbose)

    # Validate flags
    if args.resume and args.reset:
        logger.error("Cannot use --resume and --reset together")
        return 1

    # Initialize state repository
    state_repo = StateRepository(args.state_file)

    # Setup shutdown coordinator
    shutdown_coordinator = ShutdownCoordinator()

    # Load or create state
    copy_state: CopyState | None = None

    if args.reset:
        logger.info(f"Resetting state, ignoring existing state file: {args.state_file}")
        # Delete existing state
        state_repo.delete_state()
        copy_state = None
    else:
        # Try to load existing state (resume is default behavior)
        try:
            copy_state = state_repo.load_copy_state()
            if copy_state:
                logger.info(f"Resuming from state file: {args.state_file}")
                logger.info(
                    f"Found {len(copy_state.operations)} operations "
                    f"({copy_state.count_by_status('completed')} completed, "
                    f"{copy_state.count_by_status('pending')} pending, "
                    f"{copy_state.count_by_status('failed')} failed)"
                )
            else:
                logger.info("No existing state found, starting fresh")
        except ValueError as e:
            logger.error(f"Failed to load state: {e}")
            logger.info("Use --reset to start fresh")
            return 1

    # If no state exists, create new state
    if copy_state is None:
        copy_state = CopyState(
            source_account=args.source_account,
            dest_account=args.dest_account,
            vault_name="",  # Will be set when we know the vault
        )
        logger.info("Starting new copy operation")

    # Register shutdown callback to save state
    def save_state_on_shutdown():
        logger.info(f"Saving state to {args.state_file}...")
        state_repo.save_copy_state(copy_state)
        logger.info("State saved successfully")

    shutdown_coordinator.register_shutdown_callback(save_state_on_shutdown)
    shutdown_coordinator.setup_signal_handlers()

    logger.info(f"Copying recovery points:")
    logger.info(f"  Source: {args.source_account}")
    logger.info(f"  Destination: {args.dest_account}")
    logger.info(f"  Vault: {args.vault}")
    logger.info(f"  Poll interval: {args.poll_interval}s")
    logger.info(f"  State file: {args.state_file}")

    if args.config:
        logger.info(f"  Filter config: {args.config}")

    if args.dry_run:
        logger.info("  [DRY RUN]")
        return 0

    try:
        # Validate IAM permissions unless skipped
        if not args.skip_validation:
            logger.info("Validating IAM permissions...")
            validator = PermissionValidator(
                source_account_id=args.source_account,
                dest_account_id=args.dest_account,
            )

            all_granted, results = validator.validate_permissions(args.region)

            if not all_granted:
                logger.error("Missing required IAM permissions:")
                for result in results:
                    if not result.granted:
                        logger.error(f"  ✗ {result.permission}")
                        if result.error_message and args.verbose:
                            logger.error(f"    {result.error_message}")
                    elif args.verbose:
                        logger.info(f"  ✓ {result.permission}")

                logger.error("\nPermission validation failed. Use --skip-validation to bypass.")
                return 1

            logger.info("✓ All required permissions validated")

        # Create repository and services
        backup_repo = AWSBackupRepository(account_id=args.source_account)
        list_service = ListService(backup_repo, dry_run=args.dry_run)
        copy_service = CopyService(copy_repo=backup_repo, dry_run=args.dry_run)

        # List recovery points from vault
        logger.info(f"Loading recovery points from vault: {args.vault}")
        recovery_points = list_service.list_vault_recovery_points(args.vault, args.region)
        logger.info(f"Found {len(recovery_points)} recovery points")

        if len(recovery_points) == 0:
            logger.info("No recovery points to copy")
            return 0

        # Update state with vault name if not already set
        if not copy_state.vault_name:
            copy_state.vault_name = args.vault

        # Progress callback for logging
        def progress_callback(message: str, current: int, total: int) -> None:
            logger.info(f"[{current}/{total}] {message}")

        # Execute copy operation
        if args.workers > 1:
            logger.info(f"Starting multithreaded copy operation with {args.workers} workers...")
            batch = copy_service.copy_multithreaded(
                recovery_points=recovery_points,
                dest_account_id=args.dest_account,
                region=args.region,
                workers=args.workers,
                progress_callback=progress_callback,
                shutdown_check=shutdown_coordinator.is_shutdown_requested,
                poll_interval=args.poll_interval,
            )
        else:
            logger.info("Starting single-threaded copy operation...")
            batch = copy_service.copy_single_threaded(
                recovery_points=recovery_points,
                dest_account_id=args.dest_account,
                region=args.region,
                progress_callback=progress_callback,
                shutdown_check=shutdown_coordinator.is_shutdown_requested,
                poll_interval=args.poll_interval,
            )

        # Display summary
        logger.info("\nCopy operation completed:")
        logger.info(f"  Total: {len(batch.operations)}")
        logger.info(f"  Completed: {sum(1 for op in batch.operations if op.status.value == 'completed')}")
        logger.info(f"  Failed: {sum(1 for op in batch.operations if op.status.value == 'failed')}")
        logger.info(f"  Skipped: {sum(1 for op in batch.operations if op.status.value == 'skipped')}")
        logger.info(f"  In Progress: {sum(1 for op in batch.operations if op.status.value == 'in_progress')}")

        # Save final state
        save_state_on_shutdown()

        return 0

    except Exception as e:
        logger.error(f"Error during copy: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()

        # Save state on error
        save_state_on_shutdown()

        return 1
    finally:
        # Restore signal handlers
        shutdown_coordinator.restore_signal_handlers()


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
