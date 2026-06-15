#!/usr/bin/env python3
"""Install Spec / Verify / Memory + Loop framework files into a target project."""

from __future__ import annotations

import argparse
from pathlib import Path


CLAUDE_MD = """# CLAUDE.md

This project uses the Spec / Verify / Memory + Loop operating protocol.

## Core Workflow

```text
Spec -> Loop -> Verify -> Memory
```

- `Spec`: define goal, boundary, acceptance criteria, and test plan before implementation.
- `Loop`: execute through scoped states with retry policy, exit conditions, and budget.
- `Verify`: prove results with tests, checks, logs, review evidence, or manual validation.
- `Memory`: write durable rules, boundaries, pitfalls, and reusable loops back into docs.

Do not treat generated explanations as verification evidence.

## Default Development Behavior

When asked to implement, fix, refactor, or build:

1. Locate or create a spec in `docs/specs/`.
2. Select or create a loop in `docs/loops/`.
3. Implement in small scoped steps.
4. Run verify gates from `docs/verify/verify-checklist.md`.
5. Update `docs/memory/` if the task reveals durable lessons.
6. Report changed files, verification evidence, risks, and memory updates.

## Stop Conditions

Stop and ask for review before destructive operations, production data or infrastructure changes,
credential or permission changes, unresolved architecture conflicts, or continuing without evidence.
"""


SPEC_TEMPLATE = """# Spec Template

## Problem

Describe the business or engineering problem.

## Goal

What should this change accomplish?

## Non-Goals

What is explicitly out of scope?

## Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| R1 |  | P0 |  |

## Design Notes

Affected modules, APIs, data, permissions, configs, and external dependencies.

## Edge Cases

- Empty data:
- Permission denied:
- Timeout / retry:
- Concurrency:
- Rollback:

## Test Plan

| Requirement ID | Test Type | Test File / Case | Status |
|---|---|---|---|
| R1 | unit |  | todo |
"""


VERIFY_CHECKLIST = """# Verify Checklist

## P0: Must Pass

- [ ] Code compiles
- [ ] Unit tests pass
- [ ] Lint passes
- [ ] Typecheck passes
- [ ] No secrets or credentials committed
- [ ] Critical path regression covered
- [ ] Error handling reviewed
- [ ] Rollback path documented

## P1: Required for Review

- [ ] Spec or issue linked
- [ ] Acceptance criteria mapped to tests
- [ ] PR explains AI usage
- [ ] Risk and impact documented
- [ ] Config / migration changes documented

## Anti-Rationalization Questions

- What evidence proves this works?
- What edge case would break this?
- What did AI assume that may be false?
- What test would fail if the implementation is wrong?
"""


MEMORY_ENTRY = """# Memory Entry

## Date

YYYY-MM-DD

## Category

Project Rule / Pitfall / Module Boundary / Prompt Pattern / Incident

## Summary

One sentence summary.

## Context

Where did this come from?

## Rule / Lesson

What should happen next time?

## Related Links

- Spec:
- PR:
- Incident:
- ADR:
"""


LOOP_TEMPLATE = """# Loop Template

## Loop Name

Example: `feature-slice-loop`, `bugfix-loop`, `dependency-upgrade-loop`

## Goal

What outcome should this loop produce?

## Inputs

- Spec:
- Issue / backlog item:
- Relevant memory files:
- Allowed repositories / directories:

## Scope

Allowed:

- 

Forbidden:

- 

Requires approval:

- 

## State Model

| State | Description | Next States |
|---|---|---|
| load_context | Read spec and memory | plan, stop |
| plan | Produce small-step plan | implement, stop |
| implement | Change code or docs | verify, stop |
| verify | Run checks and collect evidence | implement, escalate, done |
| escalate | Ask for human review | implement, stop |
| done | Produce PR evidence and memory update |  |

## Verify Gates

- [ ] 

## Exit Conditions

Success:

- 

Failure:

- 

## Retry Policy

- Max retries:
- What may change between retries:
- What requires escalation:

## Budgets

- Token budget:
- Wall-time budget:
- Cost budget:
- Failure budget:

## Memory Writes

- [ ] project rule
- [ ] pitfall
- [ ] module boundary
- [ ] reusable prompt / loop lesson
"""


PR_TEMPLATE = """# What

Describe the change.

# Why

Link the spec, issue, bug, or ADR.

# AI Usage

- [ ] AI generated initial code
- [ ] AI generated tests
- [ ] AI assisted review/refactor
- [ ] No AI used

# Verification Evidence

- [ ] Unit tests:
- [ ] Integration tests:
- [ ] Lint / typecheck:
- [ ] Build:
- [ ] Manual validation:

# Loop Evidence

- Loop used:
- Exit condition reached:
- Retry / escalation notes:

# Risk and Rollback

- Risk:
- Rollback:

# Memory Updates

- [ ] No memory update needed
- [ ] Updated project rules
- [ ] Updated module map
- [ ] Updated pitfalls
- [ ] Updated loop
"""


