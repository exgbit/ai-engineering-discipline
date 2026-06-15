---
name: ai-verify
description: "Verify step for AI engineering discipline. Use to prove AI-generated code with tests, lint, build, static analysis, security checks, and PR evidence. Default framework: Semgrep plus native tests."
---

# AI Verify

Use Semgrep as the default cross-language static analysis framework.

Install/run:

```bash
python -m pip install --user semgrep
semgrep scan --config auto --json .
```

Always add native project checks when available: `npm test`, `pytest`, `go test ./...`, `cargo test`, `mvn test`, lint, typecheck, build.

For prewritten requirements, update `docs/verify/test-matrix.md` and map each acceptance criterion to evidence.

Output commands, results, unrun checks, and residual risk.
