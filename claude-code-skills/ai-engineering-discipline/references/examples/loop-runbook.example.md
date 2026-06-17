# Loop Runbook Example: Bugfix Loop

## Goal

Fix one well-scoped bug with test evidence and a memory update if the bug reveals a repeated pattern.

## Flow

```text
issue
  -> read linked spec or reproduce steps
  -> inspect failing area
  -> write or update failing test
  -> implement minimal fix
  -> run focused tests
  -> run broader regression tests
  -> update pitfalls if repeated
  -> open PR with evidence
```

## Verify Gates

- Reproduction test fails before fix.
- Reproduction test passes after fix.
- Related regression tests pass.
- PR explains root cause and rollback.

## Exit Conditions

Success:

- Bug is fixed.
- Test evidence is attached.
- No unrelated refactor is included.

Failure:

- Root cause remains unclear after 2 attempts.
- Fix requires cross-module design change.
- Tests require unavailable external systems.

## Escalation

Escalate to a human reviewer when the loop needs production data, schema changes, permission changes, or broad architectural decisions.
