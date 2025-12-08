# Development Backlog - shuffle-aws-vaults

## Project Context

**Scale:** ~1M recovery points across ~12 vaults, 8 resource types
**Runtime:** Hours to days
**Development Approach:** Agile with feature branches
**Story Size:** 3-5 points (deliverable in ~1 day)
**Tools:** Jira for tracking, Bitbucket for feature branches

## Story Backlog (Priority Order)

### Story 1: Basic List Command with Pagination (5 points)
**As an** AWS administrator
**I want to** list all recovery points from a source account with full pagination
**So that** I can see what needs to be migrated

**Acceptance Criteria:**
- `shuffle-aws-vaults list --source-account X` enumerates all recovery points
- Handles AWS pagination automatically (>1000 items)
- Displays: recovery point ARN, vault name, resource type, creation date, size
- Works with all 8 resource types (EBS, RDS, Aurora, S3, EFS, etc.)
- Unit tests for pagination logic
- Integration test with test vault containing 100+ recovery points

**Tasks:**
- [ ] Wire AWSBackupRepository to CLI list command
- [ ] Implement complete pagination in list_recovery_points
- [ ] Add console output formatting (table or JSON)
- [ ] Add unit tests for ListService
- [ ] Test against real AWS test account

**Branch:** `feature/SAV-1-list-command`

---

### Story 2: CSV Metadata Enrichment (4 points)
**As an** AWS administrator
**I want to** enrich recovery points with metadata from a CSV file keyed by resourceArn
**So that** I have APMID and other custom fields for filtering

**Acceptance Criteria:**
- Accepts `--metadata-csv path/to/file.csv` flag
- Joins CSV data to recovery points by resourceArn
- Displays enriched fields (APMID, custom tags) in output
- Handles missing resourceArn in CSV gracefully (log warning, continue)
- Handles malformed CSV gracefully (clear error message)
- Unit tests for CSV parsing and joining logic
- Integration test with sample CSV file

**Tasks:**
- [ ] Add CSVMetadataRepository to infrastructure layer
- [ ] Extend RecoveryPoint domain model with metadata dict
- [ ] Add MetadataEnrichmentService to application layer
- [ ] Update list command to load and join CSV
- [ ] Add error handling for CSV issues
- [ ] Create sample CSV for testing

**Branch:** `feature/SAV-2-csv-enrichment`

---

### Story 3: APMID-Based Filtering (3 points)
**As an** AWS administrator
**I want to** filter recovery points by APMID whitelist
**So that** I only copy recovery points matching approved applications

**Acceptance Criteria:**
- Accepts `--allowed-apmids "A,B,C"` flag
- Excludes recovery points whose APMID is not in whitelist
- Shows count of included vs excluded recovery points
- Handles missing APMID in metadata (excluded by default)
- Unit tests for APMID filter rule
- Integration test with mixed APMID dataset

**Tasks:**
- [ ] Extend FilterCriteria enum with APMID_IN_SET
- [ ] Implement APMIDFilterRule in filter_rule.py
- [ ] Wire to filter command in CLI
- [ ] Add filter summary output
- [ ] Add tests for filter logic

**Branch:** `feature/SAV-3-apmid-filtering`

---

### Story 4: State Persistence Infrastructure (4 points)
**As an** operator
**I want to** persist all progress to disk
**So that** the job can resume if interrupted

**Acceptance Criteria:**
- Creates state file in JSON format (default: `.shuffle-state.json`)
- Persists: inventory snapshot, copy queue, completed items, failed items
- Atomic writes (write to temp file, rename)
- State includes timestamp and schema version
- Unit tests for save/load operations
- Integration test for state file integrity

**Tasks:**
- [ ] Add StateRepository to infrastructure layer
- [ ] Define InventoryState and CopyState domain models
- [ ] Implement atomic save/load operations
- [ ] Add schema versioning
- [ ] Add state validation on load
- [ ] Add tests for state persistence

**Branch:** `feature/SAV-4-state-persistence`

---

### Story 5: Resume Mode with Graceful Shutdown (5 points)
**As an** operator
**I want to** resume from saved state and gracefully shutdown on Ctrl-C
**So that** long-running jobs can be interrupted and resumed safely

