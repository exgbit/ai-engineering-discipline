# Framework Assessment

## Current Position

This framework is not a replacement for Spec Kit, LangGraph, Semgrep, or Mem0.

It is an integrated control layer that hides their operational complexity behind:

```text
task + risk + requirements -> preset -> managed request -> orchestrated skills
```

## What the Framework Decides For You

Disciplined AI engineering by hand requires deciding:

- when a request should become a spec, and what the spec must contain;
- when a task needs a structured loop, with retries and human gates;
- how a security scan fits with tests, lint, build, and CI;
- when to write durable memory versus throwaway notes;
- how artifacts move between steps.

This framework centralizes those decisions:

- `run_request.py` accepts user intent;
- `presets/*.json` resolve low-level framework parameters;
- `docs/ai-engineering/current-request.md` becomes the handoff contract;
- the orchestrator skill calls `ai-spec`, `ai-loop`, `ai-verify`, and `ai-memory`.

## Advantages

- Users do not need to learn four frameworks before starting.
- Teams get consistent project structure and PR evidence.
- Risk policy is encoded in presets instead of improvised per developer.
- Requirement documents can be imported instead of rewritten.
- The same request format works for Claude Code and Codex.
- `execute_request.py` converts a managed request into concrete safe artifacts before implementation.

## Current Limitations

- Semgrep and native-check results are written to structured verification artifacts and merged back into generated `test-matrix.md`; exact test-case mapping still needs project-specific evidence.
- The test gate checks that a changed test references the changed code's symbols (functions/classes), which blocks empty or unrelated tests. For a stricter check, `--run-diff-coverage` (or preset `require_diff_coverage`) runs the language's coverage tool (Python/Go/JS/Java; degrades to `uncovered` if none is installed) and verifies the changed *executable* lines were actually executed by tests — this closes most of the symbol heuristic's fail-open cases (pure module-level changes, same-name cross-file). Without diff-coverage, the symbol heuristic alone is fail-open in those cases (reported as `uncovered`, not silently passed). It is an advisory discipline layer, not a tamper-proof merge gate.
- Presets cover common task/risk combinations, not every company policy. Only the preset's `verify.*` fields (and `spec.mode` / loop settings) are consumed by the deterministic scripts to drive required checks and artifacts; the other `spec.*` / `memory.*` fields (e.g. `require_rollback`, `require_edge_cases`) are advisory hints for the AI agent reading the request — the script does not tailor the generated spec from them.
- `execute_request.py` intentionally avoids business code changes and destructive operations by default.
- The framework provides discipline and gates; the actual code understanding, spec content, and judgement are done by the AI agent, not the framework.

## Data Needed To Prove Value

The included sample metrics are synthetic. A real pilot should track:

| Metric | Expected Direction |
|---|---|
| spec_coverage_rate | up |
| test_traceability_rate | up |
| review_rounds_per_pr | down |
| main_branch_failure_rate | down |
| escaped_defects | down |
| memory_update_rate | up |
| loop_success_rate | up |
| loop_budget_overrun_rate | down |

Use a four-week pilot before making claims about impact.

## Recommended Next Optimizations

1. Add exact requirement-to-test mapping instead of global verification status propagation.
2. Add real diff-coverage on top of the current symbol-reference check, to confirm the changed lines are executed by the tests.
3. Add richer policy controls for which native commands are allowed per company.
4. Add company-specific preset overlays.
