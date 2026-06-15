# Adapter Stack

This directory defines the default open-source framework choices for each layer:

| Layer | Default Framework | Repository |
|---|---|---|
| Spec | GitHub Spec Kit | https://github.com/github/spec-kit |
| Loop | LangGraph | https://github.com/langchain-ai/langgraph |
| Verify | Semgrep | https://github.com/semgrep/semgrep |
| Memory | Mem0 | https://github.com/mem0ai/mem0 |

These are defaults, not permanent lock-in. The control plane remains:

```text
Spec -> Loop -> Verify -> Memory
```

The frameworks are replaceable adapters below that control plane.
