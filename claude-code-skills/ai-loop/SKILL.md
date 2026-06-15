---
name: ai-loop
description: "Loop step for AI engineering discipline. Use when Claude Code needs to execute a feature, bugfix, refactor, migration, or docs task through a controlled agent loop with states, retry policy, exit conditions, and human escalation. Default framework: LangGraph."
---

# AI Loop

## Default Framework

Use LangGraph as the default Loop framework when a programmable agent state machine is needed.

Repository: https://github.com/langchain-ai/langgraph

Install:

```bash
python -m pip install --user langgraph
```

Minimal loop concept:

```text
load_context -> plan -> implement_small_step -> verify -> retry_or_escalate -> memory_update -> done
```

## Practical Use

For normal Claude Code project work, start with Markdown runbooks in `docs/loops/`.

Use LangGraph when:

- the loop must run repeatedly;
- multiple states or branches are needed;
- retry and escalation policy must be explicit;
- the loop should later become a service or CI workflow.

## Existing Requirement Docs

If specs were generated from existing requirement docs, select a loop per feature:

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
