# Integrated Workflow

This framework is designed so users do not need to learn Spec Kit, LangGraph, Semgrep, or Mem0 separately.

The user-facing interface is one managed request:

```bash
python .claude/skills/ai-engineering-discipline/scripts/run_request.py . \
  --task feature \
  --name "refund approval" \
  --requirements docs/requirements/refund.md \
  --risk medium
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

## Preset Resolver

Users should not provide low-level framework parameters. They provide intent:

```text
task + risk + requirement path + optional execution flag
```

The preset resolver expands this into framework parameters:

```text
feature + medium
  -> Spec Kit mode=feature, acceptance criteria required
  -> LangGraph runbook=feature-slice-loop, max_retries=2, human_gate=on_verify_failure
  -> Semgrep config=auto, severity=warning, native_tests=true, require_build=true
  -> Mem0/local memory tags=[feature, medium-risk]
```

Resolved parameters are written to:

```text
docs/ai-engineering/current-request.md
```

## Default User Flow

1. Install the framework into a target project.
2. Open Claude Code or Codex in that project.
3. Create a managed request with `run_request.py`.
4. The orchestrator scans the project, imports or creates specs, selects a loop, verifies results, and writes memory.

Command:

```bash
python .claude/skills/ai-engineering-discipline/scripts/run_request.py . \
  --task feature \
  --name "my feature" \
  --requirements docs/requirements/my-feature.md \
  --risk medium
```

## Existing Requirements

If requirements already exist, the user should not rewrite them.

Command:

```bash
python .claude/skills/ai-engineering-discipline/scripts/run_request.py . \
  --task feature \
  --name "first feature" \
  --requirements docs/requirements \
  --risk medium
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

```bash
python .claude/skills/ai-engineering-discipline/scripts/run_request.py . --task feature --name "<feature-name>" --requirements docs/requirements/<feature>.md --risk medium
```

Bug fix:

```bash
python .claude/skills/ai-engineering-discipline/scripts/run_request.py . --task bugfix --name "<bug-name>" --requirements docs/requirements/<bug>.md --risk medium
```

PR validation:

```bash
python .claude/skills/ai-engineering-discipline/scripts/run_request.py . --task verify --name "pr validation" --risk medium
```

Memory update:

```text
Use ai-engineering-discipline to update memory from this task.
Only record real rules, boundaries, and pitfalls.
```

## Rule

Most users should not call `ai-spec`, `ai-loop`, `ai-verify`, or `ai-memory` directly. Those are internal step skills used by the orchestrator.
