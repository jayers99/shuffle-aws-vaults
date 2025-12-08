# shuffle-aws-vaults

Production-ready CLI tool to migrate AWS Backup recovery points between accounts at scale (1M+ recovery points). Features include CSV metadata enrichment, state persistence with resume support, parallel processing, real-time progress tracking, and automatic error handling with retry logic.

## Features

- **📋 List & Discover**: Enumerate backup vaults and recovery points with CSV metadata enrichment
- **🔍 Filter & Select**: Filter recovery points by APMID or custom criteria
- **🚀 Copy at Scale**: Multi-threaded copy (10-50 workers) with 500+ items/hour throughput
- **💾 State Persistence**: Automatic state saving with resume support for long-running operations
- **📊 Progress Tracking**: Real-time progress bars, ETA calculation, and throughput metrics
- **⏱️ Runtime Limits**: Maintenance window compliance with graceful shutdown
- **🔄 Error Handling**: Automatic retry with exponential backoff for transient errors
- **📈 Summary Reports**: JSON summary reports with statistics and failure details
- **🛡️ Production Ready**: Credential refresh, signal handling, comprehensive error logging
- **🏗️ Clean Architecture**: DDD-based design with domain, application, and infrastructure layers

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

## Quick Start

```bash
# Install
pipenv install -e .

# List recovery points with metadata
shuffle-aws-vaults list \
  --source-account 123456789012 \
  --vault production-backups \
  --metadata-csv metadata.csv

# Copy with parallel workers and progress tracking
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --workers 20 \
  --summary-output summary.json

# Resume interrupted copy
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --resume

# Verify migration
shuffle-aws-vaults verify \
  --source-account 123456789012 \
  --dest-account 987654321098
```

## Documentation

📖 **[Complete User Guide](USER_GUIDE.md)** - Comprehensive guide with all features, examples, and troubleshooting

**Key Sections:**
- [Command Reference](USER_GUIDE.md#command-reference) - All commands and options
- [CSV Metadata Format](USER_GUIDE.md#csv-metadata-enrichment) - CSV file format and usage
- [State Management & Resume](USER_GUIDE.md#state-management--resume) - Resuming interrupted operations
- [Progress Tracking](USER_GUIDE.md#progress-tracking) - Real-time progress and summary reports
- [Performance Tuning](USER_GUIDE.md#performance-tuning) - Worker configuration and optimization
- [Error Handling](USER_GUIDE.md#error-handling) - Retry logic and failure recovery
- [Troubleshooting](USER_GUIDE.md#troubleshooting) - Common issues and solutions

## Key Features

### CSV Metadata Enrichment

Enrich recovery points with external metadata from CSV files:

```csv
resourceArn,APMID,Environment,Owner
arn:aws:ec2:us-east-1:123456789012:volume/vol-1,APP001,Production,Platform-Team
arn:aws:rds:us-east-1:123456789012:db:mydb,APP002,Production,Data-Team
```

Filter recovery points by APMID (whitelist or blacklist):

```bash
# Whitelist: Only copy specific APMIDs
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --allowed-apmids APP001,APP002 \
  --metadata-csv metadata.csv

# Blacklist: Copy everything except specific APMIDs
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --excluded-apmids APP999,TEST001 \
  --metadata-csv metadata.csv
```

**Performance:** Optimized for 1M+ rows, loads 100K rows in < 2 seconds

### State Persistence & Resume

Automatic state saving enables resumption after interruptions:

```bash
# Start copy operation
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --workers 20

# Press Ctrl+C to interrupt - state is saved automatically

# Resume from where it left off
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --resume
```

**Features:**
- Graceful shutdown on SIGINT/SIGTERM
- Automatic state file management
- Resume from any interruption point

### Multi-Threaded Copy

Parallel processing with configurable worker count:

```bash
# 10 workers (default) - ~500 items/hour
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --workers 10

# 30 workers - ~1,200 items/hour
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --workers 30
```

### Real-Time Progress

Live progress tracking with ETA:

```
Progress: [████████████████████        ] 75% (750/1000)
  Completed: 700 | Failed: 50 | In Progress: 50
  Rate: 125 items/hour | ETA: 2h 15m
```

### Runtime Limits

Compliance with maintenance windows:

```bash
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --max-runtime-minutes 120 \
  --workers 20
```

Automatically stops accepting new work when limit approached, completes in-progress items, and saves state.

### Summary Reports

Generate JSON reports for audit and analysis:

```bash
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --summary-output /reports/migration-summary.json
```

Includes: completion stats, success rate, throughput, duration, failure details

### Error Handling

**Automatic Retry** - Exponential backoff for transient errors:
- Throttling / Rate limiting
- Service unavailable
- Request timeouts
- Internal errors

**Credential Management** - Automatic refresh for expired tokens:
- ExpiredToken
- InvalidClientTokenId

**Partial Failures** - Continue processing despite individual failures

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

## Performance

**Throughput Benchmarks:**
- Single-threaded: ~50 items/hour
- 10 workers: ~500 items/hour
- 20 workers: ~900 items/hour
- 30 workers: ~1,200 items/hour

**Scale Targets:**
- 10K items: ~2-3 hours (20 workers)
- 100K items: ~20-30 hours (30 workers)
- 1M items: ~200-300 hours (30 workers, use resume mode)

**CSV Performance:**
- 100K rows: < 2 seconds to load
- 1M rows: < 20 seconds to load
- Lookups: < 1ms (O(1) hash table)

## Testing

```bash
# Run all tests
pipenv run pytest

# Run with coverage
pipenv run pytest --cov=src/shuffle_aws_vaults --cov-report=html

# Run specific test file
pipenv run pytest tests/unit/domain/test_recovery_point.py -v
```

**Test Coverage:** 67% overall (216 tests passing)

## Exit Codes

- `0` - Success: All operations completed successfully
- `1` - Error: Errors occurred during execution
- `2` - Incomplete: Interrupted by signal or runtime limit (use --resume)

## Support

- 📖 [User Guide](USER_GUIDE.md) - Complete documentation
- 🐛 [GitHub Issues](https://github.com/jayers99/shuffle-aws-vaults/issues) - Bug reports and feature requests
- 💬 Questions? Open a discussion on GitHub

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

---

**Production Ready** ✓ State Persistence ✓ Error Recovery ✓ Progress Tracking ✓ Performance Optimized
