---
name: ai-spec
description: "Spec step for AI engineering discipline. Use to convert requests, issues, PRDs, existing requirement documents, product docs, or design notes into actionable specs before coding. Default framework: GitHub Spec Kit."
---

# AI Spec

Use GitHub Spec Kit as the default framework.

Install/init:

```bash
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git
specify init . --integration codex --integration-options="--skills" --force
```

If requirements already exist, import them instead of asking the user to rewrite:

1. Find source requirement docs.
2. Create `docs/specs/requirements-index.md`.
3. Create one `docs/specs/<feature>.md` per feature using `docs/specs/spec-template.md`.
4. Preserve business rules and acceptance criteria.
5. Mark unclear items as open questions.

Do not implement code during this step.
