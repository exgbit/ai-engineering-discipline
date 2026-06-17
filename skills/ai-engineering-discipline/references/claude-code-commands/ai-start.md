# AI Engineering Start

Initialize and inspect this repository for the Spec / Loop / Verify / Memory workflow.

From the repository root, first check that this file exists:

```text
.claude/skills/ai-engineering-discipline/scripts/init_project.py
```

If it does not exist, stop and tell the user to run the framework bootstrap script first.

If it exists, run:

```bash
set -e
if command -v python3 >/dev/null 2>&1; then PYTHON=python3; else PYTHON=python; fi
"$PYTHON" .claude/skills/ai-engineering-discipline/scripts/init_project.py .
"$PYTHON" .claude/skills/ai-engineering-discipline/scripts/inspect_project.py .
"$PYTHON" .claude/skills/ai-engineering-discipline/scripts/doctor.py .
```

Then read:

- `docs/AI_ENGINEERING_START_HERE.md`
- `docs/memory/project-scan.md`
- `docs/ai-engineering/doctor-report.md`
- `CLAUDE.md`

Summarize doctor failures first, then detected stack, candidate verification commands, and the next managed-request command the user should run. Do not modify business code.
