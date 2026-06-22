---
name: ai-engineering-discipline
description: Turn any plain-language development request into a finished, verified change. Use whenever the user asks to add a feature, fix a bug, refactor, migrate, improve, or otherwise change code in this project — phrased in ordinary language like "add a refund approval flow" or "fix the login timeout". Infer the task type, write and fill the spec, implement in small steps, and verify automatically, without making the user learn task types, risk levels, presets, or the Spec/Loop/Verify/Memory workflow. Also use to bootstrap a repository with the framework.
---

# AI Engineering Discipline

## Purpose

Use this as the orchestrator skill. It coordinates four step skills:

```text
ai-spec -> ai-loop -> ai-verify -> ai-memory
```

Each step skill owns one engineering control:

- `ai-spec`: turn the request into a spec (the framework's own template, filled by you the agent)
- `ai-loop`: run the work through a controlled loop (the framework's own runbook)
- `ai-verify`: prove it with native tests plus an optional Semgrep security scan
- `ai-memory`: persist durable lessons in local `docs/memory`

## Integrated Workflow

This framework's default behavior is one integrated workflow. Keep `ai-spec`, `ai-loop`, `ai-verify`, and `ai-memory` behind this orchestrator unless the user explicitly asks to operate a single step.

The four controls map to the four step skills; only Verify calls an external tool (Semgrep, optional):

```text
Spec   -> ai-spec   -> framework's own spec template, filled by the agent
Loop   -> ai-loop   -> framework's own loop runbook
Verify -> ai-verify -> native tests + optional Semgrep security scan
Memory -> ai-memory -> local docs/memory
```

Integration depth differs by design: only Verify runs an external tool (Semgrep) at runtime via `execute_request.py`, and even that is optional. Spec/Loop/Memory are implemented entirely by the framework's own Markdown templates plus you (the agent); the tool name in each row (Spec Kit / LangGraph / Mem0) is only a style reference — the framework does not call them and they do not need to be installed. See `framework/integration-levels.md`.

## Default Entry: One Plain Sentence

This is the primary way to use the framework. The user should never have to pick a "task type", "risk", or "preset", or learn what Spec / Loop / Verify / Memory mean. When the user expresses any development intent in ordinary language — "add a refund approval flow", "fix the login timeout", "rename X to Y", "make the report query faster" — drive the whole flow yourself:

1. **Infer, do not ask.** From the sentence, infer the task type (feature / bugfix / refactor / migration / docs / verify / memory) and a short name. Use that task's default risk. Do not ask the user to choose any of these.
2. **Capture the requirement.** Write the user's request into `docs/requirements/<slug>.md` as one short file so it becomes a tracked source.
3. **Generate the scaffold** by running the managed request (this writes the spec/loop/verify/memory artifacts):
   ```bash
   python <skill_dir>/scripts/ai_discipline.py run . \
     --task <inferred> --name "<inferred name>" --requirements docs/requirements/<slug>.md
   ```
4. **Read the code, then fill the spec yourself.** First read the source files the request touches to understand the existing structure (the scripts do not analyze code — that is your job). Then complete the generated spec's `TBD` placeholders (requirements, impact analysis, acceptance criteria, test plan) from that understanding: give a real Impact Analysis (which modules/functions are affected and how), and fill `docs/memory/module-map.md` with the boundaries you found. Never hand `TBD`s back to the user.
5. **Implement in small steps, with tests.** Once the spec and loop are ready, implement the change in scoped steps following the loop. For feature/bugfix/refactor work you MUST add or update tests that actually exercise the changed code (they reference the changed functions/classes) — the gate blocks a code change with no test, and also blocks tests that do not reference the change (e.g. an empty or unrelated test). Before editing code, state the plan in one plain sentence and proceed unless the user objects.
6. **Verify, then refresh the report.** Run native checks (and Semgrep if installed), then refresh the pilot report so it is not left showing a stale pre-verify snapshot:
   ```bash
   python <skill_dir>/scripts/ai_discipline.py execute . --run-native-checks
   python <skill_dir>/scripts/ai_discipline.py report .
   ```
   Read `can_merge` / `coverage_complete` / blocking reasons from `docs/verify/verification-results.json`.
7. **Report to the user in plain language only.** Give one short plain message: what you built, whether the tests pass, and anything not covered (e.g. "added delete-by-title with a test; all tests pass; the security scan isn't installed so it didn't run"). Do NOT show the user the generated spec/loop/verify/memory files, `TBD` placeholders, or internal terms like `can_merge`/`coverage_complete` — those are working artifacts, not for the user. Never present "done" as fully verified when `coverage_complete` is false. The framework auto-writes `docs/ai-engineering/SUMMARY.md` in plain language with the same facts — make your message match it (it is the fallback if you don't translate). Update memory only with durable lessons.

**If the user already has a requirements folder** (many `.md` files and/or images, screenshots, diagrams, PDFs), use it instead of inventing the requirement: pass the whole folder to `--requirements <folder>` — it ingests text docs and images/PDFs alike. Then **read every Markdown file and visually inspect every image/PDF in it** to extract the requirements, and fold them into the spec. Image/PDF content is understood by you visually; the scripts only track the files, they do not read images.

Throughout, talk to the user about *what* is happening in ordinary language — never in terms of "Spec/Loop/Verify/Memory". Stop and ask only for real stop conditions (destructive operations, production data, credentials, permissions, or unresolvable conflicts).

## Underlying Mechanism

The sections below are how the flow above is implemented. The user does not need to see these commands or terms.

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

If setup is unclear or commands are missing, run:

```bash
python <skill_dir>/scripts/doctor.py .
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
- Run machine gates via `execute_request.py` (Semgrep + native checks; `can_merge` comes from the preset's required checks). Use `docs/verify/verify-checklist.md` as the complementary human review checklist.
- Update memory only with durable lessons learned during the task.

For managed requests, prefer `scripts/execute_request.py` before implementation. It converts `docs/ai-engineering/current-request.md` into concrete generated artifacts, so the agent does not need to reinterpret low-level framework parameters.
The generated artifacts include impact analysis and regression matrices for already-developed codebases.

If verification flags are enabled, treat `docs/verify/verification-results.json` as the structured evidence source and `docs/verify/verification-results.md` as the review summary.

### 5. Optional Semgrep Scan

The framework needs no external tools. The only optional one is Semgrep (the Verify security gate); if it is absent the scan is reported as skipped, not failed. Spec / Loop / Memory use the framework's own templates and need nothing installed. Install Semgrep only (with `--execute`) from the framework repository:

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
