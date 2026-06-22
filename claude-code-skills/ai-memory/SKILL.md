---
name: ai-memory
description: "Memory step for AI engineering discipline. Use when Claude Code needs to persist project rules, module boundaries, pitfalls, decisions, requirement indexes, and agent memory after or before AI-assisted development."
---

# AI Memory

## How This Step Works

This step is implemented by the framework itself — no external tool is called. Memory lives as durable Markdown in `docs/memory/`; you (the agent) write real, evidence-backed entries there:

```text
docs/memory/project-rules.md
docs/memory/module-map.md
docs/memory/pitfalls.md
docs/memory/project-scan.md
docs/specs/requirements-index.md
```

## Existing Requirement Docs

When requirements already exist:

1. Build `docs/specs/requirements-index.md`.
2. Record source docs, feature names, owners, and status.
3. Link specs back to original source docs.
4. Do not delete or rewrite source requirements.

## Output

Update memory only with real, evidence-backed information:

- project rules;
- module boundaries;
- repeated pitfalls;
- decisions or ADR links;
- source requirement index;
- reusable loop lessons.

Do not invent history.
