# Pull Request

## Summary
- What does this change do?
- Why is it needed?

## Checklist
- [ ] Follows guidance in COPILOT.md (architecture boundaries, coding standards, AWS/security practices)
- [ ] Minimal, focused diffs; no unrelated reformatting or cleanups
- [ ] Unit tests added/updated under `tests/unit/...`
- [ ] Integration tests added/updated under `tests/integration/...` (for infra/AWS changes)
- [ ] Documentation updated (README/USER_GUIDE/docstrings) if behavior or CLI changes
- [ ] Uses `infrastructure/logger.py` for logging (no prints)
- [ ] Uses `infrastructure/retry.py` (`with_retry`) for transient AWS errors
- [ ] Loads config via `infrastructure/config.py` as appropriate
- [ ] Validates permissions via `infrastructure/permission_validator.py` where relevant

## Risks & Rollout
- Risks:
- Mitigations:
- Rollout plan:

## Notes
- Links to related issues/PRs:
- Any follow-up tasks:
