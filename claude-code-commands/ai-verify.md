# AI Engineering Verify

Run explicit verification for the current managed request and write structured evidence.

From the repository root, first check that this file exists:

```text
.claude/skills/ai-engineering-discipline/scripts/execute_request.py
```

If it does not exist, stop and tell the user to run the framework bootstrap script first.

If it exists, run this default command:

```bash
if command -v python3 >/dev/null 2>&1; then PYTHON=python3; else PYTHON=python; fi
"$PYTHON" .claude/skills/ai-engineering-discipline/scripts/execute_request.py . --run-native-checks --run-semgrep $ARGUMENTS
```

Use `--fail-on-verify-failure` only when the user wants a non-zero exit after results are written.

After running, read:

- `docs/verify/verification-results.json`
- `docs/verify/verification-results.md`
- `docs/verify/test-matrix.md`

Summarize pass/fail/skipped checks, residual risk, and whether implementation or PR review can proceed.
