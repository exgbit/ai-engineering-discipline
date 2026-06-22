# Adapters

The framework needs no external tools to run. The only optional one is **Semgrep**, the security-scan gate in the Verify step.

| Layer | External tool | Called by the framework? | Need to install? |
|---|---|---|---|
| Spec | GitHub Spec Kit | No — style reference only | No |
| Loop | LangGraph | No — style reference only | No |
| Verify | Semgrep | Yes — security-scan gate | Optional (skipped if absent) |
| Memory | Mem0 | No — style reference only | No |

Spec / Loop / Memory are implemented by the framework's own Markdown templates plus the AI agent — the named tools are only stylistic references and are never called. The control plane is:

```text
Spec -> Loop -> Verify -> Memory
```

Only Verify optionally calls Semgrep; `default-stack.json` describes that one optional tool.