**Acceptance Criteria:**
- `--resume` flag loads state and continues from last position (default behavior)
- `--reset` flag ignores existing state and starts fresh
- Ctrl-C triggers graceful shutdown: saves state and exits within 5 seconds
- SIGTERM also triggers graceful shutdown
- Resume skips already-completed items
- Resume validates state schema version
- Integration test: interrupt and resume copy job

**Tasks:**
- [ ] Add --resume/--reset flags to CLI
- [ ] Implement resume logic in copy command
- [ ] Add signal handlers for SIGINT/SIGTERM
- [ ] Coordinate shutdown across operations
- [ ] Save final state before exit
- [ ] Add resume integration test

**Branch:** `feature/SAV-5-resume-and-shutdown`

---

### Story 6: Basic Copy Command (Single-Threaded) (5 points)
**As an** AWS administrator
**I want to** copy recovery points from source to destination account
**So that** I can replicate backups across accounts

**Acceptance Criteria:**
- `copy --source-account X --dest-account Y` copies recovery points
- Single-threaded implementation for simplicity
- Polls copy job status until completion
- Logs progress for each recovery point
- Handles copy job failures gracefully
- Updates state file after each successful copy
- Integration test: copy 10-50 recovery points

**Tasks:**
- [ ] Implement start_copy_job in AWSBackupRepository
- [ ] Implement get_copy_job_status polling
- [ ] Wire copy_service to copy CLI command
- [ ] Add progress logging
- [ ] Integrate with state persistence
- [ ] Test with real AWS accounts

**Branch:** `feature/SAV-6-basic-copy`

---

### Story 7: Vault Replication with Compliance Flags (4 points)
**As an** AWS administrator
**I want to** replicate vault structure and compliance settings to destination
**So that** destination vaults match source vault configurations

**Acceptance Criteria:**
- Creates destination vaults if they don't exist
- Replicates vault compliance flags from source to destination
- Validates compliance settings before copying
- Logs vault creation and configuration actions
- Handles "vault already exists" gracefully
- Unit tests for vault compliance validation
- Integration test with compliance-enabled vaults

**Tasks:**
- [ ] Add create_vault to AWSBackupRepository
- [ ] Extend Vault domain model with compliance flags
- [ ] Add get/set_vault_settings methods
- [ ] Implement vault replication in copy_service
- [ ] Add compliance validation
- [ ] Test with compliance-enabled test vaults

**Branch:** `feature/SAV-7-vault-replication`

---

### Story 8: IAM Permission Pre-Check (3 points)
**As an** AWS administrator
**I want to** validate IAM permissions before starting copy
**So that** I don't waste time if permissions are misconfigured

**Acceptance Criteria:**
- `copy --validate-permissions` runs dry-run permission checks
- Checks source account: List, Describe, StartCopyJob, DescribeCopyJob
- Checks destination account: CreateBackupVault, PutBackupVaultAccessPolicy
- Reports all missing permissions clearly
- Exits with error code if permissions missing
- Runs validation automatically before copy (with --skip-validation to bypass)
- Unit tests for permission validator

**Tasks:**
- [ ] Add PermissionValidator to infrastructure layer
- [ ] Define required permission sets
- [ ] Implement IAM simulation API calls
- [ ] Add clear error reporting
- [ ] Wire to copy command
- [ ] Add tests for validator

**Branch:** `feature/SAV-8-permission-check`

---

### Story 9: Token Lifecycle Management (5 points)
**As an** operator
**I want to** handle expired AWS credentials gracefully
**So that** long-running jobs don't crash when tokens expire

**Acceptance Criteria:**
- Detects ExpiredToken exceptions from boto3
- Destroys AWS clients and reloads credentials from ~/.aws/credentials
- Retries failed operation with fresh credentials
- After 3 consecutive auth failures: pauses and prompts "Press any key to retry"
- Resumes on keypress after operator refreshes token externally
- Logs all credential refresh events
- Unit tests for retry logic
- Integration test simulating token expiration

**Tasks:**
- [ ] Add credential refresh wrapper around boto3 clients
- [ ] Detect ExpiredToken and ExpiredCredentials exceptions
- [ ] Implement client destruction and recreation
- [ ] Add retry logic with exponential backoff
- [ ] Add auth failure counter with operator pause
- [ ] Add keypress wait prompt
- [ ] Add tests for token lifecycle

**Branch:** `feature/SAV-9-token-lifecycle`

---

