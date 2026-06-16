---
name: ai-engineering-discipline
description: Initialize and operate Claude Code projects with the Spec / Verify / Memory + Loop framework. Use when the user wants Claude Code to bootstrap a repository, create CLAUDE.md, install docs/specs docs/verify docs/memory docs/loops, scan project commands, select an agent loop, and enter spec-first verify-gated development.
---

# AI Engineering Discipline for Claude Code

## Purpose

Use this as the orchestrator skill in Claude Code. It coordinates four step skills:

```text
ai-spec -> ai-loop -> ai-verify -> ai-memory
```

Each step skill owns one part of the default framework:

- `ai-spec`: GitHub Spec Kit
- `ai-loop`: LangGraph
- `ai-verify`: Semgrep plus native tests
- `ai-memory`: Mem0 plus local `docs/memory`

## Integrated Workflow

This framework's default behavior is one integrated workflow. Hide the step skills behind this orchestrator unless the user explicitly asks to operate a single step.

Do not ask the user to choose between Spec Kit, LangGraph, Semgrep, or Mem0. Use the default mapping:

```text
Spec   -> ai-spec   -> GitHub Spec Kit
Loop   -> ai-loop   -> LangGraph
Verify -> ai-verify -> Semgrep + native tests
Memory -> ai-memory -> Mem0 + local docs/memory
```

Default sequence:

1. Initialize framework files if missing.
2. Run project inspection.
3. If requirements exist, ask `ai-spec` behavior to import them into `docs/specs/`.
4. Select or create the first loop with `ai-loop`.
5. Refuse to code until spec and loop are ready.
6. After implementation, run `ai-verify`.
7. Finally update memory with `ai-memory`.

The user should experience one workflow, not four frameworks.

## Parameterized Request Entry

Prefer the unified CLI when it is available:

```bash
python .claude/skills/ai-engineering-discipline/scripts/ai_discipline.py run . \
  --task feature \
  --name "refund approval" \
  --requirements docs/requirements/refund.md \
  --risk medium \
  --verify
```

For separate steps:

```bash
python .claude/skills/ai-engineering-discipline/scripts/ai_discipline.py request . \
  --task feature \
  --name "refund approval" \
  --requirements docs/requirements/refund.md \
  --risk medium
python .claude/skills/ai-engineering-discipline/scripts/ai_discipline.py execute .
python .claude/skills/ai-engineering-discipline/scripts/ai_discipline.py report .
```

`report` writes the latest `docs/reports/pilot-report.md` and `docs/reports/pilot-report.json`, then archives each run under `docs/reports/runs/` by default.

Use `metrics` to aggregate pilot reports across runs or projects:

```bash
python .claude/skills/ai-engineering-discipline/scripts/ai_discipline.py metrics .
python .claude/skills/ai-engineering-discipline/scripts/ai_discipline.py metrics . --input ../project-a --input ../project-b
```

If archived runs exist, `metrics` uses them and avoids double-counting the latest report.

Read `.ai-discipline.json` for project defaults before assuming verification behavior. Show or initialize it with:

```bash
python .claude/skills/ai-engineering-discipline/scripts/ai_discipline.py config .
python .claude/skills/ai-engineering-discipline/scripts/ai_discipline.py config . --init
```

Managed requests are still the underlying mechanism. Create a request file with:

```bash
python .claude/skills/ai-engineering-discipline/scripts/run_request.py . \
  --task feature \
  --name "refund approval" \
  --requirements docs/requirements/refund.md \
  --risk medium
```

This resolves framework parameters from presets and writes:

```text
docs/ai-engineering/current-request.md
```

Then execute that request. Do not ask the user for Spec Kit, LangGraph, Semgrep, or Mem0 parameters unless the preset is blocked.

For the simplest entry, omit `--preset` or pass `--preset standard`, `--preset default`, or `--preset auto`; all select the task+risk default preset.

Prefer the safe executor before implementation:

```bash
python .claude/skills/ai-engineering-discipline/scripts/execute_request.py .
```

This creates generated spec, loop, loop-run, verify, memory-plan, memory-candidate, and execution-report files. It does not edit business code or run destructive tools.

Use explicit verification flags only when requested or when the user has approved local checks:

```bash
python .claude/skills/ai-engineering-discipline/scripts/execute_request.py . --run-semgrep
python .claude/skills/ai-engineering-discipline/scripts/execute_request.py . --run-native-checks
```

Write results to `docs/verify/verification-results.json` and `docs/verify/verification-results.md`. The structured JSON includes `can_merge`, required checks, skipped required checks, and blocking reasons.

Use `--fail-on-verify-failure` only when the caller wants a non-zero exit after results are written and the overall verification status is `blocked`.

If Claude Code setup is unclear or commands are missing, run:

```bash
python .claude/skills/ai-engineering-discipline/scripts/doctor.py .
```

This writes `docs/ai-engineering/doctor-report.md`.

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
.github/workflows/ai-discipline.yml
```

## Claude Code Operating Rules

Before implementation:

1. Read `CLAUDE.md`.
2. Use `ai-spec` to locate, import, or create specs.
3. Use `ai-loop` to choose or create the execution loop.
4. Read relevant files in `docs/specs/`, `docs/memory/`, and `docs/loops/`.
5. For managed requests, run `scripts/execute_request.py` first so `current-request.md` becomes concrete artifacts.
6. If verification flags are enabled, read `docs/verify/verification-results.json` as the structured evidence source.

During implementation:

1. Make small scoped changes.
2. Use `ai-verify` to run verify gates from `docs/verify/verify-checklist.md`.
3. Retry only within the loop budget.
4. Escalate to the user when scope, safety, or verification is unclear.

After implementation:

1. Use `ai-memory` to update memory only with real lessons, boundaries, or pitfalls.
2. Produce PR evidence using `.github/pull_request_template.md`.
3. Do not present generated explanations as verification evidence.

## Default Open-Source Adapters

When the user asks to automatically connect mature frameworks, use this default stack:

- Spec: GitHub Spec Kit
- Loop: LangGraph
- Verify: Semgrep
- Memory: Mem0

Run from the installed Claude Code skill:

```bash
python .claude/skills/ai-engineering-discipline/scripts/install_default_adapters.py .
```

If the framework repository is available, this also works:

```bash
python scripts/install_default_adapters.py <target-project-path>
```

This only plans installation and writes `docs/adapters/default-stack.md`. Add `--execute` only when the user explicitly approves dependency installation.

## Stop Conditions

Stop and ask for review before:

- destructive operations;
- production data, credentials, billing, permissions, or infrastructure changes;
- continuing without verification evidence;
- exceeding retry, time, token, or cost budget;
- changing architecture boundaries not covered by the spec.
