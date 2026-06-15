# Framework Assessment

## Current Position

This framework is not a replacement for Spec Kit, LangGraph, Semgrep, or Mem0.

It is an integrated control layer that hides their operational complexity behind:

```text
task + risk + requirements -> preset -> managed request -> orchestrated skills
```

## Difference From Direct Framework Use

Direct use requires teams to understand each framework independently:

- when to run Spec Kit and which spec artifacts to produce;
- when a task needs a LangGraph-style loop and how retries or human gates should work;
- how Semgrep fits with tests, lint, build, and CI;
- when Mem0 is useful versus local repository memory;
- how artifacts move between frameworks.

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

- Integration is still workflow/file-protocol based, not deep SDK orchestration.
- LangGraph loops are represented as runbooks; they are not yet generated as executable graphs.
- Semgrep and native-check results are written to structured verification artifacts and merged back into generated `test-matrix.md`; exact test-case mapping still needs project-specific evidence.
- Mem0 is configured as the default memory adapter, but memory writes still default to local Markdown unless a preset enables `mem0_write`.
- Presets cover common task/risk combinations, not every company policy.
- `execute_request.py` intentionally avoids business code changes and external tool execution by default.

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
2. Add a LangGraph graph generator for common runbooks.
3. Add richer policy controls for which native commands are allowed per company.
4. Add optional Mem0 write/read commands gated by preset policy.
5. Add company-specific preset overlays.
