# AI Engineering Request

Create a managed AI engineering request from the provided arguments.

Usage examples:

```text
/ai-request --task feature --name "refund approval" --requirements docs/requirements/refund.md --risk medium
/ai-request --task bugfix --name "login timeout" --requirements docs/requirements/login-timeout.md
```

From the repository root, first check that this file exists:

```text
.claude/skills/ai-engineering-discipline/scripts/run_request.py
```

If it does not exist, stop and tell the user to run the framework bootstrap script first.

If it exists, run:

```bash
if command -v python3 >/dev/null 2>&1; then PYTHON=python3; else PYTHON=python; fi
"$PYTHON" .claude/skills/ai-engineering-discipline/scripts/run_request.py . $ARGUMENTS
```

Then run the safe executor:

```bash
if command -v python3 >/dev/null 2>&1; then PYTHON=python3; else PYTHON=python; fi
"$PYTHON" .claude/skills/ai-engineering-discipline/scripts/execute_request.py .
```

Read `docs/ai-engineering/current-request.md` and `docs/ai-engineering/execution-report.md`, then summarize the generated spec, loop, verify plan, and memory plan. Do not implement business code unless the request allows execution and the spec/loop are ready.
