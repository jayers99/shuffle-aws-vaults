# COPILOT.md

This guide instructs GitHub Copilot and Copilot Chat on how to work within this repository so generated changes are safe, consistent, and testable. Prefer small, surgical edits and preserve public APIs unless the task explicitly requires changes.

## Goals

- Align AI contributions with repo architecture and conventions.
- Fix problems at the root cause, not with surface patches.
- Always include tests and documentation updates when behavior changes.

## Repository Map

- Package: `shuffle_aws_vaults`
- Source root: `src/shuffle_aws_vaults`
- Layers:
  - `application/`: service orchestration (`copy_service.py`, `filter_service.py`, `list_service.py`, `metadata_enrichment_service.py`, `verify_service.py`).
  - `domain/`: core models/rules (`vault.py`, `recovery_point.py`, `filter_rule.py`, `migration_result.py`, `summary_report.py`, `state.py`).
  - `infrastructure/`: adapters, repositories, AWS integrations.
- Entry point: `cli.py` exposes command-line operations.
- Tests: `tests/unit/...` and `tests/integration/...`.
- Docs: `README.md`, `USER_GUIDE.md`, `ROADMAP.md`.
- Utilities: `infrastructure/logger.py`, `infrastructure/retry.py`, `infrastructure/config.py`, `infrastructure/permission_validator.py`, `infrastructure/progress_tracker.py`, `infrastructure/signal_handler.py`.

## Coding Standards

- Python: adhere to versions/configs in `pyproject.toml`/`Pipfile`.
- Style: follow existing patterns; do not reformat unrelated files.
- Naming: clear, descriptive; avoid single-letter variable names.
- Errors: raise specific exceptions; no silent failure paths.
- Logging: use `infrastructure/logger.py` (`setup_logger`, `log_operation`); avoid `print` in library code.
- Dependencies: prefer stdlib; if adding deps, update `pyproject.toml` and justify in PR.
- I/O: isolate to `infrastructure/`; keep `domain/` pure and deterministic.

## Architecture Principles

- Domain model purity: no I/O, no AWS calls, no global state.
- Services: composable, testable, minimal side effects; constructors should not perform work.
- CLI: delegates to services; no business logic in `cli.py`.
- Separation: keep boundaries clear between application, domain, and infrastructure.

## Security & AWS Practices

- Credentials: never hardcode; use existing credential management and configuration patterns.
- Permissions: validate via `infrastructure/permission_validator.py`; enforce least privilege.
- Config: load via `infrastructure/config.py` (`AWSConfig.from_env()` where appropriate).
- Retries: use `infrastructure/retry.py` (`with_retry` decorator); avoid ad-hoc sleeps.
- Rate limits: respect AWS best practices; implement exponential backoff where applicable.
- Secrets: do not log sensitive values; scrub identifiers in logs when necessary.

## Testing Requirements

- Unit tests: for each change, add/adjust tests near the module under `tests/unit/...`.
- Integration tests: for AWS/persistence/infrastructure changes, add/adjust under `tests/integration/...`.
- Scope: write specific tests for edited modules first; avoid fixing unrelated failures.
- Coverage: prefer targeted coverage gain over broad additions; consult `htmlcov/` reports as needed.

## Documentation Updates

- README: update for new CLI flags, workflows, or setup.
- USER_GUIDE: reflect user-facing behavior changes.
- Docstrings: add/update for new public classes/functions.
- Changelogs/notes: summarize rationale and risks in PR description.

## Working With Copilot Chat

- Always reference this file: “Follow COPILOT.md rules.”
- Provide exact paths and symbols: e.g., "Modify `src/shuffle_aws_vaults/application/verify_service.py`: add X and update tests in `tests/unit/application`".
- Ask for minimal diffs, root-cause fixes, and test updates.
- Prefer patches that keep style and APIs consistent unless the task calls for refactors.

### Prompt Examples

- "Implement validation in `verify_service` for scenario X; add unit tests under `tests/unit/application/` and update `README.md` if CLI flags change."
- "Add method to `domain/vault.py` to compute Y; keep domain pure and update `tests/unit/domain/`."
- "Introduce AWS adapter in `infrastructure/` for Z using existing retry/logging utilities; include integration tests."

## Do / Don’t

- Do: small, focused patches; explicit error handling; maintain boundaries; add tests.
- Do: update docs when user-facing behavior changes; prefer existing utilities.
- Don’t: reformat entire files; introduce global state; mix domain and infrastructure concerns.
- Don’t: add copyright/license headers.

## Commits & PRs

- Commits: imperative, concise, reference affected modules (e.g., "application: add metadata enrichment for X").
- PRs: narrow scope; include rationale, risks, and testing notes.
- Diffs: show only necessary changes; avoid unrelated cleanups.

## Maintenance

- Keep this file current with architecture/convention changes.
- When guidance changes, update tests/docs to reflect new standards.