TEST_MATRIX = """# Test Matrix

| Requirement ID | Requirement | Unit Test | Integration Test | Manual / Release Check | Status |
|---|---|---|---|---|---|
| R1 |  |  |  |  | todo |
"""


START_HERE = """# AI Engineering Start Here

This project uses one integrated AI engineering workflow.

You do not need to learn Spec Kit, LangGraph, Semgrep, or Mem0 separately. Use the orchestrator:

```text
Use ai-engineering-discipline to inspect this project and enter development.
```

## What Happens Behind the Scenes

```text
Spec   -> ai-spec   -> GitHub Spec Kit
Loop   -> ai-loop   -> LangGraph
Verify -> ai-verify -> Semgrep + native tests
Memory -> ai-memory -> Mem0 + local docs/memory
```

The framework decides when each step runs and how artifacts move between steps.

## If Requirements Already Exist

Put requirement documents under `docs/requirements/`, `docs/prd/`, or `docs/product/`, then ask:

```text
Use ai-engineering-discipline.
I already have requirement documents.
Import them into specs, create a requirements index, select the first implementation loop, and do not code until the spec and loop are ready.
```
"""


BUGFIX_LOOP = """# Bugfix Loop

## Goal

Fix one well-scoped bug with reproduction and verification evidence.

## Flow

```text
issue
  -> reproduce
  -> write failing test or capture trace
  -> implement minimal fix
  -> run focused tests
  -> run regression tests
  -> update memory if repeated
  -> produce PR evidence
```

## Verify Gates

- Reproduction evidence exists.
- Failing test or trace exists before fix when practical.
- Focused verification passes after fix.
- Related regression checks pass.
- PR explains root cause and rollback.

## Exit Conditions

Success:

- Bug fixed.
- Evidence attached.
- No unrelated refactor.

Failure:

- Root cause unclear after 2 attempts.
- Fix requires cross-module design change.
- Verification depends on unavailable external systems.
"""


PROJECT_RULES = """# Project Rules

- Add project-specific architecture and coding rules here.
- AI-generated code must include verification evidence before merge.
- Repeated mistakes should be converted into memory entries or loop updates.
"""


MODULE_MAP = """# Module Map

| Module | Owner | Boundary |
|---|---|---|
| TBD | TBD | Describe responsibility and forbidden dependencies |
"""


PITFALLS = """# Pitfalls

Record repeated bugs, failed assumptions, review findings, and incident lessons here.

## Template

- Date:
- Context:
- Problem:
- Rule / Lesson:
- Verification to add next time:
"""


FILES = {
    "CLAUDE.md": CLAUDE_MD,
    "docs/AI_ENGINEERING_START_HERE.md": START_HERE,
    "docs/specs/spec-template.md": SPEC_TEMPLATE,
    "docs/verify/verify-checklist.md": VERIFY_CHECKLIST,
    "docs/verify/test-matrix.md": TEST_MATRIX,
    "docs/memory/memory-entry.md": MEMORY_ENTRY,
    "docs/memory/project-rules.md": PROJECT_RULES,
    "docs/memory/module-map.md": MODULE_MAP,
    "docs/memory/pitfalls.md": PITFALLS,
    "docs/loops/loop-template.md": LOOP_TEMPLATE,
    "docs/loops/bugfix-loop.md": BUGFIX_LOOP,
    ".github/pull_request_template.md": PR_TEMPLATE,
}


def write_file(path: Path, content: str, force: bool) -> str:
    if path.exists() and not force:
        return "skip"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return "write"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", help="Target project path, or '.' for current directory.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing framework files.")
    args = parser.parse_args()

    target = Path(args.target).expanduser().resolve()
    if not target.exists() or not target.is_dir():
        raise SystemExit(f"Target project does not exist: {target}")

    counts = {"write": 0, "skip": 0}
    for rel_path, content in FILES.items():
        result = write_file(target / rel_path, content, args.force)
        counts[result] += 1
        print(f"{result}: {target / rel_path}")

    print()
    print("AI Engineering Discipline bootstrap complete.")
    print(f"written={counts['write']} skipped={counts['skip']}")
    print()
    print("Next steps:")
    print("1. Read docs/AI_ENGINEERING_START_HERE.md.")
    print("2. Ask Claude Code to use ai-engineering-discipline to inspect this project and enter development.")
    print("3. If requirements already exist, ask it to import them before coding.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
