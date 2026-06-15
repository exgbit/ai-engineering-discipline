---
name: ai-verify
description: "Verify step for AI engineering discipline. Use when Claude Code needs to prove AI-generated code is correct with tests, lint, build, static analysis, security checks, PR evidence, or CI gates. Default framework: Semgrep plus native project tests."
---

# AI Verify

## Default Framework

Use Semgrep as the default cross-language static analysis framework.

Repository: https://github.com/semgrep/semgrep

Install:

```bash
python -m pip install --user semgrep
```

Run:

```bash
semgrep scan --config auto
```

## Required Native Verification

Semgrep is not enough by itself. Always add project-native commands when available:

- Node: `npm test`, `npm run lint`, `npm run build`, `npm run typecheck`
- Python: `pytest`, `ruff check .`, `mypy .`
- Go: `go test ./...`, `go vet ./...`
- Rust: `cargo test`, `cargo clippy`
- Java: `mvn test` or `./gradlew test`

## Existing Requirement Docs

If requirements were prewritten, verify against their acceptance criteria:

1. Map each requirement to a test or manual validation.
2. Update `docs/verify/test-matrix.md`.
3. Run the narrowest useful checks first.
4. Run broader regression checks before PR.

## Output

Produce PR-ready evidence:

- commands run;
- pass/fail results;
- unrun checks and why;
- residual risks;
- requirement-to-test mapping.

Generated explanations are not verification evidence.
