# AI Engineering Start Here

This project uses one integrated AI engineering workflow.

You do not need to learn Spec Kit, LangGraph, Semgrep, or Mem0 separately. Use the orchestrator through a managed request.

## Unified CLI

When the unified script is available, prefer it over individual helper scripts:

```bash
python .claude/skills/ai-engineering-discipline/scripts/ai_discipline.py run . --task feature --name "my feature" --requirements docs/requirements/my-feature.md --risk medium --verify
```

For separate steps:

```bash
python .claude/skills/ai-engineering-discipline/scripts/ai_discipline.py request . --task feature --name "my feature" --requirements docs/requirements/my-feature.md --risk medium
python .claude/skills/ai-engineering-discipline/scripts/ai_discipline.py execute .
python .claude/skills/ai-engineering-discipline/scripts/ai_discipline.py verify . --fail-on-verify-failure
python .claude/skills/ai-engineering-discipline/scripts/ai_discipline.py report .
```

`report` writes `docs/reports/pilot-report.md` and `.json` for team review and pilot metrics.

Aggregate reports after several runs:

```bash
python .claude/skills/ai-engineering-discipline/scripts/ai_discipline.py metrics .
```

This writes `docs/reports/pilot-summary.md`, `.json`, and `.csv`.

Defaults live in `.ai-discipline.json`. Show or initialize them with:

```bash
python .claude/skills/ai-engineering-discipline/scripts/ai_discipline.py config .
python .claude/skills/ai-engineering-discipline/scripts/ai_discipline.py config . --init
```

For CI or mature projects, set `verify`, `run_semgrep`, `run_native_checks`, and `fail_on_verify_failure` to `true`.

## Claude Code Commands

If this project was installed through `scripts/bootstrap.sh` or `scripts/bootstrap.bat`, use:

```text
/ai-start
/ai-request --task feature --name "my feature" --requirements docs/requirements/my-feature.md --risk medium
/ai-execute
/ai-verify
/ai-doctor
```

These commands live in `.claude/commands/` and call the installed `.claude/skills/ai-engineering-discipline/scripts/` helpers.

Equivalent script command:

```bash
python .claude/skills/ai-engineering-discipline/scripts/run_request.py . \
  --task feature \
  --name "my feature" \
  --requirements docs/requirements/my-feature.md \
  --risk medium
```

For the simplest entry, omit `--preset` or pass `--preset standard`, `--preset default`, or `--preset auto`; all select the task+risk default preset.

Requirement paths may be absolute, relative to your current shell directory, or relative to the target project.
External requirement files are imported by `run_request.py`; `execute_request.py` only reads requirement sources already inside this project.

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

Then create and execute a managed request:

```text
/ai-request --task feature --name "first feature" --requirements docs/requirements --risk medium
/ai-execute
```

Equivalent script command:

```bash
python .claude/skills/ai-engineering-discipline/scripts/run_request.py . --task feature --name "first feature" --requirements docs/requirements --risk medium
python .claude/skills/ai-engineering-discipline/scripts/execute_request.py .
```

Expected outputs:

```text
docs/specs/requirements-index.md
docs/specs/<feature>.md
docs/loops/<selected-loop>.md
docs/verify/test-matrix.md
```

## Daily Commands

New feature:

```text
/ai-request --task feature --name "<feature-name>" --requirements docs/requirements/<feature>.md --risk medium
/ai-execute
```

Bug fix:

```text
/ai-request --task bugfix --name "<bug-name>" --requirements docs/requirements/<bug>.md --risk medium
/ai-execute
```

PR validation:

```text
/ai-request --task verify --name "pr validation" --risk medium
/ai-verify
```

Memory update:

```text
/ai-request --task memory --name "memory update" --risk low
/ai-execute
```

## Rule

Most users should not call `ai-spec`, `ai-loop`, `ai-verify`, or `ai-memory` directly. Those are internal steps used by `ai-engineering-discipline`.

After creating a managed request, execute safe setup:

```bash
python .claude/skills/ai-engineering-discipline/scripts/execute_request.py .
```

Optional explicit verification:

```bash
python .claude/skills/ai-engineering-discipline/scripts/execute_request.py . --run-native-checks
python .claude/skills/ai-engineering-discipline/scripts/execute_request.py . --run-semgrep
```

If Claude Code setup fails, run:

```text
/ai-doctor
```

Verification results are written to `docs/verify/verification-results.json` and `docs/verify/verification-results.md`.
