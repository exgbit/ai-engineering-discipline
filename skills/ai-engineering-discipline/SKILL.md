---
name: ai-engineering-discipline
description: Bootstrap and operate AI-assisted software projects with the Spec / Verify / Memory + Loop framework. Use when the user wants to initialize a project for Claude Code, reduce manual setup, create CLAUDE.md/AGENTS-style operating rules, install docs/specs docs/verify docs/memory docs/loops templates, choose an agent loop, or enter development with automated spec-first, verify-gated, memory-writing workflow.
---

# AI Engineering Discipline

## Purpose

Use this as the orchestrator skill. It coordinates four step skills:

```text
ai-spec -> ai-loop -> ai-verify -> ai-memory
```

Each step skill owns one default open-source framework:

- `ai-spec`: GitHub Spec Kit
- `ai-loop`: LangGraph
- `ai-verify`: Semgrep plus native tests
- `ai-memory`: Mem0 plus local `docs/memory`

## Integrated Workflow

This framework's default behavior is one integrated workflow. Keep `ai-spec`, `ai-loop`, `ai-verify`, and `ai-memory` behind this orchestrator unless the user explicitly asks to operate a single step.

Default mapping:

```text
Spec   -> ai-spec   -> GitHub Spec Kit
Loop   -> ai-loop   -> LangGraph
Verify -> ai-verify -> Semgrep + native tests
Memory -> ai-memory -> Mem0 + local docs/memory
```

If requirement documents already exist, import them first with the `ai-spec` workflow, create `docs/specs/requirements-index.md`, then select a loop. Do not code until spec and loop are ready.

The skill should minimize human setup:

```text
bootstrap project -> inspect context -> ensure spec -> select loop -> verify -> update memory
```

## Parameterized Request Entry

Prefer the unified CLI when it is available:

```bash
python <skill_dir>/scripts/ai_discipline.py run . \
  --task feature \
  --name "refund approval" \
  --requirements docs/requirements/refund.md \
  --risk medium \
  --verify
```

For separate steps:

```bash
python <skill_dir>/scripts/ai_discipline.py request . \
  --task feature \
  --name "refund approval" \
  --requirements docs/requirements/refund.md \
  --risk medium
python <skill_dir>/scripts/ai_discipline.py execute .
python <skill_dir>/scripts/ai_discipline.py report .
```

`report` writes the latest `docs/reports/pilot-report.md` and `docs/reports/pilot-report.json`, then archives each run under `docs/reports/runs/` by default.

Use `metrics` to aggregate pilot reports across runs or projects:

```bash
python <skill_dir>/scripts/ai_discipline.py metrics .
python <skill_dir>/scripts/ai_discipline.py metrics . --input ../project-a --input ../project-b
```

If archived runs exist, `metrics` uses them and avoids double-counting the latest report.

Read `.ai-discipline.json` for project defaults before assuming verification behavior. Show or initialize it with:

```bash
python <skill_dir>/scripts/ai_discipline.py config .
python <skill_dir>/scripts/ai_discipline.py config . --init
```

Managed requests are still the underlying mechanism. Create a request file with:

```bash
python .codex/skills/ai-engineering-discipline/scripts/run_request.py . \
  --task feature \
  --name "refund approval" \
  --requirements docs/requirements/refund.md \
  --risk medium
```

This resolves framework parameters from presets and writes `docs/ai-engineering/current-request.md`. Execute that request through this orchestrator.

For the simplest entry, omit `--preset` or pass `--preset standard`, `--preset default`, or `--preset auto`; all select the task+risk default preset.

Then execute safe setup artifacts:

```bash
python <skill_dir>/scripts/execute_request.py .
```

This creates generated spec, loop, loop-run, verify, memory-plan, memory-candidate, and execution-report files. It does not edit business code or run destructive tools.

Use explicit verification flags only when requested or when the user has approved local checks:

```bash
python <skill_dir>/scripts/execute_request.py . --run-semgrep
python <skill_dir>/scripts/execute_request.py . --run-native-checks
```

Write results to `docs/verify/verification-results.json` and `docs/verify/verification-results.md`. The structured JSON includes `can_merge`, required checks, skipped required checks, and blocking reasons.

Use `--fail-on-verify-failure` only when the caller wants a non-zero exit after results are written and the overall verification status is `blocked`.

If Claude Code setup is unclear or commands are missing, run:

```bash
python .claude/skills/ai-engineering-discipline/scripts/doctor.py .
```

