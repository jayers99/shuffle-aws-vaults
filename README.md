# shuffle-aws-vaults

CLI tool to migrate AWS Backup recovery points from a source account to a destination account at scale. Replicates vault structures, applies configurable filters to exclude unwanted recovery points, and tracks progress for large batch operations.

## Features

- **List & Discover**: Enumerate backup vaults and recovery points across AWS accounts and regions
- **Filter & Select**: Apply configurable rules to identify which recovery points to migrate
- **Copy at Scale**: Execute parallel copy operations with progress tracking and batch management
- **Verify Migration**: Validate successful migration by comparing source and destination
- **Safe by Default**: Dry-run mode and idempotent operations prevent accidents
- **Clean Architecture**: DDD-based design with domain, application, and infrastructure layers

## Architecture

This project follows Modern Software Engineering, TDD, and Domain-Driven Design principles:

```
src/shuffle_aws_vaults/
├── cli.py                    # CLI entry point with argparse
├── domain/                   # Pure business logic (no AWS dependencies)
│   ├── recovery_point.py     # Recovery point domain model
│   ├── vault.py             # Vault domain model
│   ├── filter_rule.py       # Filter rules and evaluation
│   └── migration_result.py  # Migration tracking and results
├── application/             # Use case orchestration
│   ├── list_service.py      # List vaults and recovery points
│   ├── filter_service.py    # Apply filter rules
│   ├── copy_service.py      # Execute copy operations
│   └── verify_service.py    # Verify migration results
└── infrastructure/          # AWS SDK integration
    ├── aws_backup_repository.py  # boto3 implementation
    ├── config.py                  # Configuration management
    └── logger.py                  # Logging setup
```

## Installation

### Prerequisites

- Python 3.12.10 (managed via `pyenv`)
- AWS credentials configured with appropriate permissions
- Pipenv for dependency management

### Setup

```bash
# Install Python version
pyenv install 3.12.10

# Install dependencies
pipenv install --dev

# Install package in editable mode
pipenv install -e .
```

## Usage

### Basic Commands

```bash
# List vaults in source account
shuffle-aws-vaults list \
  --source-account 123456789012 \
  --region us-east-1

# List specific vault
shuffle-aws-vaults list \
  --source-account 123456789012 \
  --vault my-backup-vault

# Apply filters to recovery points
shuffle-aws-vaults filter \
  --source-account 123456789012 \
  --config filters.yaml

# Copy recovery points to destination account
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --batch-size 20 \
  --region us-east-1

# Verify successful migration
shuffle-aws-vaults verify \
  --source-account 123456789012 \
  --dest-account 987654321098
```

### Global Options

- `--dry-run`: Show what would be done without making changes
- `--region`: AWS region (default: us-east-1)
- `-v, --verbose`: Enable verbose logging
- `--version`: Show version and exit

### Configuration

Set environment variables for common settings:

```bash
export AWS_SOURCE_ACCOUNT_ID=123456789012
export AWS_DEST_ACCOUNT_ID=987654321098
export AWS_REGION=us-east-1
export DRY_RUN=true
export BATCH_SIZE=10
```

For cross-account access, configure IAM roles:

```bash
export AWS_SOURCE_ROLE_ARN=arn:aws:iam::123456789012:role/BackupMigrationRole
export AWS_DEST_ROLE_ARN=arn:aws:iam::987654321098:role/BackupMigrationRole
```

## Development

### Running Tests

```bash
# Run all tests with coverage
pipenv run pytest tests/ -v

# Run specific test file
pipenv run pytest tests/unit/domain/test_recovery_point.py -v

# Run with coverage report
pipenv run pytest tests/ --cov=src/shuffle_aws_vaults --cov-report=html
```

### Code Quality

```bash
# Format code with black
pipenv run black src/ tests/

# Lint with ruff
pipenv run ruff check src/ tests/

# Type check with mypy
pipenv run mypy src/
```

### Project Structure

Every Python file includes:
- Shebang (`#!/usr/bin/env python3`)
- Module docstring
- `__version__` and `__author__` metadata
- `file_info()` function returning metadata dictionary
- `if __name__ == "__main__": main()` block for standalone execution

## IAM Permissions

The tool requires the following AWS permissions:

**Source Account:**
- `backup:ListBackupVaults`
- `backup:ListRecoveryPointsByBackupVault`
- `backup:DescribeRecoveryPoint`
- `backup:StartCopyJob`
- `backup:DescribeCopyJob`

**Destination Account:**
- `backup:CreateBackupVault`
- `backup:PutBackupVaultAccessPolicy`

## Examples

### Dry Run Before Copying

```bash
# See what would be copied without making changes
shuffle-aws-vaults copy \
  --dry-run \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --verbose
```

### Filtered Migration

```bash
# Create filter configuration
cat > filters.yaml <<EOF
match_all: true
rules:
  - criteria: RESOURCE_TYPE
    value: EBS
    include: true
  - criteria: MIN_SIZE_GB
    value: 10.0
    include: true
  - criteria: STATUS
    value: COMPLETED
    include: true
EOF

# Apply filters and copy
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --config filters.yaml \
  --batch-size 15
```

## Troubleshooting

### Permission Errors

Ensure IAM roles have the required permissions and trust relationships configured for cross-account access.

### Copy Job Failures

Check AWS Backup service limits and ensure destination account has sufficient capacity.

### Timeout Issues

Reduce `--batch-size` for large recovery points or slow networks.

## Contributing

This is a solo development project following trunk-based development:
- Work in small vertical slices
- Keep trunk always releasable
- Tests first, then implementation, then refactor
- No speculative features

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

John Ayers
