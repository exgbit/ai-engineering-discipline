---
name: ai-memory
description: "Memory step for AI engineering discipline. Use when Claude Code needs to persist project rules, module boundaries, pitfalls, decisions, requirement indexes, and agent memory after or before AI-assisted development. Default framework: Mem0 plus local docs/memory."
---

# AI Memory

## Default Framework

Use Mem0 as the default agent memory framework when durable programmatic memory is needed.

Repository: https://github.com/mem0ai/mem0

Install:

```bash
python -m pip install --user mem0ai
```

## Local Memory Comes First

For a normal code repository, write durable Markdown memory first:

```text
docs/memory/project-rules.md
docs/memory/module-map.md
docs/memory/pitfalls.md
docs/memory/project-scan.md
docs/specs/requirements-index.md
```

Use Mem0 when memory must be queried across sessions, agents, or repositories.

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
