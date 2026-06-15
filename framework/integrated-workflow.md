# Integrated Workflow

This framework is designed so users do not need to learn Spec Kit, LangGraph, Semgrep, or Mem0 separately.

The user-facing interface is one workflow:

```text
ai-engineering-discipline
```

Internally, the framework routes work through four integrated steps:

```text
Spec   -> ai-spec   -> GitHub Spec Kit
Loop   -> ai-loop   -> LangGraph
Verify -> ai-verify -> Semgrep + native tests
Memory -> ai-memory -> Mem0 + local docs/memory
```

## What This Framework Adds

Using the four frameworks directly requires users to know:

- when requirements should become specs;
- how Spec Kit artifacts hand off to implementation work;
- when a task needs a LangGraph-style loop versus a simple runbook;
- how Semgrep fits with tests, lint, build, and CI;
- when Mem0 is useful versus local project memory;
- how evidence and memory flow across steps.

This framework owns those decisions. The user asks for a development task; the orchestrator calls the right step skills and keeps the artifacts connected.

## Default User Flow

1. Install the framework into a target project.
2. Open Claude Code or Codex in that project.
3. Ask the orchestrator to enter development.
4. The orchestrator scans the project, imports or creates specs, selects a loop, verifies results, and writes memory.

Prompt:

```text
Use ai-engineering-discipline to inspect this project and enter development.
```

## Existing Requirements

If requirements already exist, the user should not rewrite them.

Prompt:

```text
Use ai-engineering-discipline.
I already have requirement documents.
Import them into specs, create a requirements index, select the first implementation loop, and do not code until the spec and loop are ready.
```

Expected artifacts:

```text
docs/specs/requirements-index.md
docs/specs/<feature>.md
docs/loops/<selected-loop>.md
docs/verify/test-matrix.md
docs/memory/project-rules.md
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

Most users should not call `ai-spec`, `ai-loop`, `ai-verify`, or `ai-memory` directly. Those are internal step skills used by the orchestrator.
