# Contributing

Thanks for contributing to shuffle-aws-vaults! This guide summarizes expectations and workflows.

## Principles
- Small, focused changes with clear scope.
- Respect architecture boundaries (domain, application, infrastructure).
- Tests and docs accompany behavior changes.
- Security first: least privilege, no secrets in code or logs.

## Getting Started
- Read [COPILOT.md](COPILOT.md) for AI-assisted development rules.
- Review [README.md](README.md) and [USER_GUIDE.md](USER_GUIDE.md) for project context.
- Ensure Python and dependencies are installed per `pyproject.toml`/`Pipfile`.

## Development Workflow
1. Create a branch from `main`.
2. Make minimal diffs; avoid unrelated reformatting.
3. Add unit tests under `tests/unit/...` for logic changes.
4. Add integration tests under `tests/integration/...` for infra/AWS changes.
5. Update docs (README/USER_GUIDE/docstrings) for user-facing changes.
6. Run tests locally.
7. Commit with imperative messages referencing affected modules.
8. Open a PR using the template; ensure checklist is complete.

## Code Conventions
- Use `infrastructure/logger.py` (`setup_logger`, `log_operation`) for logging.
- Apply retries with `infrastructure/retry.py` (`with_retry`) for transient AWS errors.
- Load configuration via `infrastructure/config.py` (`AWSConfig.from_env`).
- Validate permissions via `infrastructure/permission_validator.py` when relevant.
- Keep `domain/` pure (no I/O, global state, or AWS calls).

## Testing
- Be specific: test the changed modules first.
- Do not fix unrelated tests; scope to your changes.
- Prefer deterministic tests; mock external services for unit tests.

## Security & Compliance
- Never hardcode credentials or secrets.
- Least privilege IAM policies; document required permissions.
- Avoid logging sensitive identifiers; scrub where necessary.

## Pull Requests
- Use the PR template and complete the checklist.
- Provide rationale, risks, and rollout notes.
- Keep scope narrow and focused.

## Issue Reporting
- Use issue templates for bugs and features.
- Include reproduction steps, expected behavior, and environment details.

## Contact
- Maintainer: John Ayers
- Roadmap: see [ROADMAP.md](ROADMAP.md)