This writes `docs/ai-engineering/doctor-report.md`.

## Quick Start

When the user asks to initialize a project, run:

```bash
python <skill_dir>/scripts/init_project.py <target-project-path>
```

If the user is already inside the target project, use:

```bash
python <skill_dir>/scripts/init_project.py .
```

Use `--force` only when the user explicitly wants to overwrite existing framework files.

## Execution Workflow

### 1. Initialize Framework Files

Run `scripts/init_project.py` against the target repository. It creates:

```text
CLAUDE.md
docs/specs/spec-template.md
docs/verify/verify-checklist.md
docs/verify/test-matrix.md
docs/memory/memory-entry.md
docs/memory/project-rules.md
docs/memory/module-map.md
docs/memory/pitfalls.md
docs/loops/loop-template.md
docs/loops/bugfix-loop.md
.github/pull_request_template.md
.github/workflows/ai-discipline.yml
```

### 2. Inspect the Target Project

After initialization, inspect the repository before editing source code:

```bash
python <skill_dir>/scripts/inspect_project.py <target-project-path>
```

This writes `docs/memory/project-scan.md` with detected stack signals, candidate commands, and important directories. Review it before treating it as a rule source.

- identify language and framework;
- identify build, test, lint, and package commands;
- identify main source, test, config, and migration directories;
- inspect existing README, package metadata, CI files, and test layout.

Write only real findings. Do not invent project history.

### 3. Seed Memory

Update these files when evidence exists:

- `docs/memory/project-rules.md`: architecture, coding, testing, and review rules.
- `docs/memory/module-map.md`: module ownership and dependency boundaries.
- `docs/memory/pitfalls.md`: real repeated problems or risks discovered in code/review.

If evidence is insufficient, leave TODO placeholders instead of guessing.

### 4. Enter Development

For implementation work, enforce:

```text
Spec -> Loop -> Verify -> Memory
```

- Treat existing projects as the default case. Before coding, map the current baseline, affected modules, coupling risks, compatibility constraints, and required regression checks.
- If no spec exists, create one from `docs/specs/spec-template.md` before coding.
- If no loop exists for the task type, create one from `docs/loops/loop-template.md`.
- Use `docs/loops/bugfix-loop.md` for bug fixes with reproduction steps.
- Run verification from `docs/verify/verify-checklist.md`.
- Update memory only with durable lessons learned during the task.

For managed requests, prefer `scripts/execute_request.py` before implementation. It converts `docs/ai-engineering/current-request.md` into concrete generated artifacts, so the agent does not need to reinterpret low-level framework parameters.
The generated artifacts include impact analysis and regression matrices for already-developed codebases.

If verification flags are enabled, treat `docs/verify/verification-results.json` as the structured evidence source and `docs/verify/verification-results.md` as the review summary.

### 5. Install Default Open-Source Adapters

When the user wants mature GitHub/open-source frameworks automatically connected, use the default stack:

- Spec: GitHub Spec Kit
- Loop: LangGraph
- Verify: Semgrep
- Memory: Mem0

Run from the framework repository:

```bash
python scripts/install_default_adapters.py <target-project-path>
```

Or run from an installed skill:

```bash
python <skill_dir>/scripts/install_default_adapters.py <target-project-path>
```

This is a dry run that writes `docs/adapters/default-stack.md`. Run with `--execute` only after the user confirms real installation.

### 6. Stop Conditions

Stop and ask the user before:

- destructive operations;
- production data or infrastructure changes;
- credential, billing, permission, or security-sensitive changes;
- exceeding retry, time, token, or cost budget;
- continuing without verification evidence.

## Recommended Command Entries

Initialize current project:

```bash
python <skill_dir>/scripts/init_project.py .
python <skill_dir>/scripts/inspect_project.py .
```

Start a feature:

```bash
python <skill_dir>/scripts/run_request.py . --task feature --name "<feature>" --requirements docs/requirements/<feature>.md --risk medium
python <skill_dir>/scripts/execute_request.py .
```

Fix a bug:

```bash
python <skill_dir>/scripts/run_request.py . --task bugfix --name "<bug>" --requirements docs/requirements/<bug>.md --risk medium
python <skill_dir>/scripts/execute_request.py .
```

Run verification:

```bash
python <skill_dir>/scripts/run_request.py . --task verify --name "pr validation" --risk medium
python <skill_dir>/scripts/execute_request.py . --run-native-checks --run-semgrep
```
