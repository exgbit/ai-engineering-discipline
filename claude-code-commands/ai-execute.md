# AI Engineering Execute

Execute the current managed request safely.

Optional arguments are passed to the executor, for example:

```text
/ai-execute --run-native-checks
/ai-execute --run-semgrep --run-native-checks
```

From the repository root, first check that this file exists:

```text
.claude/skills/ai-engineering-discipline/scripts/execute_request.py
```

If it does not exist, stop and tell the user to run the framework bootstrap script first.

If it exists, run:

```bash
if command -v python3 >/dev/null 2>&1; then PYTHON=python3; else PYTHON=python; fi
"$PYTHON" .claude/skills/ai-engineering-discipline/scripts/execute_request.py . $ARGUMENTS
```

Read:

- `docs/ai-engineering/execution-report.md`
- `docs/specs/`
- `docs/loops/`
- `docs/verify/current-request-verify.md`
- `docs/memory/current-request-memory.md`

If verification flags were used, also read `docs/verify/verification-results.json` and `docs/verify/verification-results.md`. Report what was generated, what verification ran, and what remains blocked.

If the command exits non-zero, still read `docs/ai-engineering/execution-report.md`; it may contain a generated blocked report with the next `/ai-request` command.
