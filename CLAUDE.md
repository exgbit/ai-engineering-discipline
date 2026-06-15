# CLAUDE.md

This file defines the operating protocol for AI-assisted development in this repository or any project that adopts the Spec / Verify / Memory + Loop framework.

## Core Operating Model

Use four connected layers for every engineering task:

```text
Spec -> Loop -> Verify -> Memory
```

- `Spec`: define the target, boundaries, acceptance criteria, and test plan before implementation.
- `Loop`: execute work through a controlled state machine with scope, retry policy, exit conditions, and budget.
- `Verify`: prove the result with tests, checks, review evidence, or manual validation.
- `Memory`: write durable lessons, rules, boundaries, and pitfalls back into project context.

Do not treat prompt output as evidence. A generated explanation is not verification.

## Required Project Structure

When applying this framework to a product repository, prefer this structure:

```text
docs/specs/
docs/verify/
docs/memory/
docs/loops/
AGENTS.md or CLAUDE.md
```

Use these framework templates when the target project does not already have equivalents:

- `templates/spec-template.md`
- `templates/verify-checklist.md`
- `templates/memory-entry.md`
- `templates/loop-template.md`
- `templates/pr-template.md`

## Task Classification

Classify each request before acting:

| Task Type | Required Loop | Required Evidence |
|---|---|---|
| New feature | feature-slice loop | spec, tests, PR evidence |
| Bug fix | bugfix loop | reproduction, failing test or trace, passing verification |
| Refactor | refactor loop | unchanged behavior proof, regression tests |
| Migration | migration loop | rollout plan, rollback plan, data safety checks |
| Documentation | docs loop | source consistency and links |
| Framework change | framework loop | updated templates, examples, and metrics if affected |

If a repeated task does not have a loop yet, create or update a loop runbook in `docs/loops/` or `framework/`.

## Execution Protocol

### 1. Load Context

Before planning, read relevant files:

- current issue, request, or backlog item;
- related spec under `docs/specs/`;
- relevant memory under `docs/memory/`;
- existing loop under `docs/loops/` or `framework/loop-engineering.md`;
- current tests, CI scripts, and PR template.

If no spec exists for implementation work, create a minimal spec first.

### 2. Build or Select Loop

Every non-trivial task must have an explicit loop:

```text
load_context -> plan -> implement_small_step -> verify -> retry_or_escalate -> done -> memory_update
```

The loop must define:

- goal;
- allowed and forbidden scope;
- verify gates;
- success exit;
- failure exit;
- retry budget;
- escalation path;
- memory writes.

### 3. Implement in Small Steps

Keep each implementation step scoped to the spec. Do not add unrelated refactors or speculative improvements. If the spec is wrong or incomplete, stop and update the spec before continuing.

### 4. Verify Before Claiming Completion

Run the narrowest useful checks first, then broader checks when risk requires it.

Common verify gates:

- unit tests;
- integration tests;
- lint / typecheck;
- build;
- security or secret scan;
- manual validation logs;
- benchmark or performance checks;
- review checklist.

If verification cannot be run, state why and record the residual risk.

### 5. Update Memory

After completing or stopping a task, update memory when the work reveals:

- a new project rule;
- a module boundary;
- a repeated pitfall;
- a reusable loop;
- a prompt or verification pattern;
- a release or rollback lesson.

Prefer durable files over chat-only memory.

## Stop Conditions

Stop and request human review when:

- production data, credentials, billing, permissions, or infrastructure are involved;
- the loop would exceed its retry, time, token, or cost budget;
- requirements contradict existing memory or architecture rules;
- tests reveal a broader design issue;
- the task requires destructive operations;
- the agent cannot produce verification evidence.

## Anti-Rationalization Gate

Before finalizing, check for these failure modes:

| Claim | Required Proof |
|---|---|
| "It works" | Passing test, build, or manual validation |
| "Small change" | Impact analysis and affected files |
| "No risk" | Rollback path or reason risk is contained |
| "AI generated it correctly" | Human-readable verification evidence |
| "Tests can come later" | Explicit owner, risk, and follow-up date |

## PR Output Requirements

Every AI-assisted PR should include:

- linked spec or issue;
- selected loop or new loop runbook;
- AI usage summary;
- verification evidence;
- risk and rollback notes;
- memory updates or reason none were needed.

## Metrics To Track

Track these weekly during adoption:

- `spec_coverage_rate`
- `test_traceability_rate`
- `review_rounds_per_pr`
- `main_branch_failure_rate`
- `escaped_defects`
- `memory_update_rate`
- `loop_success_rate`
- `loop_retry_rate`
- `loop_escalation_rate`
- `loop_budget_overrun_rate`

Use `scripts/summarize_metrics.py` when a metrics CSV is available.

## Default Behavior

When asked to "implement", "fix", "refactor", or "build":

1. Locate or create the spec.
2. Select or define the loop.
3. Implement within scope.
4. Run verify gates.
5. Update memory if needed.
6. Report evidence, risks, and changed files.

When asked to "write an article" or "prepare a report":

1. Separate verified sources from user-provided signals.
2. Mark unverified claims clearly.
3. Prefer framework evidence, pilot metrics, and linked sources.
4. Do not present synthetic sample data as real-world proof.

## One-Line Principle

Do not prompt the agent harder. Design the loop that makes the agent useful, verifiable, and safe.
