---
name: ai-engineering-discipline
description: Turn any plain-language development request into a finished, verified change. Use whenever the user asks to add a feature, fix a bug, refactor, migrate, improve, or otherwise change code in this project — phrased in ordinary language like "add a refund approval flow" or "fix the login timeout". Infer the task type, write and fill the spec, implement in small steps, and verify automatically, without making the user learn task types, risk levels, presets, or the Spec/Loop/Verify/Memory workflow. Also use to bootstrap a repository with the framework.
---

# AI Engineering Discipline for Claude Code

## Purpose

Use this as the orchestrator skill in Claude Code. It coordinates four step skills:

```text
ai-spec -> ai-loop -> ai-verify -> ai-memory
```

Each step skill owns one engineering control:

- `ai-spec`: turn the request into a spec (the framework's own template, filled by you the agent)
- `ai-loop`: run the work through a controlled loop (the framework's own runbook)
- `ai-verify`: prove it with native tests, required codebase-memory impact analysis, and an optional Semgrep security scan
- `ai-memory`: persist durable lessons in local `docs/memory`

## Integrated Workflow

This framework's default behavior is one integrated workflow. Hide the step skills behind this orchestrator unless the user explicitly asks to operate a single step.

Do not surface tool names to the user. The four controls map to the four step skills; only Verify calls runtime external tools (codebase-memory required for impact analysis, Semgrep optional for security scanning):

```text
Spec   -> ai-spec   -> framework's own spec template, filled by the agent
Loop   -> ai-loop   -> framework's own loop runbook
Verify -> ai-verify -> native tests + required codebase-memory impact analysis + optional Semgrep security scan
Memory -> ai-memory -> local docs/memory
```

Integration depth differs by design: only Verify runs runtime external tools via `execute_request.py`: codebase-memory is required for impact analysis, while Semgrep is optional for security scanning. Spec/Loop/Memory are implemented entirely by the framework's own Markdown templates plus you (the agent); the tool name in each row (Spec Kit / LangGraph / Mem0) is only a style reference — the framework does not call them and they do not need to be installed. See `framework/integration-levels.md`.

## Default Entry: One Plain Sentence

This is the primary way to use the framework. The user should never have to pick a "task type", "risk", or "preset", or learn what Spec / Loop / Verify / Memory mean. When the user expresses any development intent in ordinary language — "add a refund approval flow", "fix the login timeout", "rename X to Y", "make the report query faster" — drive the whole flow yourself:

1. **Infer, do not ask.** From the sentence, infer the task type (feature / bugfix / refactor / migration / docs / verify / memory) and a short name. Use that task's default risk. Do not ask the user to choose any of these.
2. **Capture the requirement.** Write the user's request into `docs/requirements/<slug>.md` as one short file so it becomes a tracked source.
3. **Generate the scaffold** by running the managed request (this writes the spec/loop/verify/memory artifacts):
   ```bash
   python .claude/skills/ai-engineering-discipline/scripts/ai_discipline.py run . \
     --task <inferred> --name "<inferred name>" --requirements docs/requirements/<slug>.md
   ```
4. **Build the graph, then fill the spec yourself.** First read the source files the request touches to understand the existing structure (the scripts do not analyze code — that is your job). **codebase-memory (a code knowledge-graph MCP) is REQUIRED — the verify gate blocks a code change without it (opt out only via `AI_DISCIPLINE_GRAPH_OPTIONAL=1`). The framework auto-runs it during verify and writes the blast radius to `docs/verify/impact-graph.md`. You can also call `detect_changes`/`explore` directly to get the affected interfaces and transitive callers, and fill the Impact Analysis from that blast radius — sanity-check it; the framework does not judge the graph's quality.** For a new project, build the graph as soon as the first source/test skeleton exists and use the requirement to define the initial unit tests. For an existing project, build/refresh the graph before implementation and use the impacted function/API/interface set to decide which tests must exist. Then complete the generated spec's `TBD` placeholders (requirements, impact analysis, acceptance criteria, test plan): give a real Impact Analysis and fill `docs/memory/module-map.md` with the boundaries you found. Never hand `TBD`s back to the user.
5. **Write or update tests before implementation.** New project: create the requirement-driven test cases/unit tests first. Existing project: from the graph blast radius, refresh blind spots with `ai_discipline.py index .`; for every requirement-touched or transitively affected interface with no guarding test, add the necessary test **before** editing implementation. After writing the tests and before editing implementation, record the red phase:
   ```bash
   python .claude/skills/ai-engineering-discipline/scripts/ai_discipline.py execute . --record-red-phase
   ```
   This writes `docs/verify/red-phase-results.json` / `.md`; tests are expected to fail here. If they do not fail, fix the tests before implementation. Then implement in scoped steps following the loop until the tests pass. For feature/bugfix/refactor/migration work you MUST add or update tests that actually exercise the changed code (they reference the changed functions/classes), and the final full test suite must pass. The gate blocks code changes with no test, unrelated tests, missing runnable tests, affected interfaces without guarding tests, missing required diff coverage, a missing knowledge graph, or a graph that returns no affected interface for changed business code. Before editing code, state the plan in one plain sentence and proceed unless the user objects.
6. **Verify, then refresh the report.** Run native checks with diff coverage (and Semgrep if installed), fail on blocking or incomplete required evidence, then refresh the pilot report so it is not left showing a stale pre-verify snapshot:
   ```bash
   python .claude/skills/ai-engineering-discipline/scripts/ai_discipline.py execute . --run-native-checks --run-diff-coverage --run-semgrep --fail-on-verify-failure --fail-on-incomplete-coverage
   python .claude/skills/ai-engineering-discipline/scripts/ai_discipline.py report .
   ```
   Read `can_merge` / `coverage_complete` / blocking reasons from `docs/verify/verification-results.json`.
7. **Report to the user in plain language only.** Give one short plain message: what you built, whether the tests pass, and anything not covered (e.g. "added delete-by-title with a test; all tests pass; the security scan isn't installed so it didn't run"). Do NOT show the user the generated spec/loop/verify/memory files, `TBD` placeholders, or internal terms like `can_merge`/`coverage_complete` — those are working artifacts, not for the user. Never present "done" as fully verified when `coverage_complete` is false. The framework auto-writes `docs/ai-engineering/SUMMARY.md` in plain language with the same facts — make your message match it (it is the fallback if you don't translate). Update memory only with durable lessons.

**If the user already has a requirements folder** (many `.md` files and/or images, screenshots, diagrams, PDFs), use it instead of inventing the requirement: pass the whole folder to `--requirements <folder>` — it ingests text docs and images/PDFs alike. Then **read every Markdown file and visually inspect every image/PDF in it** to extract the requirements, and fold them into the spec. Image/PDF content is understood by you visually; the scripts only track the files, they do not read images.

Throughout, talk to the user about *what* is happening in ordinary language — never in terms of "Spec/Loop/Verify/Memory". Stop and ask only for real stop conditions (destructive operations, production data, credentials, permissions, or unresolvable conflicts).

## Underlying Mechanism

The sections below are how the flow above is implemented. They are the default-entry steps in detail — the user does not need to see these commands or terms.

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

Then execute that request. Do not ask the user for low-level verification parameters unless the preset is blocked.

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
7. For existing projects, identify affected modules, coupling risks, compatibility constraints, and required regression checks before coding.

During implementation:

1. Make small scoped changes.
2. Run machine gates with `ai-verify` / `execute_request.py` (Semgrep + native checks; `can_merge` is computed from the preset's required checks, not from the checklist file). Use `docs/verify/verify-checklist.md` as the complementary human review checklist.
3. Retry only within the loop budget.
4. Escalate to the user when scope, safety, or verification is unclear.

After implementation:

1. Use `ai-memory` to update memory only with real lessons, boundaries, or pitfalls.
2. Produce PR evidence using `.github/pull_request_template.md`.
3. Do not present generated explanations as verification evidence.
4. Ensure the generated impact analysis and regression matrix are complete for already-developed codebases.

## Optional Semgrep Scan

The framework needs codebase-memory for the Verify impact-analysis gate on development tasks. Semgrep is optional for the Verify security gate; if it is absent the scan is reported as skipped/uncovered, not silently successful. Spec / Loop / Memory use the framework's own templates and need no external template framework.

Check or install Semgrep from the installed Claude Code skill (add `--execute` to install):

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
