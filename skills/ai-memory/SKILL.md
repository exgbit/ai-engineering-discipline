---
name: ai-memory
description: "Memory step for AI engineering discipline. Use to persist project rules, module boundaries, pitfalls, requirement indexes, and durable agent memory. Default framework: Mem0 plus local docs/memory."
---

# AI Memory

Use Mem0 as the default programmatic memory framework when cross-session or cross-agent memory is needed.

Install:

```bash
python -m pip install --user mem0ai
```

For normal repositories, write local Markdown memory first:

- `docs/memory/project-rules.md`
- `docs/memory/module-map.md`
- `docs/memory/pitfalls.md`
- `docs/memory/project-scan.md`
- `docs/specs/requirements-index.md`

Only write evidence-backed memory. Do not invent history.
