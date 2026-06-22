---
name: ai-loop
description: "Loop step for AI engineering discipline. Use when Claude Code needs to execute a feature, bugfix, refactor, migration, or docs task through a controlled agent loop with states, retry policy, exit conditions, and human escalation."
---

# AI Loop

## How This Step Works

This step is implemented by the framework itself — no external tool is called. The orchestrator generates a Markdown loop runbook in `docs/loops/`; you (the agent) follow it. The loop shape is:

```text
load_context -> plan -> implement_small_step -> verify -> retry_or_escalate -> memory_update -> done
```

## Selecting a Loop

For normal project work, follow the Markdown runbook in `docs/loops/`. Pick or create one per task type:

- bug or defect: `docs/loops/bugfix-loop.md`;
- new feature: create `docs/loops/feature-slice-loop.md`;
- migration: create `docs/loops/migration-loop.md`;
- refactor: create `docs/loops/refactor-loop.md`.

## Output

Produce or update a loop runbook with:

- scope;
- state model;
- verify gates;
- success exit;
- failure exit;
- retry budget;
- escalation path;
- memory writes.
