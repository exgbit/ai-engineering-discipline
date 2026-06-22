# Existing Requirements Workflow

Use this workflow when the project already has PRDs, feature docs, design docs, customer requirement docs, or issue lists.

## Goal

Do not ask humans to rewrite existing requirements. Convert existing documents into the framework flow:

```text
Existing docs -> ai-spec -> ai-loop -> ai-verify -> ai-memory
```

## Step 1: ai-spec

Input:

- `docs/`
- `requirements/`
- `prd/`
- `product/`
- issue exports;
- design docs;
- API docs.

Actions:

1. Create `docs/specs/requirements-index.md`.
2. List every source document, feature, owner, and status.
3. Create one `docs/specs/<feature>.md` per feature.
4. Preserve source wording for business rules and acceptance criteria.
5. Mark unclear items as open questions.

## Step 2: ai-loop

Choose a loop per feature:

- bug: `bugfix-loop`;
- new feature: `feature-slice-loop`;
- migration: `migration-loop`;
- refactor: `refactor-loop`;
- docs only: `docs-loop`.

## Step 3: ai-verify

Build `docs/verify/test-matrix.md` from the imported requirements:

| Requirement | Verification |
|---|---|
| business rule | unit/integration/manual evidence |
| API behavior | contract/API test |
| UI behavior | E2E/manual screenshot |
| security rule | Semgrep/native security check |

## Step 4: ai-memory

Persist durable context:

- source docs and feature index;
- project rules found in requirements;
- module ownership if stated;
- pitfalls only if supported by evidence.

## Claude Prompt

```text
Use ai-spec to import existing requirement documents into docs/specs/.
Then use ai-loop to select the first implementation loop.
Do not write code until the spec and loop are ready.
```
