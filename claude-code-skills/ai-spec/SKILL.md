---
name: ai-spec
description: "Spec step for AI engineering discipline. Use when Claude Code needs to turn a request, issue, PRD, existing requirement document, product doc, API contract, or design note into actionable specs before coding."
---

# AI Spec

## How This Step Works

This step is implemented by the framework itself — no external tool is called. The orchestrator generates a spec from `docs/specs/spec-template.md`; you (the agent) read the current code and fill it in with real requirements, impact analysis, acceptance criteria, and a test plan.

## If Requirements Already Exist

Do not ask the user to rewrite them. Import them.

Workflow:

1. Find requirement docs: `docs/`, `requirements/`, `prd/`, `product/`, `specs/`, `*.md`, `*.docx`, `*.pdf` if text is available, plus images/diagrams you can read visually.
2. Create `docs/specs/requirements-index.md` listing source docs and feature names.
3. For each feature, create or update `docs/specs/<feature>.md` using `docs/specs/spec-template.md`.
4. Preserve original wording for business rules and acceptance criteria.
5. Mark unclear items as open questions instead of guessing.

## Output

Produce:

- a spec file;
- acceptance criteria;
- non-goals;
- edge cases;
- test plan mapping requirements to verify gates;
- open questions if requirements are incomplete.

Do not implement code in this step.