### Story 10: Multi-Threaded Copy with Safe Concurrency (5 points)
**As an** operator
**I want to** copy recovery points in parallel
**So that** I can process 1M recovery points in reasonable time

**Acceptance Criteria:**
- `--workers N` flag controls parallelism (default: 10)
- Uses ThreadPoolExecutor for parallel copy jobs
- Thread-safe state updates (locks around state file writes)
- No double-processing of recovery points
- Credential refresh pauses all workers, then resumes
- Global lock around credential refresh
- Logs worker activity and throughput
- Integration test: 10 workers copying 100 recovery points

**Tasks:**
- [ ] Add ThreadPoolExecutor to copy_service
- [ ] Implement thread-safe state updates
- [ ] Add --workers flag to CLI
- [ ] Add global credential lock
- [ ] Pause/resume workers during credential refresh
- [ ] Add concurrency tests

**Branch:** `feature/SAV-10-parallel-copy`

---

### Story 11: Real-Time Progress Display (4 points)
**As an** operator
**I want to** see continuous progress updates
**So that** I can monitor long-running copy jobs

**Acceptance Criteria:**
- Console displays: completed/total, current rate (items/hour), ETA, errors
- Updates every 5 seconds without scrolling (same-line refresh)
- Verbose mode (`-v`) shows per-recovery-point details
- Calculates ETA based on rolling average throughput
- Shows time elapsed since start
- Displays final summary on completion
- Integration test verifies progress output

**Tasks:**
- [ ] Add ProgressTracker to infrastructure layer
- [ ] Calculate rolling average throughput
- [ ] Implement console refresh (ANSI codes or library)
- [ ] Add ETA calculation
- [ ] Wire to copy command
- [ ] Add verbose output mode
- [ ] Test progress display

**Branch:** `feature/SAV-11-progress-display`

---

### Story 12: Runtime Limits and Change Windows (3 points)
**As an** operator
**I want to** set maximum runtime limits
**So that** copy jobs respect change window constraints

**Acceptance Criteria:**
- `--max-runtime-minutes N` sets time limit
- Gracefully exits when limit reached (saves state first)
- Logs time remaining periodically
- Exit code indicates incomplete (exit 2) vs success (exit 0)
- Progress display shows time remaining in window
- Integration test with short runtime limit

**Tasks:**
- [ ] Add --max-runtime-minutes flag
- [ ] Track elapsed time since start
- [ ] Trigger graceful shutdown at limit
- [ ] Save state before exit
- [ ] Add time remaining to progress display
- [ ] Add tests for runtime limits

**Branch:** `feature/SAV-12-runtime-limits`

---

### Story 13: Summary Reports and Completion Metrics (3 points)
**As an** operator
**I want to** see a final summary report
**So that** I know what succeeded, failed, and was skipped

**Acceptance Criteria:**
- Final summary shows: total items, succeeded, failed, skipped, duration
- Lists all failures with recovery point ARN and error message
- Exports summary to JSON file (for automation/reporting)
- Calculates success rate percentage
- Estimates items per hour throughput
- Displays summary on both completion and interruption

**Tasks:**
- [ ] Add summary generation to copy_service
- [ ] Include success/failure breakdown
- [ ] Export to JSON file
- [ ] Display summary on exit
- [ ] Add tests for summary generation

**Branch:** `feature/SAV-13-summary-reports`

---

### Story 14: Production Error Handling (4 points)
**As an** operator
**I want to** graceful handling of production edge cases
**So that** the tool is reliable at 1M scale

**Acceptance Criteria:**
- Missing metadata (APMID) logs warning and excludes recovery point
- Vault already exists in destination: continues without error
- Transient AWS errors (throttling, timeouts): retry with exponential backoff
- Partial batch failures: continue processing remaining items
- All errors logged with context (recovery point ARN, operation)
- Never crashes - always saves state on unexpected errors
- Integration test covering error scenarios

**Tasks:**
- [ ] Add comprehensive exception handling
- [ ] Implement retry logic for transient errors
- [ ] Handle missing metadata gracefully
- [ ] Handle vault exists errors
- [ ] Add error logging with context
- [ ] Add tests for error scenarios

**Branch:** `feature/SAV-14-error-handling`

---

### Story 15: CSV Parsing Optimization (3 points)
**As an** operator
**I want to** fast CSV parsing for large metadata files
**So that** enrichment doesn't bottleneck performance

