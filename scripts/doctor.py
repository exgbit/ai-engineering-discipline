#!/usr/bin/env python3
"""Diagnose a target project's AI Engineering Discipline installation."""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from dataclasses import dataclass
from pathlib import Path


GENERATED = "<!-- ai-engineering:generated -->"


@dataclass
class Check:
    status: str
    item: str
    detail: str


def file_check(target: Path, rel_path: str, required: bool = True) -> Check:
    path = target / rel_path
    if path.is_file():
        return Check("ok", rel_path, "file exists")
    return Check("fail" if required else "warn", rel_path, "missing file")


def dir_check(target: Path, rel_path: str, required: bool = True) -> Check:
    path = target / rel_path
    if path.is_dir():
        return Check("ok", rel_path, "directory exists")
    return Check("fail" if required else "warn", rel_path, "missing directory")


def skill_check(target: Path, rel_path: str, required: bool = True) -> Check:
    path = target / rel_path / "SKILL.md"
    if path.is_file():
        return Check("ok", rel_path, "skill found")
    return Check("fail" if required else "warn", rel_path, "missing SKILL.md")


def skill_script_check(target: Path, script_name: str) -> Check:
    rel_path = f".claude/skills/ai-engineering-discipline/scripts/{script_name}"
    path = target / rel_path
    if path.is_file():
        return Check("ok", rel_path, "script found")
    return Check("fail", rel_path, "missing script")


def command_check(target: Path, name: str) -> Check:
    rel_path = f".claude/commands/{name}.md"
    path = target / rel_path
    if path.is_file():
        return Check("ok", rel_path, "slash command found")
    return Check("fail", rel_path, "missing slash command")


def command_content_check(target: Path, name: str, required_text: str) -> Check:
    rel_path = f".claude/commands/{name}.md"
    path = target / rel_path
    item = f"{rel_path} contains {required_text!r}"
    if not path.is_file():
        return Check("fail", item, "missing slash command")
    content = path.read_text(encoding="utf-8", errors="ignore")
    if required_text in content:
        return Check("ok", item, "current command content")
    return Check("warn", item, f"missing expected text: {required_text}")


def mcp_impact_check(target: Path) -> Check:
    """可选:代码知识图谱 MCP 是否配置(给 agent 做影响分析用)。永不 fail——它是可选增强,
    没配只回退到手填影响分析,不算安装问题。"""
    import json
    import shutil
    item = "knowledge-graph MCP (impact analysis)"
    for cfg in (target / ".mcp.json", target / ".claude" / "mcp.json"):
        if not cfg.is_file():
            continue
        try:
            data = json.loads(cfg.read_text(encoding="utf-8", errors="ignore"))
        except (OSError, ValueError):
            continue
        servers = data.get("mcpServers") or data.get("servers") or {}
        if isinstance(servers, dict) and any(
            "memory" in str(name).lower() or "graph" in str(name).lower() for name in servers
        ):
            return Check("ok", item, "MCP configured — graph-driven impact analysis available")
    if shutil.which("codebase-memory-mcp") or shutil.which("codebase-memory"):
        return Check("ok", item, "binary on PATH — graph-driven impact analysis available")
    return Check("warn", item, "optional; not configured — impact analysis is hand-filled (not a problem)")


