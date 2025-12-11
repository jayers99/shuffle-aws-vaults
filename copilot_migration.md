# GitHub Copilot Instructions

## Session Startup

Read these files in order before starting any work:

1. `shuffle_aws_vaults_brainstorm.md` - Domain requirements
2. `ROADMAP.md` - Story backlog with acceptance criteria
3. `CLAUDE.md` - Architecture and coding conventions
4. `README.md` - Project overview

## Project Overview

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

## Development Workflow

### TDD (Always)
1. **Red** - Write failing test first
2. **Green** - Write minimal code to pass
3. **Refactor** - Clean up while tests stay green

### Branch Naming
- `feature/SAV-N-short-description`
- `bugfix/SAV-N-short-description`

### Commits
- Brief single line focusing on "why" not "what"
- Types: `feat:`, `fix:`, `test:`, `refactor:`, `docs:`, `chore:`

## File Template

Every Python file must include:
- `#!/usr/bin/env python3`
- Module docstring
- `__version__` and `__author__`
- `file_info()` → dict
- `if __name__ == "__main__": main()`

## Commands

```bash
# Tests
pipenv run pytest

# Quality
pipenv run black src/ tests/
pipenv run ruff check src/ tests/
pipenv run mypy src/
```

## Story Execution

Work through **ROADMAP.md** Stories 1-15 in order:

1. Read the story's acceptance criteria
2. Create feature branch: `feature/SAV-N-description`
3. Write tests first (TDD)
4. Implement to pass tests
5. Run full test suite
6. Create PR with UAT instructions
7. Move to next story after merge

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration tests for user-facing features
- [ ] Code formatted (black) and linted (ruff, mypy)
- [ ] PR created with UAT instructions
- [ ] Merged to main