**Acceptance Criteria:**
- Lazy loading: load CSV only when needed
- Index CSV by resourceArn for O(1) lookups
- Stream parsing for large files (don't load entire CSV into memory)
- Progress indicator for CSV loading
- Handles CSV files with 1M+ rows
- Benchmark: <5 seconds to load 1M row CSV

**Tasks:**
- [ ] Implement lazy loading for CSV
- [ ] Add resourceArn index (dict)
- [ ] Use streaming CSV parser
- [ ] Add progress indicator
- [ ] Benchmark CSV loading performance
- [ ] Optimize memory usage

**Branch:** `feature/SAV-15-csv-optimization`

---

## Development Workflow

### Git/Bitbucket Feature Branch Flow

1. **Create Jira Story** - Story created in backlog with acceptance criteria
2. **Create Feature Branch** - `git checkout -b feature/SAV-N-description` from `main`
3. **Implement & Test** - Write code, tests, commit frequently
4. **Pull Request** - Create PR in Bitbucket when story complete
5. **Code Review** - Review and address feedback
6. **Merge to Main** - Squash merge when approved
7. **Move Story to Done** - Update Jira

### Commit Guidelines

- Commit frequently within feature branch (5-10 commits per story)
- Descriptive commit messages following convention:
  - `feat: add CSV metadata repository`
  - `test: add integration test for list command`
  - `fix: handle missing resourceArn in CSV`
  - `refactor: extract pagination logic`
  - `docs: update README with CSV format`
- Always include tests with feature commits
- Keep each commit focused and atomic
- Use co-author tag for Claude Code commits

### Branch Naming Convention

- `feature/SAV-N-short-description` - New features
- `bugfix/SAV-N-short-description` - Bug fixes
- `hotfix/SAV-N-short-description` - Production hotfixes

## Test Environment Strategy (80/20 Approach)

**Setup Tasks:**
- Create test AWS accounts (source + destination)
- Create 3-5 test vaults with compliance flags
- Generate 100-500 dummy recovery points (all 8 resource types)
- Create sample CSV metadata file with APMID data
- Set up IAM roles with required permissions

**80/20 Principle:**
- Avoid full production scale (1M recovery points)
- Focus on representative shape and behavior
- Cover all 8 resource types with minimal counts
- Test critical edge cases: missing metadata, auth failures, interruptions

**Test Data Generation:**
- Script to create dummy EBS volumes, RDS databases, etc.
- Script to run backups and create recovery points
- CSV generator with realistic APMID values
- Test vaults with different compliance settings

## Definition of Done

Each story is considered done when:
- [ ] Feature code implemented following DDD architecture
- [ ] Unit tests written and passing (>80% coverage)
- [ ] Integration tests written for user-facing features
- [ ] Manual testing in test environment completed
- [ ] Code reviewed and approved in Bitbucket
- [ ] Documentation updated (README, docstrings)
- [ ] Merged to main branch
- [ ] Jira story moved to Done

## Story Sizing Reference

- **3 points:** Simple feature, clear implementation, minimal integration
- **4 points:** Moderate complexity, some integration points, standard testing
- **5 points:** Complex feature, multiple integration points, extensive testing

## Success Metrics

- **Correctness:** All test recovery points copied with correct metadata
- **Resumability:** Can resume from any interruption (Ctrl-C test passes)
- **Performance:** >500 recovery points/hour with 10 workers
- **Reliability:** Handles token expiration and auth failures gracefully
- **Observability:** Real-time progress with ETA and error diagnostics

## Critical Path (Must Have)

1. Stories 1-3: List + CSV + Filtering (foundation)
2. Stories 4-5: State + Resume (long-running reliability)
3. Stories 6-8: Copy + Vault + Permissions (core migration)
4. Story 9: Token Lifecycle (production requirement)
5. Story 10: Parallelism (scale requirement)
6. Stories 11-12: Progress + Runtime (operator UX)

## Nice-to-Haves (Stretch Goals)

- Story 13: Summary Reports
- Story 14: Advanced Error Handling
- Story 15: CSV Optimization
- Additional: Batch copy job submission
- Additional: Performance profiling and tuning

## Notes

- Work on one story at a time
- Commit to feature branch frequently
- Keep main branch always releasable
- TDD where possible (tests first)
- Security: never log credentials or sensitive metadata
- Focus on getting stories to Done vs starting new ones
