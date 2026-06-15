---
name: ai-loop
description: "Loop step for AI engineering discipline. Use to run feature, bugfix, refactor, migration, or docs work through controlled loops. Default framework: LangGraph."
---

# AI Loop

Use LangGraph as the default programmable loop framework.

Install:

```bash
python -m pip install --user langgraph
```

For normal project work, start with Markdown loop runbooks in `docs/loops/`.

Every loop must define:

- state model;
- scope;
- verify gates;
- retry budget;
- success exit;
- failure exit;
- escalation path;
- memory writes.

Use existing requirement specs to choose the loop: bugfix, feature-slice, migration, refactor, or docs.
