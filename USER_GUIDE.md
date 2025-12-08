# shuffle-aws-vaults User Guide

Comprehensive guide for migrating AWS Backup recovery points between accounts at scale.

## Table of Contents

- [Quick Start](#quick-start)
- [Command Reference](#command-reference)
- [CSV Metadata Enrichment](#csv-metadata-enrichment)
- [State Management & Resume](#state-management--resume)
- [Progress Tracking](#progress-tracking)
- [Performance Tuning](#performance-tuning)
- [Error Handling](#error-handling)
- [Advanced Use Cases](#advanced-use-cases)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/jayers99/shuffle-aws-vaults.git
cd shuffle-aws-vaults

# Install Python 3.12.10
pyenv install 3.12.10

# Install dependencies
pipenv install --dev

# Install package
pipenv install -e .
```

### Basic Workflow

```bash
# 1. List recovery points in source account
shuffle-aws-vaults list \
  --source-account 123456789012 \
  --region us-east-1 \
  --vault my-backup-vault

# 2. Copy to destination account
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault my-backup-vault \
  --region us-east-1 \
  --workers 10

# 3. Verify migration
shuffle-aws-vaults verify \
  --source-account 123456789012 \
  --dest-account 987654321098
```

---

## Command Reference

### `list` - List Recovery Points

List backup vaults and recovery points in source account.

**Usage:**
```bash
shuffle-aws-vaults list \
  --source-account SOURCE_ACCOUNT \
  [--region REGION] \
  [--vault VAULT_NAME] \
  [--metadata-csv CSV_FILE] \
  [--output json|table] \
  [--dry-run] \
  [-v]
```

**Options:**
- `--source-account` (required): Source AWS account ID
- `--region`: AWS region (default: us-east-1)
- `--vault`: Specific vault name (optional, lists all if omitted)
- `--metadata-csv`: Path to CSV metadata file for enrichment
- `--output`: Output format - `table` (default) or `json`
- `--dry-run`: Show what would be queried without making API calls
- `-v, --verbose`: Enable verbose logging

**Examples:**

```bash
# List all vaults in account
shuffle-aws-vaults list --source-account 123456789012

# List specific vault with metadata
shuffle-aws-vaults list \
  --source-account 123456789012 \
  --vault production-backups \
  --metadata-csv metadata.csv

# JSON output for scripting
shuffle-aws-vaults list \
  --source-account 123456789012 \
  --output json > recovery-points.json
```

---

### `filter` - Filter Recovery Points

Apply filter rules to select recovery points for migration.

**Usage:**
```bash
shuffle-aws-vaults filter \
  --source-account SOURCE_ACCOUNT \
  --vault VAULT_NAME \
  [--allowed-apmids APMID1,APMID2,...] \
  [--excluded-apmids APMID1,APMID2,...] \
  [--metadata-csv CSV_FILE] \
  [--region REGION] \
  [--output json|table] \
  [-v]
```

**Options:**
- `--source-account` (required): Source AWS account ID
- `--vault` (required): Vault name to filter
- `--allowed-apmids`: Comma-separated list of allowed APMID values (whitelist)
- `--excluded-apmids`: Comma-separated list of excluded APMID values (blacklist)
- `--metadata-csv`: Path to CSV metadata file (required if using APMID filters)
- `--region`: AWS region (default: us-east-1)
- `--output`: Output format - `table` (default) or `json`
- `-v, --verbose`: Enable verbose logging

**Examples:**

```bash
# Filter by allowed APMIDs (whitelist)
shuffle-aws-vaults filter \
  --source-account 123456789012 \
  --vault production-backups \
  --allowed-apmids APP001,APP002,APP003 \
  --metadata-csv metadata.csv

# Filter by excluded APMIDs (blacklist)
shuffle-aws-vaults filter \
  --source-account 123456789012 \
  --vault production-backups \
  --excluded-apmids APP999,TEST001 \
  --metadata-csv metadata.csv

# Combine both: allow specific APMIDs but exclude certain ones
shuffle-aws-vaults filter \
  --source-account 123456789012 \
  --vault production-backups \
  --allowed-apmids APP001,APP002,APP003 \
  --excluded-apmids APP002 \
  --metadata-csv metadata.csv

# View filtered results as JSON
shuffle-aws-vaults filter \
  --source-account 123456789012 \
  --vault production-backups \
  --allowed-apmids APP001 \
  --metadata-csv metadata.csv \
  --output json
```

---

### `copy` - Copy Recovery Points

Copy recovery points from source to destination account with progress tracking and resume support.

**Usage:**
```bash
shuffle-aws-vaults copy \
  --source-account SOURCE_ACCOUNT \
  --dest-account DEST_ACCOUNT \
  --vault VAULT_NAME \
  [--region REGION] \
  [--workers NUM_WORKERS] \
  [--poll-interval SECONDS] \
  [--max-runtime-minutes MINUTES] \
  [--allowed-apmids APMID1,APMID2,...] \
  [--excluded-apmids APMID1,APMID2,...] \
  [--metadata-csv CSV_FILE] \
  [--state-file STATE_FILE] \
  [--resume] \
  [--reset] \
  [--summary-output SUMMARY_FILE] \
  [--dry-run] \
  [-v]
```

**Options:**
- `--source-account` (required): Source AWS account ID
- `--dest-account` (required): Destination AWS account ID
- `--vault` (required): Vault name to copy
- `--region`: AWS region (default: us-east-1)
- `--workers`: Number of parallel workers (default: 10, range: 1-50)
- `--poll-interval`: Seconds between status checks (default: 30)
- `--max-runtime-minutes`: Maximum runtime in minutes (optional)
- `--allowed-apmids`: Filter by comma-separated allowed APMID values (whitelist)
- `--excluded-apmids`: Filter by comma-separated excluded APMID values (blacklist)
- `--metadata-csv`: Path to CSV metadata file (required if using APMID filters)
- `--state-file`: Custom state file path (default: auto-generated)
- `--resume`: Resume from previous run
- `--reset`: Reset state and start fresh
- `--summary-output`: Path to save JSON summary report
- `--dry-run`: Show what would be copied without executing
- `-v, --verbose`: Enable verbose logging

**Examples:**

```bash
# Basic copy with 10 workers
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --workers 10

# Copy with allowed APMID filtering (whitelist)
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --allowed-apmids APP001,APP002 \
  --metadata-csv metadata.csv \
  --workers 15

# Copy with excluded APMID filtering (blacklist)
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --excluded-apmids APP999,TEST001 \
  --metadata-csv metadata.csv \
  --workers 15

# Copy with runtime limit (2 hour maintenance window)
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --max-runtime-minutes 120 \
  --workers 20

# Resume interrupted copy
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --resume \
  --workers 10

# Save summary report
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --summary-output /tmp/migration-summary.json \
  --workers 10
```

---

### `verify` - Verify Migration

Verify that recovery points were successfully copied to destination account.

**Usage:**
```bash
shuffle-aws-vaults verify \
  --source-account SOURCE_ACCOUNT \
  --dest-account DEST_ACCOUNT \
  [--region REGION] \
  [-v]
```

**Options:**
- `--source-account` (required): Source AWS account ID
- `--dest-account` (required): Destination AWS account ID
- `--region`: AWS region (default: us-east-1)
- `-v, --verbose`: Enable verbose logging

**Examples:**

```bash
# Verify migration
shuffle-aws-vaults verify \
  --source-account 123456789012 \
  --dest-account 987654321098

# Verbose verification with details
shuffle-aws-vaults verify \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --verbose
```

---

## CSV Metadata Enrichment

### CSV Format

The CSV metadata file enriches recovery points with additional metadata for filtering and tracking.

**Required Column:**
- `resourceArn`: AWS resource ARN (must match recovery point resource ARN)

**Optional Columns:**
- `APMID`: Application ID for filtering
- `Environment`: Environment name (e.g., Production, Development)
- `Owner`: Team or owner name
- `CostCenter`: Cost center code
- Any other custom metadata fields

**Example CSV:**

```csv
resourceArn,APMID,Environment,Owner,CostCenter
arn:aws:ec2:us-east-1:123456789012:volume/vol-abc123,APP001,Production,Platform-Team,CC-1234
arn:aws:rds:us-east-1:123456789012:db:mydb,APP002,Production,Data-Team,CC-5678
arn:aws:dynamodb:us-east-1:123456789012:table/MyTable,APP003,Development,Dev-Team,CC-9012
arn:aws:efs:us-east-1:123456789012:file-system/fs-xyz789,APP001,Production,Platform-Team,CC-1234
```

### CSV File Requirements

- **Encoding**: UTF-8
- **Size**: Optimized for 1M+ rows
- **Loading**: Lazy-loaded on first use, cached in memory
- **Progress**: Automatic progress logging every 10,000 rows
- **Performance**: 100K rows load in < 2 seconds

### Using CSV Metadata

```bash
# List with metadata enrichment
shuffle-aws-vaults list \
  --source-account 123456789012 \
  --vault production-backups \
  --metadata-csv /path/to/metadata.csv

# Filter by APMID using metadata
shuffle-aws-vaults filter \
  --source-account 123456789012 \
  --vault production-backups \
  --allowed-apmids APP001,APP002 \
  --metadata-csv /path/to/metadata.csv

# Copy with metadata filtering
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --allowed-apmids APP001 \
  --metadata-csv /path/to/metadata.csv
```

### Missing Metadata

If a recovery point's resourceArn is not found in the CSV:
- A warning is logged
- The recovery point is excluded from filtered results
- The operation continues with remaining recovery points

---

## State Management & Resume

### State Persistence

Copy operations automatically save state to enable resumption after interruptions.

**State File Location:**
- Default: `~/.shuffle-aws-vaults/state_{source_account}_{vault}_{timestamp}.json`
- Custom: Specify with `--state-file` option

**State Contents:**
- Recovery points being processed
- Copy job IDs and statuses
- Completion tracking
- Timestamp and metadata

### Graceful Shutdown

The tool handles interruptions gracefully:

**Signals Handled:**
- `SIGINT` (Ctrl+C): Graceful shutdown
- `SIGTERM`: Graceful shutdown

**Shutdown Behavior:**
1. Catches interrupt signal
2. Completes current copy operations
3. Saves state to disk
4. Exits with code 2 (incomplete)

### Resume Mode

Resume an interrupted copy operation:

```bash
# Resume from previous state
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --resume

# Resume with custom state file
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --state-file /path/to/state.json \
  --resume
```

**Resume Behavior:**
- Loads previous state
- Skips completed copy operations
- Resumes in-progress operations
- Processes any pending items

### Reset State

Start fresh, ignoring previous state:

```bash
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --reset
```

### State File Conflicts

If both `--resume` and `--reset` are specified:
- Error: Cannot use both flags together
- Choose one or the other

---

## Progress Tracking

### Real-Time Progress Display

The copy command shows real-time progress:

```
Starting copy operation...
Progress: [████████████████████████        ] 75% (750/1000)
  Completed: 700 | Failed: 50 | In Progress: 50
  Rate: 125 items/hour | ETA: 2h 15m
```

**Progress Information:**
- Progress bar with percentage
- Items completed, failed, in progress
- Processing rate (items/hour)
- Estimated time to completion (ETA)

### Progress Updates

- Updates every 5 seconds
- Shows worker thread activity
- Displays current copy operation details
- Logs milestone progress (every 100 items)

### Summary Report

Generate a JSON summary report of the copy operation:

```bash
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --summary-output /tmp/summary.json
```

**Summary Report Contents:**

```json
{
  "total_items": 1000,
  "completed": 950,
  "failed": 30,
  "skipped": 20,
  "in_progress": 0,
  "duration_seconds": 7200.5,
  "duration_formatted": "2h 0m",
  "start_time": "2025-12-08T10:00:00+00:00",
  "end_time": "2025-12-08T12:00:00+00:00",
  "success_rate": 95.0,
  "throughput_per_hour": 475.0,
  "failures": [
    {
      "recovery_point_arn": "arn:aws:backup:...",
      "error_message": "Access denied",
      "timestamp": "2025-12-08T11:30:00+00:00"
    }
  ]
}
```

**Use Cases:**
- Automation reporting
- Audit trails
- Performance analysis
- Failure investigation

---

## Performance Tuning

### Worker Threads

Control parallelism with the `--workers` option:

```bash
# Conservative (10 workers)
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --workers 10

# Aggressive (30 workers)
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --workers 30
```

**Recommendations:**
- **Start with 10 workers**: Good balance for most use cases
- **Increase to 20-30**: For large migrations (1M+ items)
- **Decrease to 5**: If hitting rate limits
- **Max 50 workers**: Hard limit to prevent overwhelming AWS APIs

### Poll Interval

Control how frequently copy job status is checked:

```bash
# Default: 30 seconds
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --poll-interval 30

# Aggressive: 10 seconds (faster completion detection)
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --poll-interval 10

# Conservative: 60 seconds (lower API calls)
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --poll-interval 60
```

**Trade-offs:**
- **Shorter interval**: Faster completion detection, more API calls
- **Longer interval**: Fewer API calls, slower to detect completion

### Runtime Limits

Set maximum runtime for maintenance windows:

```bash
# 2 hour maintenance window
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --max-runtime-minutes 120 \
  --workers 20
```

**Behavior:**
- Monitors elapsed time
- Gracefully stops accepting new work when limit approaches
- Completes in-progress operations
- Saves state for resumption
- Exits with code 2 (incomplete)

**Use Cases:**
- Change window compliance
- Cost control
- Resource scheduling

### Performance Expectations

**Throughput:**
- **Single-threaded**: ~50 items/hour
- **10 workers**: ~500 items/hour
- **20 workers**: ~900 items/hour
- **30 workers**: ~1,200 items/hour

**Scaling:**
- **10K items**: ~2-3 hours with 20 workers
- **100K items**: ~20-30 hours with 30 workers
- **1M items**: ~200-300 hours (8-12 days) with 30 workers

**Optimization Tips:**
1. Use maximum workers your AWS limits allow
2. Run during off-peak hours
3. Use resume mode for long migrations
4. Monitor CloudWatch for throttling
5. Request AWS service limit increases if needed

---

## Error Handling

### Retry Logic

Automatic retry with exponential backoff for transient errors:

**Transient Errors (Auto-Retry):**
- `Throttling` / `ThrottlingException`
- `TooManyRequestsException`
- `RequestLimitExceeded`
- `ServiceUnavailable`
- `InternalError` / `InternalFailure`
- `RequestTimeout` / `RequestTimeoutException`

**Retry Configuration:**
- Max attempts: 3
- Initial delay: 1 second
- Exponential backoff: 2x multiplier
- Max delay: 60 seconds

**Example Retry Sequence:**
1. First failure: Wait 1 second, retry
2. Second failure: Wait 2 seconds, retry
3. Third failure: Wait 4 seconds, retry
4. Fourth failure: Give up, log error

### Credential Management

Automatic credential refresh for expired tokens:

**Credential Errors (Auto-Refresh):**
- `ExpiredToken` / `ExpiredTokenException`
- `InvalidClientTokenId`
- `UnrecognizedClientException`

**Refresh Behavior:**
1. Detects credential error
2. Clears cached sessions
3. Retries with fresh credentials
4. After 3 consecutive failures: Prompts user to refresh externally

### Error Logging

All errors are logged with full context:

```
ERROR: Failed to copy recovery point arn:aws:backup:us-east-1:123456789012:recovery-point:abc123
  Error: Access denied (arn:aws:iam::123456789012:role/BackupRole)
  Stack trace: ...
```

**Logged Information:**
- Recovery point ARN
- Error message
- AWS error code
- Timestamp
- Full stack trace

### Partial Failures

Copy operations continue despite individual failures:

```
Total: 1000 items
  Completed: 950
  Failed: 50
  Success Rate: 95%
```

**Failure Handling:**
1. Individual item fails
2. Error logged with context
3. Operation continues with next item
4. Failed items included in summary report
5. State saved includes failure information

### Exit Codes

```bash
# Exit code 0: Success
shuffle-aws-vaults copy ... && echo "Success"

# Exit code 1: Errors occurred
shuffle-aws-vaults copy ... || echo "Errors"

# Exit code 2: Incomplete (interrupted or runtime limit)
shuffle-aws-vaults copy --max-runtime-minutes 60 ...
echo $?  # 2 if runtime limit reached
```

**Exit Codes:**
- `0`: All operations completed successfully
- `1`: Errors occurred during execution
- `2`: Incomplete (interrupted by signal or runtime limit)

---

## Advanced Use Cases

### Large-Scale Migration (1M+ Items)

Strategy for migrating 1M+ recovery points:

```bash
# Step 1: Initial run with runtime limit
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --workers 30 \
  --max-runtime-minutes 240 \
  --state-file /persistent/state.json \
  --summary-output /persistent/summary-1.json

# Step 2: Resume after maintenance window
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --workers 30 \
  --max-runtime-minutes 240 \
  --state-file /persistent/state.json \
  --resume \
  --summary-output /persistent/summary-2.json

# Step 3: Repeat until complete
# Monitor progress in summary reports
```

### Multi-Vault Migration

Migrate multiple vaults sequentially:

```bash
#!/bin/bash
VAULTS=("vault-1" "vault-2" "vault-3" "vault-4")

for vault in "${VAULTS[@]}"; do
  echo "Migrating vault: $vault"

  shuffle-aws-vaults copy \
    --source-account 123456789012 \
    --dest-account 987654321098 \
    --vault "$vault" \
    --workers 20 \
    --summary-output "/reports/${vault}-summary.json"

  if [ $? -eq 0 ]; then
    echo "✓ $vault completed successfully"
  else
    echo "✗ $vault failed or incomplete"
  fi
done
```

### Filtered Migration with CSV

Migrate only specific applications:

```bash
# Create CSV with metadata
cat > metadata.csv <<EOF
resourceArn,APMID,Environment
arn:aws:ec2:us-east-1:123456789012:volume/vol-1,APP001,Production
arn:aws:rds:us-east-1:123456789012:db:db-1,APP001,Production
arn:aws:ec2:us-east-1:123456789012:volume/vol-2,APP002,Development
arn:aws:rds:us-east-1:123456789012:db:db-2,APP002,Development
EOF

# Migrate only APP001 (Production)
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --allowed-apmids APP001 \
  --metadata-csv metadata.csv \
  --workers 15 \
  --summary-output app001-migration.json
```

### Dry-Run Validation

Validate configuration before executing:

```bash
# Dry-run to see what would be copied
shuffle-aws-vaults copy \
  --dry-run \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --allowed-apmids APP001,APP002 \
  --metadata-csv metadata.csv \
  --verbose

# Review output, then execute
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --allowed-apmids APP001,APP002 \
  --metadata-csv metadata.csv \
  --workers 20
```

### Monitoring and Alerting

Monitor copy operations with summary reports:

```bash
#!/bin/bash
# Run copy operation
shuffle-aws-vaults copy \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups \
  --workers 20 \
  --summary-output /tmp/summary.json

# Parse summary report
SUCCESS_RATE=$(jq -r '.success_rate' /tmp/summary.json)
FAILED=$(jq -r '.failed' /tmp/summary.json)

# Alert on low success rate
if (( $(echo "$SUCCESS_RATE < 95" | bc -l) )); then
  echo "WARNING: Success rate below 95%: $SUCCESS_RATE%"
  echo "Failed items: $FAILED"
  # Send alert to monitoring system
fi

# Alert on high failure count
if [ "$FAILED" -gt 100 ]; then
  echo "ERROR: More than 100 failures detected"
  # Send critical alert
fi
```

---

## Troubleshooting

### Permission Errors

**Symptom:**
```
ERROR: Access denied when listing recovery points
ERROR: Failed to create vault: Access denied
```

**Solution:**

1. Verify IAM permissions:
```bash
# Source account needs:
# - backup:ListBackupVaults
# - backup:ListRecoveryPointsByBackupVault
# - backup:DescribeRecoveryPoint
# - backup:StartCopyJob
# - backup:DescribeCopyJob

# Destination account needs:
# - backup:CreateBackupVault
# - backup:PutBackupVaultAccessPolicy
```

2. Check IAM role trust relationships for cross-account access

3. Verify AWS credentials are configured:
```bash
aws sts get-caller-identity
```

### Rate Limiting / Throttling

**Symptom:**
```
WARNING: Transient error: Throttling (attempt 1/3)
WARNING: Transient error: TooManyRequestsException (attempt 2/3)
```

**Solution:**

1. Reduce worker count:
```bash
shuffle-aws-vaults copy \
  --workers 5 \  # Reduced from 20
  ...
```

2. Increase poll interval:
```bash
shuffle-aws-vaults copy \
  --poll-interval 60 \  # Increased from 30
  ...
```

3. Request AWS service limit increase

### Credential Expiration

**Symptom:**
```
WARNING: Credential error detected: ExpiredToken
INFO: Refreshing credentials and retrying...
```

**Solution:**

1. For temporary credentials: Automatic refresh (no action needed)

2. For long-running operations: Use IAM roles or refresh credentials externally

3. If prompted: Refresh credentials and press Enter

### CSV Loading Errors

**Symptom:**
```
ERROR: CSV file missing 'resourceArn' column
ERROR: CSV file not found: /path/to/metadata.csv
```

**Solution:**

1. Verify CSV file exists and path is correct

2. Check CSV has required 'resourceArn' column:
```csv
resourceArn,APMID
arn:aws:ec2:...,APP001
```

3. Verify CSV encoding is UTF-8

4. Check file permissions

### Copy Job Failures

**Symptom:**
```
ERROR: Copy job failed: InvalidParameterValueException
ERROR: Copy job failed: ResourceNotFoundException
```

**Solution:**

1. Verify source recovery point exists and is COMPLETED

2. Check destination vault exists and has correct permissions

3. Verify resource type is supported for cross-account copy

4. Check AWS Backup service limits in destination account

### State File Corruption

**Symptom:**
```
ERROR: Failed to load state file: Invalid JSON
ERROR: State file version mismatch
```

**Solution:**

1. Start fresh with `--reset`:
```bash
shuffle-aws-vaults copy --reset ...
```

2. Use a new state file:
```bash
shuffle-aws-vaults copy \
  --state-file /tmp/new-state.json \
  ...
```

3. Manually inspect and fix JSON (advanced):
```bash
cat ~/.shuffle-aws-vaults/state_*.json | jq .
```

### Memory Issues

**Symptom:**
```
WARNING: System memory usage high
Process killed (OOM)
```

**Solution:**

1. Reduce worker count:
```bash
shuffle-aws-vaults copy --workers 5 ...
```

2. Process vaults separately instead of all at once

3. Increase system memory or use larger instance

### Incomplete Migration

**Symptom:**
```
Exit code: 2
WARNING: Runtime limit reached, stopping gracefully
```

**Solution:**

1. Resume the operation:
```bash
shuffle-aws-vaults copy --resume ...
```

2. Increase runtime limit:
```bash
shuffle-aws-vaults copy \
  --max-runtime-minutes 480 \  # 8 hours
  ...
```

3. Run without runtime limit (for completion):
```bash
shuffle-aws-vaults copy ...  # No --max-runtime-minutes
```

### Network Timeouts

**Symptom:**
```
WARNING: Transient error: RequestTimeout (attempt 1/3)
ERROR: Failed after 3 transient error retries
```

**Solution:**

1. Check network connectivity to AWS

2. Increase poll interval to reduce API call frequency

3. Reduce worker count to lower concurrent connections

4. Check for VPC endpoint or proxy issues

---

## Getting Help

### Verbose Logging

Enable detailed logging for troubleshooting:

```bash
shuffle-aws-vaults copy \
  --verbose \
  --source-account 123456789012 \
  --dest-account 987654321098 \
  --vault production-backups
```

### Log Files

Logs are written to:
- Console: `INFO` level and above
- With `--verbose`: `DEBUG` level (includes API calls, retry attempts)

### Support

- **GitHub Issues**: https://github.com/jayers99/shuffle-aws-vaults/issues
- **Documentation**: README.md, USER_GUIDE.md
- **Source Code**: https://github.com/jayers99/shuffle-aws-vaults

---

## Best Practices

### Before Migration

1. ✓ Test with small vault first (< 100 items)
2. ✓ Verify IAM permissions in both accounts
3. ✓ Validate CSV metadata format
4. ✓ Run with `--dry-run` to preview
5. ✓ Check AWS Backup service limits
6. ✓ Plan maintenance windows for large migrations

### During Migration

1. ✓ Monitor progress and success rate
2. ✓ Check CloudWatch for throttling
3. ✓ Save summary reports for audit trail
4. ✓ Use state files for long-running operations
5. ✓ Be prepared to resume if interrupted

### After Migration

1. ✓ Run `verify` command to confirm completion
2. ✓ Review summary report for failures
3. ✓ Investigate and retry failed items
4. ✓ Archive state files and summary reports
5. ✓ Document any issues or lessons learned

---

## Appendix

### Supported Resource Types

AWS Backup supports cross-account copy for:
- Amazon EBS volumes
- Amazon RDS databases
- Amazon DynamoDB tables
- Amazon EFS file systems
- Amazon FSx file systems
- Amazon EC2 instances
- Amazon S3 buckets
- Amazon Aurora clusters

### AWS Service Limits

Be aware of these AWS limits:
- **Concurrent copy jobs**: Varies by region (typically 100-1000)
- **API rate limits**: Varies by operation
- **Recovery point size**: Maximum 16 TB per copy

### Performance Benchmarks

Based on testing with production-scale data:
- **CSV Loading**: 100K rows in < 2 seconds
- **Metadata Lookup**: < 1ms per lookup (O(1))
- **Copy Throughput**: ~500 items/hour with 10 workers
- **State Persistence**: < 100ms to save state
- **Resume Overhead**: < 5 seconds to load and resume

---

Last Updated: 2025-12-08
