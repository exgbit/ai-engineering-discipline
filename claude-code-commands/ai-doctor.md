# AI Engineering Doctor

Diagnose the Claude Code installation for the Spec / Loop / Verify / Memory workflow.

From the repository root, first check that this file exists:

```text
.claude/skills/ai-engineering-discipline/scripts/doctor.py
```

If it does not exist, stop and tell the user to run the framework bootstrap script first.

If it exists, run:

```bash
if command -v python3 >/dev/null 2>&1; then PYTHON=python3; else PYTHON=python; fi
"$PYTHON" .claude/skills/ai-engineering-discipline/scripts/doctor.py . $ARGUMENTS
```

Read `docs/ai-engineering/doctor-report.md`. Summarize failures first, then warnings, then the next concrete fix. Do not modify business code.
