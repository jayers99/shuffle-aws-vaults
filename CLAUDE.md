# shuffle-aws-vaults

CLI tool to migrate AWS Backup recovery points between accounts at scale (1M+ recovery points).

**Python 3.12+ required** | See [COPILOT.md](COPILOT.md) for detailed coding standards

## Architecture

Clean Architecture with DDD layers - no AWS dependencies leak into domain:

```
src/shuffle_aws_vaults/
├── domain/          # Pure business logic (no I/O, no AWS)
├── application/     # Use case services (orchestration)
├── infrastructure/  # AWS SDK, state persistence, retry, signals
└── cli.py           # Entry point (argparse) - delegates to services
```

## CLI Usage

```bash
shuffle-aws-vaults list --source-account 111111111111 --vault my-vault
shuffle-aws-vaults copy --source-account 111 --dest-account 222 --vault my-vault --workers 10
shuffle-aws-vaults filter --vault my-vault --allowed-apmids APM001,APM002
shuffle-aws-vaults verify --source-account 111 --dest-account 222
```

Global flags: `--dry-run`, `--region`, `-v/--verbose`, `--output [text|json]`

## Dev Commands

```bash
pipenv install --dev                                 # setup
pipenv run pytest                                    # all tests (229)
pipenv run pytest tests/unit/domain/ -v             # domain layer only
pipenv run black src/ tests/                         # format
pipenv run ruff check src/ tests/                    # lint
pipenv run mypy src/                                 # type check
```

## File Template

Every Python file must include:
- `#!/usr/bin/env python3`
- Module docstring
- `__version__` and `__author__`
- `file_info()` → dict
- `if __name__ == "__main__": main()`

## Domain Concepts

| Concept | Description |
|---------|-------------|
| RecoveryPoint | AWS Backup recovery point + optional CSV metadata (APMID) |
| Vault | AWS Backup vault containing recovery points |
| State | Persistent migration state enabling `--resume` |
| FilterRule | Whitelist/blacklist by APMID |
| MigrationResult | Tracks copy job status (pending/in_progress/completed/failed) |

## Key Infrastructure Patterns

| Pattern | Module | Purpose |
|---------|--------|---------|
| Retry | `retry.py` | Exponential backoff with `@with_retry` decorator |
| Signals | `signal_handler.py` | Graceful SIGINT/SIGTERM shutdown |
| State | `state_repository.py` | Atomic JSON persistence (temp + rename) |
| Permissions | `permission_validator.py` | Pre-flight IAM validation |
| Progress | `progress_tracker.py` | Real-time ETA and throughput |

## Testing

- Unit tests mirror src: `tests/unit/{domain,application,infrastructure}/`
- Mock AWS calls with `pytest-mock` - never call real AWS in tests
- Fixtures in `tests/conftest.py`
- No CI/CD pipeline yet - run tests locally before commits

## Security

- Validate IAM permissions before operations (`--skip-validation` to bypass)
- Never log credentials or sensitive identifiers
- Use `credential_manager.py` for cross-account assume-role
- Respect AWS rate limits via retry decorator

## Branch Naming

Use `SAV-N` prefix: `feature/SAV-15-csv-optimization`
