# Integrated Workflow

This framework is designed so users do not need to learn or install Spec Kit, LangGraph, or Mem0 at all. The only optional external tool is Semgrep (the security scan).

The Claude Code user-facing interface is one managed request through slash commands:

```text
/ai-request --task feature --name "refund approval" --requirements docs/requirements/refund.md --risk medium
/ai-execute
```

Equivalent script command:

```bash
python .claude/skills/ai-engineering-discipline/scripts/run_request.py . \
  --task feature \
  --name "refund approval" \
  --requirements docs/requirements/refund.md \
  --risk medium
```

Internally, the framework routes work through four steps, all implemented by its own Markdown templates plus the AI agent:

```text
Spec   -> ai-spec   -> framework's own spec template (filled by the agent)
Loop   -> ai-loop   -> framework's own loop runbook
Verify -> ai-verify -> native tests + optional Semgrep security scan
Memory -> ai-memory -> local docs/memory
```

Only the Verify step calls an external tool (Semgrep), and only if it is installed — otherwise the scan is reported as skipped, not failed. No other external tool is called or needed. (The Spec / Loop / Memory templates take stylistic inspiration from GitHub Spec Kit, LangGraph, and Mem0, but the framework does not run those tools and you do not need to install them.)

## What This Framework Adds

Doing disciplined AI engineering by hand requires deciding:

- when requirements should become a spec;
- how the spec hands off to implementation;
- when a task needs a structured loop versus a simple runbook;
- how the security scan fits with tests, lint, build, and CI;
- when to write durable memory versus throwaway notes;
- how evidence and memory flow across steps.

This framework owns those decisions. The user asks for a development task; the orchestrator runs the steps and keeps the artifacts connected.

## Preset Resolver

Users should not provide low-level framework parameters. They provide intent:

```text
task + risk + requirement path + optional execution flag
```

The preset resolver expands this into framework parameters:

```text
feature + medium
  -> spec:   mode=feature, acceptance criteria required
  -> loop:   runbook=feature-slice-loop, max_retries=2, human_gate=on_verify_failure
  -> verify: Semgrep config=auto (only if installed), severity=warning, native_tests=true, require_build=true
  -> memory: local docs/memory tags=[feature, medium-risk]
```

Resolved parameters are written to:

```text
docs/ai-engineering/current-request.md
```

## Default User Flow

1. Install the framework into a target project.
2. Open Claude Code or Codex in that project.
3. In Claude Code, run `/ai-start`.
4. Create a managed request with `/ai-request`.
5. Generate safe artifacts with `/ai-execute`.
6. Run explicit verification with `/ai-verify` when needed.

Equivalent command:

```bash
python .claude/skills/ai-engineering-discipline/scripts/run_request.py . \
  --task feature \
  --name "my feature" \
  --requirements docs/requirements/my-feature.md \
  --risk medium
```

## Existing Requirements

If requirements already exist, the user should not rewrite them.

Claude Code command:

```text
/ai-request --task feature --name "first feature" --requirements docs/requirements --risk medium
/ai-execute
```

Equivalent script command:

```bash
python .claude/skills/ai-engineering-discipline/scripts/run_request.py . \
  --task feature \
  --name "first feature" \
  --requirements docs/requirements \
  --risk medium
```

Expected artifacts:

```text
docs/specs/requirements-index.md
docs/specs/<feature>.md
docs/loops/<selected-loop>.md
docs/verify/test-matrix.md
docs/memory/project-rules.md
```

## Daily Commands

New feature:

```text
/ai-request --task feature --name "<feature-name>" --requirements docs/requirements/<feature>.md --risk medium
/ai-execute
```

Bug fix:

```text
/ai-request --task bugfix --name "<bug-name>" --requirements docs/requirements/<bug>.md --risk medium
/ai-execute
```

PR validation:

```text
/ai-request --task verify --name "pr validation" --risk medium
/ai-verify
```

Memory update:

```text
/ai-request --task memory --name "memory update" --risk low
/ai-execute
```

## Rule

Most users should not call `ai-spec`, `ai-loop`, `ai-verify`, or `ai-memory` directly. Those are internal step skills used by the orchestrator.
