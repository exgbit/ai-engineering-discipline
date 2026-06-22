---
name: ai-loop
description: "Loop step for AI engineering discipline. Use to run feature, bugfix, refactor, migration, or docs work through controlled loops."
---

# AI Loop

This step is implemented by the framework itself — no external tool is called. The orchestrator generates a Markdown loop runbook in `docs/loops/`; you (the agent) follow it.

Every loop must define:

- state model;
- scope;
- verify gates;
- retry budget;
- success exit;
- failure exit;
- escalation path;
- memory writes.

Use the existing requirement specs to choose the loop: bugfix, feature-slice, migration, refactor, or docs.
