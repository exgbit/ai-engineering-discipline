# Presets

Presets hide low-level framework parameters from users.

Users provide:

```text
task + risk + requirement path
```

The framework resolves:

```text
spec mode and required spec sections
loop runbook, retries, checkpoint, human gate
native checks, required diff coverage for development tasks, Semgrep config/severity when security scanning is required
memory write behavior and tags
```

Example:

```bash
python scripts/run_request.py /path/to/project \
  --task feature \
  --name "refund approval" \
  --requirements /path/to/refund.md \
  --risk medium
```

This writes `docs/ai-engineering/current-request.md` with the resolved parameters.

## Field Semantics: Enforced vs Advisory

Preset fields fall into two tiers. **Enforced** fields are consumed by the deterministic
scripts (`run_request.py` / `execute_request.py`) and change what the framework generates,
checks, or blocks on. **Advisory** fields are copied verbatim into
`current-request.md` for the AI agent to read; the scripts do not read them, so they
shape agent behavior only, never the gate.

| Field | Tier | Consumed by |
|---|---|---|
| `spec.mode` | enforced | `execute_request.py` (written into the spec's Design Notes) |
| `spec.require_non_goals` / `require_acceptance_criteria` / `require_edge_cases` / `require_open_questions` / `require_reproduction` | advisory | AI agent only |
| `loop.runbook` | enforced | `run_request.py` (loop template lookup), `execute_request.py` (loop artifact) |
| `loop.max_retries` / `human_gate` / `checkpoint` | enforced | `execute_request.py` (loop artifact and run log) |
| `loop.token_budget` / `wall_time_budget` / `cost_budget` / `failure_budget` | enforced (optional) | `execute_request.py`; presets omit them on purpose — they default to `TBD` in the loop artifact for the AI/human to fill, because budget policy is project-specific |
| `verify.*` (`native_tests`, `require_build`, `require_diff_coverage`, `require_design_diagram`, `require_security_scan`, `semgrep_config`, `severity`, `require_regression_tests`, `require_failing_test_or_trace`, `require_manual_validation`, `require_link_check`, `require_source_consistency`) | enforced | `execute_request.py` (`required_verify_checks` and the verification gate) |
| `memory.*` (`local_memory`, `write_pitfalls`, `tags`) | advisory | AI agent only (echoed into the memory plan) |

Requirement paths may be absolute, relative to your current shell directory, or relative to the target project.
External requirement files are copied into the target project before `current-request.md` is executed.

## Included Presets

| Preset | Use |
|---|---|
| `feature-low` | Small low-risk feature |
| `feature-medium` | Default feature work |
| `feature-high` | Critical feature with human gates |
| `bugfix-medium` | Default bugfix with reproduction/verification |
| `refactor-medium` | Behavior-preserving refactor |
| `migration-high` | High-risk migration with rollback |
| `docs-low` | Documentation-only work |
| `verify-medium` | PR/change verification |
| `memory-low` | Memory organization/update |
