# AI Engineering Start Here

This project uses one integrated AI engineering workflow.

You do not need to learn Spec Kit, LangGraph, Semgrep, or Mem0 separately. Use the orchestrator through a managed request.

```bash
python .claude/skills/ai-engineering-discipline/scripts/run_request.py . \
  --task feature \
  --name "my feature" \
  --requirements docs/requirements/my-feature.md \
  --risk medium
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

Then create a managed request:

```bash
python .claude/skills/ai-engineering-discipline/scripts/run_request.py . \
  --task feature \
  --name "first feature" \
  --requirements docs/requirements \
  --risk medium
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

```bash
python .claude/skills/ai-engineering-discipline/scripts/run_request.py . \
  --task feature \
  --name "<feature-name>" \
  --requirements docs/requirements/<feature>.md \
  --risk medium
```

Bug fix:

```bash
python .claude/skills/ai-engineering-discipline/scripts/run_request.py . \
  --task bugfix \
  --name "<bug-name>" \
  --requirements docs/requirements/<bug>.md \
  --risk medium
```

PR validation:

```bash
python .claude/skills/ai-engineering-discipline/scripts/run_request.py . \
  --task verify \
  --name "pr validation" \
  --risk medium
```

Memory update:

```text
Use ai-engineering-discipline to update memory from this task.
Only record real rules, boundaries, and pitfalls.
```

## Rule

Most users should not call `ai-spec`, `ai-loop`, `ai-verify`, or `ai-memory` directly. Those are internal steps used by `ai-engineering-discipline`.

After creating a managed request, ask Claude Code:

```text
Use ai-engineering-discipline to execute docs/ai-engineering/current-request.md.
```
