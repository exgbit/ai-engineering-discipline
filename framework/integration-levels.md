# Integration Levels

This project is an independent AI coding workflow framework. It is not affiliated with, endorsed by, or officially maintained by GitHub Spec Kit, LangGraph, Semgrep, or Mem0. Project names and trademarks belong to their respective owners.

The framework uses these projects as default adapter targets for the Spec / Loop / Verify / Memory model. Integration depth is intentionally explicit:

| Layer | Default framework | Current level | What works today | Compatibility risk |
|---|---|---|---|---|
| Spec | GitHub Spec Kit | Artifact-compatible | Generates spec artifacts and request contracts aligned with spec-driven development. | Low until CLI integration is enabled. |
| Loop | LangGraph | Runbook-compatible | Generates loop runbooks and `docs/loops/current-loop-run.md` state evidence. | Low until runtime graph integration is enabled. |
| Verify | Semgrep | Runtime-integrated | Runs `semgrep scan --config <config> --json .`, parses results, and blocks unsafe verification states. | Medium because CLI or JSON output can change. |
| Memory | Mem0 | Local-memory-first | Generates local memory plans and `docs/memory/memory-candidates.md` for review before durable writes. | Low until SDK/API sync is enabled. |

## Compatibility Policy

- Core workflow artifacts should remain usable even if an external framework changes.
- Adapter integrations must fail closed: if a required external tool is missing, fails, times out, or emits unparsable output, verification should become `pending` or `blocked`, never silently successful.
- Runtime integrations should be isolated behind adapter scripts instead of being embedded in generated project files.
- Deeper integrations should add contract tests before becoming default behavior.

## Release Wording

Recommended wording for public release:

> AI Engineering Discipline is an independent workflow framework that organizes AI coding around four engineering controls: Spec, Loop, Verify, and Memory. It uses GitHub Spec Kit, LangGraph, Semgrep, and Mem0 as default adapter targets. Semgrep is currently runtime-integrated as a verification gate; the other layers are integrated through generated artifacts, workflow contracts, and adapter metadata, with deeper CLI/runtime/API integrations planned.
