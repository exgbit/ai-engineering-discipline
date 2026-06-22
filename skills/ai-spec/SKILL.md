---
name: ai-spec
description: "Spec step for AI engineering discipline. Use to convert requests, issues, PRDs, existing requirement documents, product docs, or design notes into actionable specs before coding."
---

# AI Spec

This step is implemented by the framework itself — no external tool is called. The orchestrator generates a spec from `docs/specs/spec-template.md`; you (the agent) read the current code and fill it in with real requirements, impact analysis, acceptance criteria, and a test plan.

If requirements already exist, import them instead of asking the user to rewrite:

1. Find source requirement docs (and images/diagrams you can read visually).
2. Create `docs/specs/requirements-index.md`.
3. Create one `docs/specs/<feature>.md` per feature using `docs/specs/spec-template.md`.
4. Preserve business rules and acceptance criteria.
5. Mark unclear items as open questions.

Do not implement code during this step.
