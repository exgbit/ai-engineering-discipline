---
name: ai-spec
description: "Spec step for AI engineering discipline. Use when Claude Code needs to turn a request, issue, PRD, existing requirement document, product doc, API contract, or design note into actionable specs before coding. Default framework: GitHub Spec Kit."
---

# AI Spec

## Default Framework

Use GitHub Spec Kit as the default Spec framework.

Repository: https://github.com/github/spec-kit

Primary commands after Spec Kit is installed:

```bash
specify init . --integration claude --force
```

Then in Claude Code, prefer Spec Kit commands when available:

```text
/speckit.constitution
/speckit.specify
/speckit.plan
/speckit.tasks
/speckit.implement
```

## If Requirements Already Exist

Do not ask the user to rewrite them. Import them.

Workflow:

1. Find requirement docs: `docs/`, `requirements/`, `prd/`, `product/`, `specs/`, `*.md`, `*.docx`, `*.pdf` if text is available.
2. Create `docs/specs/requirements-index.md` listing source docs and feature names.
3. For each feature, create or update `docs/specs/<feature>.md` using `docs/specs/spec-template.md`.
4. Preserve original wording for business rules and acceptance criteria.
5. Mark unclear items as open questions instead of guessing.
6. If Spec Kit is installed, use `/speckit.specify` to convert the selected feature into Spec Kit artifacts.

## Output

Produce:

- a spec file;
- acceptance criteria;
- non-goals;
- edge cases;
- test plan mapping requirements to verify gates;
- open questions if requirements are incomplete.

Do not implement code in this step.
