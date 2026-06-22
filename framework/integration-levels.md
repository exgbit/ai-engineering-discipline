# Tool Names and What They Mean

This project is an independent AI coding workflow framework. It is not affiliated with, endorsed by, or officially maintained by GitHub Spec Kit, LangGraph, Semgrep, or Mem0. Project names and trademarks belong to their respective owners.

The Spec / Loop / Memory steps are implemented entirely by the framework's own Markdown templates plus the AI agent. The named open-source tools are only stylistic references — the framework does not call them. The only external tool it actually runs is Semgrep, in the Verify step, and only if it is installed.

| Layer | Tool name | Called at runtime? | Need to install? |
|---|---|---|---|
| Spec | GitHub Spec Kit | No — style reference only | No |
| Loop | LangGraph | No — style reference only | No |
| Verify | Semgrep | Yes — runs `semgrep scan` as the security gate | Optional (skipped if absent) |
| Memory | Mem0 | No — style reference only | No |

## Verification Policy

- Core workflow artifacts stay usable even with no external tool installed.
- The one runtime tool (Semgrep) fails closed: if it is missing, fails, times out, or emits unparsable output, the scan is reported as `uncovered` or `blocked`, never silently successful.

## Release Wording

Recommended wording for public release:

> AI Engineering Discipline is an independent workflow framework that organizes AI coding around four engineering controls: Spec, Loop, Verify, and Memory. It runs on its own Markdown templates plus your AI agent; the only external tool it calls is Semgrep, as an optional security-scan gate. It is not affiliated with GitHub Spec Kit, LangGraph, or Mem0, and it does not call or require them.
