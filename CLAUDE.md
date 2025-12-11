# shuffle-aws-vaults

CLI tool to migrate AWS Backup recovery points between accounts at scale (1M+ recovery points).

## Architecture

Clean Architecture with DDD layers - no AWS dependencies leak into domain:

```
src/shuffle_aws_vaults/
├── domain/          # Pure business logic (RecoveryPoint, Vault, State, FilterRule)
├── application/     # Use case services (list, copy, filter, verify)
├── infrastructure/  # AWS SDK, CSV parsing, state persistence, logging
└── cli.py           # Entry point (argparse)
```

## Commands

```bash
# Tests
pipenv run pytest                                    # all tests
pipenv run pytest tests/unit/domain/ -v             # domain layer only

# Quality
pipenv run black src/ tests/
pipenv run ruff check src/ tests/
pipenv run mypy src/
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
| State | Persistent migration state enabling --resume |
| FilterRule | Whitelist/blacklist by APMID |
| MigrationResult | Tracks copy job status (pending/in_progress/completed/failed) |

## Testing Notes

- Unit tests mirror src: `tests/unit/{domain,application,infrastructure}/`
- Mock AWS calls with `pytest-mock` - never call real AWS in tests
- Fixtures in `tests/conftest.py`
- Coverage: 67% (216 tests)

## Story Prefix

Use `SAV-N` for branches: `feature/SAV-15-csv-optimization`