def collect_checks(target: Path) -> list[Check]:
    checks = [
        Check("ok", "python", f"{sys.executable} ({sys.version.split()[0]})"),
        file_check(target, ".ai-discipline.json", required=False),
        file_check(target, "CLAUDE.md"),
        file_check(target, "AGENTS.md"),
        file_check(target, "docs/AI_ENGINEERING_START_HERE.md"),
        file_check(target, ".github/pull_request_template.md"),
        file_check(target, ".github/workflows/ai-discipline.yml", required=False),
        dir_check(target, "docs/specs"),
        dir_check(target, "docs/verify"),
        dir_check(target, "docs/memory"),
        dir_check(target, "docs/loops"),
        skill_check(target, ".claude/skills/ai-engineering-discipline"),
        skill_check(target, ".claude/skills/ai-spec"),
        skill_check(target, ".claude/skills/ai-loop"),
        skill_check(target, ".claude/skills/ai-verify"),
        skill_check(target, ".claude/skills/ai-memory"),
        skill_check(target, ".codex/skills/ai-engineering-discipline", required=False),
        skill_script_check(target, "init_project.py"),
        skill_script_check(target, "ai_discipline.py"),
        skill_script_check(target, "inspect_project.py"),
        skill_script_check(target, "run_request.py"),
        skill_script_check(target, "execute_request.py"),
        skill_script_check(target, "doctor.py"),
        skill_script_check(target, "install_default_adapters.py"),
        command_check(target, "ai-start"),
        command_check(target, "ai-build"),
        command_check(target, "ai-request"),
        command_check(target, "ai-execute"),
        command_check(target, "ai-verify"),
        command_check(target, "ai-doctor"),
        command_content_check(target, "ai-start", "PYTHON=python3"),
        command_content_check(target, "ai-start", "set -e"),
        command_content_check(target, "ai-request", "PYTHON=python3"),
        command_content_check(target, "ai-request", "set -e"),
        command_content_check(target, "ai-execute", "PYTHON=python3"),
        command_content_check(target, "ai-execute", "set -e"),
        command_content_check(target, "ai-verify", "PYTHON=python3"),
        command_content_check(target, "ai-verify", "set -e"),
        command_content_check(target, "ai-doctor", "doctor-report.md"),
        command_content_check(target, "ai-doctor", "set -e"),
        file_check(target, "docs/ai-engineering/current-request.md", required=False),
        file_check(target, "docs/adapters/default-stack.md", required=False),
        file_check(target, "docs/memory/project-scan.md", required=False),
        mcp_impact_check(target),
    ]
    return checks


def render_report(target: Path, checks: list[Check]) -> str:
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    failures = sum(1 for item in checks if item.status == "fail")
    warnings = sum(1 for item in checks if item.status == "warn")
    lines = [
        "# AI Engineering Doctor Report",
        "",
        f"Created: {now}",
        f"Target: `{target}`",
        "",
        "## Summary",
        "",
        f"- Failures: `{failures}`",
        f"- Warnings: `{warnings}`",
        "",
        "| Status | Item | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check.status} | `{check.item}` | {check.detail} |")

    lines.extend([
        "",
        "## Recommended Fixes",
        "",
    ])
    if failures:
        lines.append("- Re-run the framework bootstrap from the framework repository with `--force` if generated framework files are stale or missing.")
        lines.append("- If only `.claude/commands` are missing, reinstall from `claude-code-commands/` or rerun bootstrap.")
        lines.append("- If `.claude/skills` are missing, rerun bootstrap instead of copying command files manually.")
    else:
        lines.append("- No blocking installation issue detected.")
    if warnings:
        lines.append("- Warnings are usually optional context, but `current-request.md` is required before `/ai-execute` or `/ai-verify` can do useful work.")
        lines.append("- If a command content check warns, rerun bootstrap or `init_project.py . --force` to refresh `.claude/commands`.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", nargs="?", default=".", help="Target project path.")
    parser.add_argument("--fail-on-error", action="store_true", help="Exit non-zero when required checks fail.")
    args = parser.parse_args()

    target = Path(args.target).expanduser().resolve()
    if not target.exists() or not target.is_dir():
        raise SystemExit(f"Target project does not exist: {target}")

    checks = collect_checks(target)
    report = render_report(target, checks)
    print(report.rstrip())
    print()
    # 诊断默认不污染未初始化的项目:仅当 docs/ 已存在(项目已 init)时才落地报告
    if (target / "docs").is_dir():
        report_path = target / "docs" / "ai-engineering" / "doctor-report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(GENERATED + "\n" + report, encoding="utf-8")
        print(f"wrote: {report_path}")
    else:
        print("(skip report: docs/ not found; run init first)")

    if args.fail_on_error and any(item.status == "fail" for item in checks):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
