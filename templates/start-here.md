# AI Engineering Start Here

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

Put requirement documents under a clear directory, such as:

```text
docs/requirements/
docs/prd/
docs/product/
```

Then ask:

```text
Use ai-engineering-discipline.
I already have requirement documents.
Import them into specs, create a requirements index, select the first implementation loop, and do not code until the spec and loop are ready.
```

Expected outputs:

```text
docs/specs/requirements-index.md
docs/specs/<feature>.md
docs/loops/<selected-loop>.md
docs/verify/test-matrix.md
```

## Daily Prompts

New feature:

```text
Use ai-engineering-discipline to develop <feature-name>.
Start from spec and do not code until spec and loop are ready.
```

Bug fix:

```text
Use ai-engineering-discipline to fix this bug.
Reproduce first, then verify the minimal fix.
```

PR validation:

```text
Use ai-engineering-discipline to verify this PR and produce PR evidence.
```

Memory update:

```text
Use ai-engineering-discipline to update memory from this task.
Only record real rules, boundaries, and pitfalls.
```

## Rule

Most users should not call `ai-spec`, `ai-loop`, `ai-verify`, or `ai-memory` directly. Those are internal steps used by `ai-engineering-discipline`.
