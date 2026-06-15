---
name: ai-engineering-discipline
description: Initialize and operate Claude Code projects with the Spec / Verify / Memory + Loop framework. Use when the user wants Claude Code to bootstrap a repository, create CLAUDE.md, install docs/specs docs/verify docs/memory docs/loops, scan project commands, select an agent loop, and enter spec-first verify-gated development.
---

# AI Engineering Discipline for Claude Code

## Purpose

Use this skill in Claude Code to reduce manual project setup and force AI-assisted development through:

```text
Spec -> Loop -> Verify -> Memory
```

## Initialize a Project

If the current directory is the target project:

```bash
python .claude/skills/ai-engineering-discipline/scripts/init_project.py .
python .claude/skills/ai-engineering-discipline/scripts/inspect_project.py .
```

If initializing another project:

```bash
python <skill_dir>/scripts/init_project.py <target-project-path>
python <skill_dir>/scripts/inspect_project.py <target-project-path>
```

Use `--force` only when the user explicitly asks to overwrite existing framework files.

## What Initialization Creates

```text
CLAUDE.md
docs/specs/spec-template.md
docs/verify/verify-checklist.md
docs/verify/test-matrix.md
docs/memory/memory-entry.md
docs/memory/project-rules.md
docs/memory/module-map.md
docs/memory/pitfalls.md
docs/memory/project-scan.md
docs/loops/loop-template.md
docs/loops/bugfix-loop.md
.github/pull_request_template.md
```

## Claude Code Operating Rules

Before implementation:

1. Read `CLAUDE.md`.
2. Read relevant files in `docs/specs/`, `docs/memory/`, and `docs/loops/`.
3. If no spec exists, create one before coding.
4. If no suitable loop exists, create one before coding.

During implementation:

1. Make small scoped changes.
2. Run verify gates from `docs/verify/verify-checklist.md`.
3. Retry only within the loop budget.
4. Escalate to the user when scope, safety, or verification is unclear.

After implementation:

1. Update memory only with real lessons, boundaries, or pitfalls.
2. Produce PR evidence using `.github/pull_request_template.md`.
3. Do not present generated explanations as verification evidence.

## Stop Conditions

Stop and ask for review before:

- destructive operations;
- production data, credentials, billing, permissions, or infrastructure changes;
- continuing without verification evidence;
- exceeding retry, time, token, or cost budget;
- changing architecture boundaries not covered by the spec.
