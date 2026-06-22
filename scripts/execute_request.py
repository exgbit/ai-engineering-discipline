#!/usr/bin/env python3
"""Execute safe setup steps from docs/ai-engineering/current-request.md."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATED = "<!-- ai-engineering:generated -->"
DEFAULT_TIMEOUT_SECONDS = 600
OUTPUT_LIMIT = 12000


@dataclass
class ManagedRequest:
    path: Path
    task: str
    name: str
    execute: bool
    preset: str
    risk: str
    requirements: list[Path]
    spec_path: Path
    loop_path: Path
    verify_matrix_path: Path
    memory_path: Path
    spec_params: dict[str, object]
    loop_params: dict[str, object]
    verify_params: dict[str, object]
    memory_params: dict[str, object]


@dataclass
class CommandResult:
    name: str
    command: list[str]
    status: str
    exit_code: int | None
    duration_seconds: float
    stdout: str
    stderr: str
    output_path: str | None = None


def skill_script(name: str) -> Path | None:
    candidates = [
        Path(__file__).resolve().parent / name,
        ROOT / "skills" / "ai-engineering-discipline" / "scripts" / name,
        ROOT / "scripts" / name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def slugify(value: str) -> str:
    result = []
    previous_dash = False
    for char in value.lower():
        if char.isalnum():
            result.append(char)
            previous_dash = False
        elif not previous_dash:
            result.append("-")
            previous_dash = True
    return "".join(result).strip("-") or "request"


def path_is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def extract_section(text: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\s*$([\s\S]*?)(?=^## |\Z)"
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def extract_json_block(text: str, heading: str) -> dict[str, object]:
    pattern = rf"^### {re.escape(heading)}\s*```json\s*([\s\S]*?)\s*```"
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        return {}
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        # 用 ValueError 让 main 走 blocked 降级(写 execution-report),与缺字段口径一致
        raise ValueError(f"Invalid JSON block for {heading}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON block for {heading} must be an object.")
    return value


def parse_bullet_value(section: str, label: str) -> str:
    pattern = rf"^- {re.escape(label)}:\s*`?([^`\n]+)`?\s*$"
    match = re.search(pattern, section, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def target_project_path(target: Path, raw: str, label: str) -> Path:
    target_root = target.resolve()
    path = Path(raw).expanduser()
    candidate = path if path.is_absolute() else target_root / path
    candidate = candidate.resolve()
    if candidate != target_root and not path_is_relative_to(candidate, target_root):
        raise SystemExit(f"{label} must stay inside target project: {candidate}")
    return candidate


def parse_bullet_paths(section: str, target: Path) -> list[Path]:
    paths: list[Path] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- ") or stripped == "- None":
            continue
        match = re.match(r"^- `([^`]+)`$", stripped)
        if match:
            paths.append(target_project_path(target, match.group(1), "Requirement source"))
        else:
            # 不静默丢弃:格式不规范的需求行(如缺反引号)给出告警
            print(f"warning: 忽略格式不规范的需求行(应为 - `path`): {stripped}", file=sys.stderr)
    return paths


def target_artifact_path(target: Path, raw: str, label: str) -> Path:
    return target_project_path(target, raw, f"{label} artifact")


def parse_request(target: Path, request_path: Path) -> ManagedRequest:
    if not request_path.exists():
        raise FileNotFoundError(f"Managed request not found: {request_path}")
    text = request_path.read_text(encoding="utf-8")
    task_section = extract_section(text, "Task")
    requirements_section = extract_section(text, "Requirement Sources")
    artifacts_section = extract_section(text, "Target Artifacts")

    def artifact(label: str, default: str) -> Path:
        raw = parse_bullet_value(artifacts_section, label) or default
        return target_artifact_path(target, raw, label)

    task = parse_bullet_value(task_section, "Type")
    name = parse_bullet_value(task_section, "Name")
    execute = parse_bullet_value(task_section, "Execute implementation now") == "true"
    preset = parse_bullet_value(task_section, "Preset")
    risk = parse_bullet_value(task_section, "Risk")
    if not task or not name:
        raise ValueError(f"Request is missing required Task fields: {request_path}")

    return ManagedRequest(
        path=request_path,
        task=task,
        name=name,
        execute=execute,
        preset=preset,
        risk=risk,
        requirements=parse_bullet_paths(requirements_section, target),
        spec_path=artifact("Spec", f"docs/specs/{slugify(name)}.md"),
        loop_path=artifact("Loop", "docs/loops/loop-template.md"),
        verify_matrix_path=artifact("Verify matrix", "docs/verify/test-matrix.md"),
        memory_path=artifact("Memory", "docs/memory"),
        spec_params=extract_json_block(text, "Spec"),
        loop_params=extract_json_block(text, "Loop"),
        verify_params=extract_json_block(text, "Verify"),
        memory_params=extract_json_block(text, "Memory"),
    )


def is_framework_placeholder(path: Path, content: str) -> bool:
    if GENERATED in content:
        return False
    rel_path = "/".join(path.parts[-3:])
    if rel_path == "docs/verify/test-matrix.md":
        return (
            "# Test Matrix Example" in content
            or (
                "| Requirement ID | Requirement | Unit Test | Integration Test | Manual / Release Check | Status |"
                in content
                and "| R1 |  |  |  |  | todo |" in content
            )
        )
    if "/docs/loops/" in "/" + "/".join(path.parts):
        return ("## Loop Name" in content and "Example:" in content) or (
            "# Bugfix Loop" in content and "Fix one well-scoped bug with reproduction" in content
        ) or (
            "# Loop Runbook Example: Bugfix Loop" in content and "Fix one well-scoped bug with test evidence" in content
        )
    return False


def safe_write(path: Path, content: str, force: bool, actions: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = GENERATED + "\n" + content.rstrip() + "\n"
    if path.exists() and not force:
        existing = path.read_text(encoding="utf-8")
        if not is_framework_placeholder(path, existing):
            reason = "generated file" if GENERATED in existing else "human file"
            actions.append(f"skip {reason}: {path}")
            return
    path.write_text(body, encoding="utf-8")
    actions.append(f"write: {path}")


def write_json_artifact(path: Path, payload: dict[str, object], actions: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"generated_by": "ai-engineering-discipline", **payload}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    actions.append(f"write: {path}")


# 图片/PDF 等非文本需求源:脚本不读其字节,内容由 Claude 在 Claude Code 中视觉识别
VISUAL_REQUIREMENT_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".pdf"}


def requirement_title(path: Path) -> str:
    if not path.exists():
        return path.name
    if path.suffix.lower() in VISUAL_REQUIREMENT_EXTS:
        return path.name
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        clean = line.strip().lstrip("#").strip()
        if clean:
            return clean[:120]
    return path.name


def requirement_excerpt(path: Path, max_chars: int = 1200) -> str:
    if not path.exists():
        return f"Missing requirement source: `{path}`"
    if path.suffix.lower() in VISUAL_REQUIREMENT_EXTS:
        return f"[Visual requirement — open and read `{path.name}` visually in Claude Code to extract its requirements.]"
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n\n[truncated by execute_request.py]"


def rel(path: Path, target: Path) -> str:
    try:
        return str(path.relative_to(target))
    except ValueError:
        return str(path)


def md_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def memory_artifact_rows(target: Path) -> str:
    rows = []
    for rel_path, purpose in [
        ("docs/memory/project-scan.md", "Detected stack, directories, and candidate commands"),
        ("docs/memory/project-rules.md", "Durable architecture and coding rules"),
        ("docs/memory/module-map.md", "Module ownership, boundaries, and coupling"),
        ("docs/memory/pitfalls.md", "Known failure patterns and regression risks"),
    ]:
        status = "found" if (target / rel_path).exists() else "missing"
        rows.append(f"| `{rel_path}` | {md_cell(purpose)} | {status} |")
    return "\n".join(rows)


def write_requirements_index(target: Path, request: ManagedRequest, force: bool, actions: list[str]) -> Path:
    index = target / "docs" / "specs" / "requirements-index.md"
    lines = [
        "# Requirements Index",
        "",
        f"Request: `{request.name}`",
        f"Preset: `{request.preset}`",
        "",
        "| Source | Imported Title | Status |",
        "|---|---|---|",
    ]
    if request.requirements:
        for source in request.requirements:
            status = "found" if source.exists() else "missing"
            lines.append(
                f"| {md_cell(f'`{rel(source, target)}`')} | {md_cell(requirement_title(source))} | {md_cell(status)} |"
            )
    else:
        lines.append("| None | No external requirement source was provided. | open |")
    safe_write(index, "\n".join(lines), force, actions)
    return index


def write_spec(target: Path, request: ManagedRequest, force: bool, actions: list[str]) -> None:
    req_rows = []
    excerpts = []
    if request.requirements:
        for idx, source in enumerate(request.requirements, start=1):
            req_id = f"R{idx}"
            title = requirement_title(source)
            req_rows.append(
                f"| {md_cell(req_id)} | {md_cell(f'Import `{rel(source, target)}`: {title}')} | "
                f"{md_cell('P0')} | {md_cell('Source reviewed and mapped to tests')} |"
            )
            excerpts.extend([
                f"### {req_id}: `{rel(source, target)}`",
                "",
                "```text",
                requirement_excerpt(source),
                "```",
                "",
            ])
    else:
        req_rows.append("| R1 | Define requirement before implementation | P0 | Requirement is explicit and testable |")
        excerpts.append("No external requirement source was provided.")

    content = f"""# Spec: {request.name}

## Problem

Define the problem from the imported requirement sources. Do not implement until open questions are resolved.

## Goal

Complete `{request.task}` work for `{request.name}` within `{request.risk or "unknown"}` risk policy.

## Non-Goals

- Do not expand scope beyond the managed request.
- Do not perform destructive operations without human approval.
- Do not treat AI explanation as verification evidence.

## Requirement Sources

{chr(10).join(f"- `{rel(source, target)}`" for source in request.requirements) if request.requirements else "- None"}

## Existing Project Baseline

Read these memory artifacts before planning changes. Treat missing files as setup gaps, not permission to guess.

| Artifact | Purpose | Status |
|---|---|---|
{memory_artifact_rows(target)}

## Imported Requirement Excerpts

{chr(10).join(excerpts)}

## Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
{chr(10).join(req_rows)}

## Design Notes

- Spec generated by ai-engineering-discipline from the request and the current code.
- Spec mode: `{request.spec_params.get("mode", request.task)}`
- Implementation should be planned in small, reviewable steps.

## Impact Analysis

Complete this before editing code in an existing project.

If a code knowledge-graph MCP is configured (the `impact` layer in `adapters/default-stack.json`, e.g. codebase-memory), fill this table from its blast radius instead of guessing: ensure the repo is indexed (`index_repository`), then run `detect_changes` (git diff -> affected symbols) and `explore` (transitive callers / depth) for this change, and list the affected interfaces / functions / callers it returns — cite the tool + symbol names as Evidence. If no such MCP is configured, fill it by reading the code (current behavior).

| Area | Impact | Evidence / Files | Risk |
|---|---|---|---|
| Affected modules | TBD | `docs/memory/module-map.md` | TBD |
| Public APIs / contracts | TBD | route, RPC, CLI, event, or package references | TBD |
| Data model / migrations | TBD | schema, migration, cache, queue, or storage references | TBD |
| Background jobs / integrations | TBD | scheduler, webhook, worker, external service references | TBD |
| Backward compatibility | Existing behavior must not regress without explicit approval. | existing tests, callers, docs | high |

## Coupling Constraints

- [ ] Identify upstream callers that depend on the changed behavior.
- [ ] Identify downstream services, modules, data stores, queues, or jobs touched by the change.
- [ ] Confirm which existing behavior must remain unchanged.
- [ ] Record any cross-module boundary change that needs human review.

## Edge Cases

- Empty or malformed input:
- Permission denied:
- Timeout / retry:
- Concurrency:
- Rollback:

## Test Plan

| Requirement ID | Test Type | Test File / Case | Status |
|---|---|---|---|
{chr(10).join(f"| R{idx} | pending | TBD | todo |" for idx, _ in enumerate(request.requirements or [Path('none')], start=1))}

## Regression Plan

Map existing behavior that could break because of this change.

| Existing Behavior | Related Module / API | Regression Check | Required |
|---|---|---|---|
| TBD | TBD | TBD | yes |

## Open Questions

{"- [ ] Confirm the imported requirements are complete and testable." if request.requirements else "- [ ] Define and import a testable requirement before implementation (no external requirement source was provided)."}
"""
    safe_write(request.spec_path, content, force, actions)


def write_loop(target: Path, request: ManagedRequest, force: bool, actions: list[str]) -> None:
    loop = request.loop_params
    content = f"""# Loop: {loop.get("runbook", request.task + "-loop")}

## Goal

Execute `{request.name}` through a bounded `{request.task}` loop.

## Inputs

- Spec: `{rel(request.spec_path, target)}`
- Request: `{rel(request.path, target)}`
- Requirement sources: {", ".join(f"`{rel(p, target)}`" for p in request.requirements) if request.requirements else "None"}
- Memory: `{rel(request.memory_path, target)}`

## Scope

Allowed:

- Update generated spec, loop, verify, and memory planning artifacts.
- Implement code only after spec and loop are accepted.
- Make one scoped change at a time, with explicit affected modules and regression checks.

Forbidden:

- Destructive operations.
- Credential, billing, permission, or production changes.
- Unverified claims of success.
- Opportunistic refactors outside the affected-module set.

Requires approval:

- Architecture changes across module boundaries.
- Backward-incompatible API, data, or event changes.
- Retrying beyond `{loop.get("max_retries", "preset")}` attempts.
- Human gate: `{loop.get("human_gate", "on_conflict")}`.

## State Model

| State | Description | Next States |
|---|---|---|
| load_context | Read request, spec, requirements, and memory | plan, stop |
| map_impact | Identify affected modules, coupling, and regression scope | plan, escalate, stop |
| plan | Produce small implementation plan | implement, stop |
| implement | Make one scoped change | verify, stop |
| verify | Run required gates and collect evidence | implement, escalate, done |
| escalate | Ask for human review | implement, stop |
| done | Produce PR evidence and memory update |  |

## Verify Gates

- [ ] Spec exists and maps requirements.
- [ ] Impact analysis names affected modules and coupling risks.
- [ ] Test matrix exists.
- [ ] Regression matrix covers existing behavior that must not break.
- [ ] Native checks run when enabled by preset.
- [ ] Semgrep runs when enabled and available.
- [ ] Memory update is evidence-backed.

## Exit Conditions

Success:

- Acceptance criteria are verified with evidence.
- Required regression checks pass or have approved waivers.
- No unresolved P0 risk remains.

Failure:

- Requirements conflict.
- Affected-module ownership or coupling is unclear.
- Verification cannot run.
- Work exceeds retry or approval policy.

## Retry Policy

- Max retries: `{loop.get("max_retries", "TBD")}`
- Checkpoint: `{loop.get("checkpoint", "TBD")}`
- What may change between retries: plan, tests, implementation details.
- What requires escalation: scope expansion, destructive work, unresolved verification.

## Budgets

Loop Engineering 要求每个 loop 有明确预算(见 framework/loop-engineering.md)。未设则填 TBD 后由负责人补。

- Token budget: `{loop.get("token_budget", "TBD")}`
- Wall-time budget: `{loop.get("wall_time_budget", "TBD")}`
- Cost budget: `{loop.get("cost_budget", "TBD")}`
- Failure budget: `{loop.get("failure_budget", "TBD")}`
"""
    safe_write(request.loop_path, content, force, actions)


def write_verify_artifacts(target: Path, request: ManagedRequest, force: bool, actions: list[str]) -> None:
    rows = []
    for idx, source in enumerate(request.requirements or [Path("none")], start=1):
        requirement = requirement_title(source) if source != Path("none") else request.name
        rows.append(
            f"| {md_cell(f'R{idx}')} | {md_cell(requirement)} | {md_cell('TBD')} | "
            f"{md_cell('TBD')} | {md_cell('TBD')} | {md_cell('todo')} |"
        )

    matrix = f"""# Test Matrix

Request: `{request.name}`
Spec: `{rel(request.spec_path, target)}`

## Requirement Traceability

| Requirement ID | Requirement | Unit Test | Integration Test | Manual / Release Check | Status |
|---|---|---|---|---|---|
{chr(10).join(rows)}

## Regression Matrix

Use this section for existing projects. Add concrete checks before implementation if the change touches coupled modules.

| Existing Behavior | Related Module / API | Regression Check | Required | Status |
|---|---|---|---|---|
| Existing behavior identified from `docs/memory/module-map.md` | TBD | TBD | yes | todo |
"""
    safe_write(request.verify_matrix_path, matrix, force, actions)

    plan = target / "docs" / "verify" / "current-request-verify.md"
    verify = request.verify_params
    content = f"""# Verify Plan: {request.name}

## Preset Policy

```json
{json.dumps(verify, ensure_ascii=False, indent=2)}
```

## Required Evidence

- Native tests: `{verify.get("native_tests", False)}`
- Build required: `{verify.get("require_build", False)}`
- Security scan: `{verify.get("require_security_scan", False)}`
- Link/source consistency: `{verify.get("require_link_check", verify.get("require_source_consistency", False))}`
- Impact analysis completed: `required`
- Regression matrix completed for affected existing behavior: `required`

## Evidence Log

- Pending. Run implementation checks after code changes.
- Pending. Fill affected modules and regression checks before implementation.
- Optional structured results: `docs/verify/verification-results.json`
- Optional readable results: `docs/verify/verification-results.md`
"""
    safe_write(plan, content, force, actions)


def write_memory_plan(target: Path, request: ManagedRequest, force: bool, actions: list[str]) -> None:
    memory_dir = request.memory_path if request.memory_path.suffix == "" else request.memory_path.parent
    path = memory_dir / "current-request-memory.md"
    content = f"""# Memory Plan: {request.name}

## Policy

```json
{json.dumps(request.memory_params, ensure_ascii=False, indent=2)}
```

## Candidate Writes

- Project rule: only if this request reveals a durable rule.
- Module map: only if ownership or dependency boundaries are confirmed.
- Pitfall: only if a real failure pattern is observed.
- Regression rule: only if this request proves a check must always run for a coupled module.

## Existing Project Update Checklist

- [ ] Update `module-map.md` if affected module boundaries or coupling changed.
- [ ] Update `project-rules.md` if the request revealed a durable implementation rule.
- [ ] Update `pitfalls.md` if verification found a repeatable failure pattern.
- [ ] Keep temporary observations in `memory-candidates.md` until reviewed.

## Evidence Required

Do not write memory from assumptions. Link to spec, PR, logs, tests, or review notes.
"""
    safe_write(path, content, force, actions)


def run_script_if_available(name: str, target: Path, actions: list[str]) -> None:
    script = skill_script(name)
    if not script:
        actions.append(f"skip missing script: {name}")
        return
    result = subprocess.run([sys.executable, str(script), str(target)], text=True, capture_output=True)
    if result.returncode == 0:
        actions.append(f"ok: {name}")
    else:
        actions.append(f"failed: {name}: {result.stderr.strip() or result.stdout.strip()}")


def truncate_output(value: str, limit: int = OUTPUT_LIMIT) -> str:
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "\n[truncated]"


def command_to_text(command: list[str]) -> str:
    return " ".join(command) if command else "none"


def required_verify_checks(request: ManagedRequest) -> list[str]:
    verify = request.verify_params
    checks: list[str] = ["impact_analysis", "regression_matrix"]
    if verify.get("native_tests"):
        checks.append("native_checks")
    if verify.get("require_build"):
        checks.append("build")
    if verify.get("require_security_scan"):
        checks.append("semgrep")
    if verify.get("require_regression_tests"):
        checks.append("regression_tests")
    if verify.get("require_failing_test_or_trace"):
        checks.append("failing_test_or_trace")
    if verify.get("require_manual_validation"):
        checks.append("manual_validation")
    if verify.get("require_link_check") or verify.get("require_source_consistency"):
        checks.append("source_consistency")
    return checks


def markdown_section(text: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\s*$([\s\S]*?)(?=^## |\Z)"
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def section_is_complete(section: str) -> bool:
    if not section:
        return False
    markers = [
        "TBD",
        "| Existing behavior identified from `docs/memory/module-map.md` |",
        "| Affected modules | TBD |",
        "| Public APIs / contracts | TBD |",
        "- [ ]",
    ]
    return not any(marker in section for marker in markers)


def impact_analysis_missing_parts(request: ManagedRequest) -> list[str]:
    if not request.spec_path.exists():
        return ["Spec file"]
    text = request.spec_path.read_text(encoding="utf-8", errors="ignore")
    missing = []
    for heading in ["Impact Analysis", "Coupling Constraints", "Regression Plan"]:
        if not section_is_complete(markdown_section(text, heading)):
            missing.append(heading)
    return missing


def regression_matrix_complete(request: ManagedRequest) -> bool:
    # 接受两处任一已填:verify 的 Regression Matrix,或 spec 的 Regression Plan
    # (ai-build 流程让 agent 填 spec,二者口径需一致,避免"按文档填了仍判未完成")
    if request.verify_matrix_path.exists():
        text = request.verify_matrix_path.read_text(encoding="utf-8", errors="ignore")
        if section_is_complete(markdown_section(text, "Regression Matrix")):
            return True
    if request.spec_path.exists():
        spec = request.spec_path.read_text(encoding="utf-8", errors="ignore")
        if section_is_complete(markdown_section(spec, "Regression Plan")):
            return True
    return False


# 人工类 required 检查:脚本无法自动完成,列为"需人工确认",不锁死 can_merge
HUMAN_CHECKS = {"regression_tests", "failing_test_or_trace", "manual_validation", "source_consistency"}

# 这些任务类型改了代码就必须配套测试(实质质量门禁,而非扫 markdown)
TASKS_NEEDING_TESTS = {"feature", "bugfix", "refactor", "migration"}

_CODE_EXTS = (
    ".py", ".go", ".js", ".ts", ".jsx", ".tsx", ".java", ".rs", ".rb",
    ".php", ".c", ".cc", ".cpp", ".cs", ".kt", ".swift", ".scala",
)


def git_changed_files(target: Path) -> list[str] | None:
    """目标项目工作树改动的文件(相对路径);非 git 仓库或 git 不可用时返回 None。"""
    try:
        result = subprocess.run(
            ["git", "-C", str(target), "status", "--porcelain"],
            capture_output=True, text=True, timeout=30,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    files: list[str] = []
    for line in result.stdout.splitlines():
        path = line[3:].strip() if len(line) > 3 else ""
        if " -> " in path:  # 重命名:取新路径
            path = path.split(" -> ")[-1].strip()
        if path:
            files.append(path)
    return files


def is_test_file(path: str) -> bool:
    segs = path.lower().split("/")
    if any(seg in {"tests", "test", "__tests__", "spec"} for seg in segs):
        return True
    name = segs[-1]
    return (
        name.startswith("test_") or name.endswith("_test.py") or name.endswith("_test.go")
        or ".test." in name or ".spec." in name
        or name.endswith("test.java") or name.endswith("tests.java")
    )


def is_framework_artifact(path: str) -> bool:
    return path.startswith(("docs/", ".claude/", ".codex/", ".github/")) or path == ".ai-discipline.json"


def is_code_file(path: str) -> bool:
    return path.endswith(_CODE_EXTS)


# 从改动代码里提取被定义的符号(函数/类/方法名),用于核对测试是否真的引用了改动。
# 既认 def/class/func 等关键字定义,也认 const/let NAME = (...) => 这类 JS/TS
# 箭头函数 / 函数表达式 / 类表达式的赋值式定义(否则前端代码会整体绕过门禁)。
_SYMBOL_DEF_RE = re.compile(
    r"^[+\s]*(?:export\s+)?(?:default\s+)?(?:public\s+|private\s+|static\s+)*(?:async\s+)?"
    r"(?:def|class|func|function|fn|interface|type|struct|trait|impl)\s+([A-Za-z_$][\w$]*)"
)
_SYMBOL_ASSIGN_RE = re.compile(
    r"^[+\s]*(?:export\s+)?(?:default\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*"
    r"(?:async\s+)?(?:\([^)]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>|function\b|class\b)"
)


def _match_symbol(line):
    match = _SYMBOL_DEF_RE.match(line) or _SYMBOL_ASSIGN_RE.match(line)
    return match.group(1) if match else None


def _nearest_def_above(lines, idx):
    """找改动行所属的符号。装饰器行(@...)属于其下方的函数,向下找;否则向上找最近的 def
    —— 否则改装饰器/签名上方的行会被误归到上一个函数。"""
    if not lines:
        return None
    start = min(max(idx, 0), len(lines) - 1)
    if lines[start].lstrip().startswith("@"):  # 改动落在装饰器上 → 归属下方的函数
        for j in range(start, min(start + 12, len(lines))):
            sym = _match_symbol(lines[j])
            if sym:
                return sym
    for i in range(start, -1, -1):
        sym = _match_symbol(lines[i])
        if sym:
            return sym
    return None


def changed_code_symbols(target: Path, code_files: list[str]) -> set[str]:
    """改动涉及的符号(函数/类名)。用 git diff --unified=0 精确定位改动行:
    - 对每个 hunk,按新文件起始行号在改动后的文件里**向上找最近的 def**(含缩进的类方法);
    - 从新增行(+)提取新增的定义。
    不用 git 自带的 hunk funcname:它只认顶格声明,会把缩进的类方法误归到外层 class
    (于是任何 import 该类的测试都白送通过)。也不用 -W:-W 会把相邻未改函数带进来。"""
    symbols: set[str] = set()
    for f in code_files:
        try:
            content_lines = (target / f).read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            content_lines = []
        diff_text = ""
        try:
            result = subprocess.run(
                ["git", "-C", str(target), "diff", "HEAD", "--unified=0", "--", f],
                capture_output=True, text=True, timeout=30,
            )
            diff_text = result.stdout
        except (OSError, subprocess.SubprocessError):
            diff_text = ""
        file_syms: set[str] = set()
        has_hunk = False
        for line in diff_text.splitlines():
            if line.startswith("@@"):
                has_hunk = True
                # @@ -a,b +c,d @@ :取新文件改动起始行 c,在改后文件里向上找最近的 def
                m = re.search(r"\+(\d+)", line)
                if m and content_lines:
                    idx = min(max(int(m.group(1)) - 1, 0), len(content_lines) - 1)
                    sym = _nearest_def_above(content_lines, idx)
                    if sym:
                        file_syms.add(sym)
            elif line.startswith("+") and not line.startswith("+++"):
                sym = _match_symbol(line[1:])
                if sym:
                    file_syms.add(sym)
        # 回退全文提取的两种情形:① 无 diff(untracked/新文件);② git 把改动当作 binary
        # (含 null 字节的代码文件,只输出 "Binary files differ"、无 hunk)。有 hunk 却提
        # 不到符号(纯模块级改动)不回退,留给门禁标 uncovered(见 verification_gate_details)。
        if not diff_text.strip() or (not has_hunk and not file_syms):
            for line in content_lines:
                sym = _match_symbol(line)
                if sym:
                    file_syms.add(sym)
        symbols |= file_syms
    return symbols


def tests_reference_symbols(target: Path, test_files: list[str], symbols: set[str]) -> bool:
    """改动的测试文件是否引用了任一改动符号。提不出符号时返回 True(不阻断)。"""
    if not symbols:
        return True
    for tf in test_files:
        try:
            content = (target / tf).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(re.search(rf"\b{re.escape(s)}\b", content) for s in symbols):
            return True
    return False


def native_test_outcome(native: list[CommandResult]) -> str:
    """测试命令的整体结果:'passed' | 'failed' | 'none'。只看测试命令(name 以 'test' 结尾,
    覆盖 go:test/python:pytest/python:unittest/.../java:gradle-test,排除 lint/typecheck/build)
    的进程状态,不靠 count_test_cases 的脆弱正则,对 go/java 也稳。fail-closed:没装/跳过算 none。"""
    test_items = [i for i in native if i.name != "native:detect" and i.name.endswith("test")]
    if not test_items:
        return "none"
    if any(i.status in {"failed", "timeout"} for i in test_items):
        return "failed"
    if all(i.status == "passed" for i in test_items):
        return "passed"
    return "none"  # 部分/全部 skipped(工具没装)→ 不能宣称套件全绿


def verification_gate_details(
    request: ManagedRequest,
    semgrep: CommandResult | None,
    native: list[CommandResult],
    diff_cov: dict | None = None,
) -> dict[str, object]:
    required = required_verify_checks(request)
    regression_outcome = native_test_outcome(native)  # 全套测试真跑且过 = 回归已验证
    executed: list[dict[str, object]] = []
    blocking_reasons: list[str] = []   # 真问题(测试失败/安全发现/文档未填)→ 阻断 can_merge
    uncovered_checks: list[str] = []   # 自动工具不可用或未运行 → 仅提示,不阻断
    needs_human_checks: list[str] = []  # 人工类检查 → 仅提示,不阻断

    # 文档类(agent 能补)未完成 → 阻断
    impact_missing = impact_analysis_missing_parts(request)
    if impact_missing:
        blocking_reasons.append(f"impact analysis incomplete: {', '.join(impact_missing)}")
    # 回归:从"spec 填没填"升级成"全套测试真跑且过"。全套绿→已验证;全套红→失败项已在
    # native 循环阻断;无可跑套件(none)→ 回退到要求填 Regression Plan,fail-closed。
    if "regression_matrix" in required and regression_outcome == "none" and not regression_matrix_complete(request):
        blocking_reasons.append(
            "regression unverified: no test suite ran and the spec's Regression Plan is not filled"
        )

    # semgrep(自动工具):失败/有发现 → 阻断;不可用或未运行 → 仅提示
    if semgrep:
        executed.append({"name": "semgrep", "required": "semgrep" in required, "status": semgrep.status})
        if semgrep.status in {"failed", "timeout"}:
            blocking_reasons.append(f"semgrep {semgrep.status}")
        elif semgrep.status == "skipped":
            if "semgrep" in required:
                uncovered_checks.append("semgrep (tool unavailable)")
        else:
            summary = parse_semgrep_summary(semgrep.stdout)
            if summary.get("parse_error"):
                blocking_reasons.append("semgrep output parse error")
            if summary.get("findings", 0):
                blocking_reasons.append(f"semgrep findings: {summary.get('findings')}")
            if summary.get("errors", 0):
                blocking_reasons.append(f"semgrep scan errors: {summary.get('errors')}")
    elif "semgrep" in required:
        uncovered_checks.append("semgrep (not run)")

    # native:失败 → 阻断;探测不到可运行命令 → 仅提示
    native_ran = False
    build_ran = False
    for item in native:
        is_build = "build" in item.name.lower()
        native_ran = native_ran or item.name != "native:detect"
        build_ran = build_ran or is_build
        executed.append({
            "name": item.name,
            "required": bool(("native_checks" in required and item.name != "native:detect") or ("build" in required and is_build)),
            "status": item.status,
        })
        if item.status in {"failed", "timeout"}:
            blocking_reasons.append(f"{item.name} {item.status}")

    if "native_checks" in required and (not native or not native_ran or all(item.status == "skipped" for item in native)):
        uncovered_checks.append("native_checks (no runnable test command found)")
    if "build" in required:
        # required 的 build 即使无法运行也要如实报告,不能从所有列表里静默蒸发
        if not build_ran:
            uncovered_checks.append("build (no build step detected for this stack)")
        elif any("build" in item.name.lower() and item.status == "skipped" for item in native):
            uncovered_checks.append("build (not run)")

    # 测试配套门禁(实质质量,非 markdown 扫描):feature/bugfix/refactor/migration 改了代码
    # 就必须配套测试,且测试要真引用改动符号(堵空测试/测错函数)。test_evidence_ok 三态供
    # 下面的人工检查复用:True=有覆盖改动的测试;False=改了码却没有;None=非 git 无法核实。
    test_evidence_ok = None
    if request.task in TASKS_NEEDING_TESTS:
        repo = request.path.parents[2]
        changed = git_changed_files(repo)
        if changed is None:
            uncovered_checks.append("test-coverage (cannot verify: target is not a git repository)")
        else:
            code_changed = [f for f in changed if is_code_file(f) and not is_test_file(f) and not is_framework_artifact(f)]
            test_changed = [f for f in changed if is_test_file(f) and not is_framework_artifact(f)]
            if not code_changed:
                test_evidence_ok = True  # 没改业务代码,无需配套测试
            elif not test_changed:
                test_evidence_ok = False
                blocking_reasons.append(
                    f"code changed without a matching test change ({len(code_changed)} code file(s), 0 test files)"
                )
            else:
                symbols = changed_code_symbols(repo, code_changed)
                if not symbols:
                    # 改动不含可提取的函数/类符号(如纯模块级赋值/配置)→ 无法静态核实测试
                    # 是否覆盖;不静默放行,降级为未覆盖(coverage 不全,但不误拦)
                    uncovered_checks.append("test-coverage (changed code has no extractable symbol to match tests against)")
                elif tests_reference_symbols(repo, test_changed, symbols):
                    test_evidence_ok = True
                else:
                    test_evidence_ok = False
                    blocking_reasons.append(
                        "the changed tests do not reference any changed code symbol — the test may not actually cover the change"
                    )

    for manual_check in sorted(HUMAN_CHECKS):
        if manual_check not in required:
            continue
        # 回归测试(refactor):全套测试真跑且过 = 行为不变证据,自动满足,不再要人工确认
        if manual_check == "regression_tests" and regression_outcome == "passed":
            continue
        # bugfix 失败测试证据:有覆盖改动的测试即满足;没有时已被上面的测试配套门禁阻断
        # (不重复记);非 git(None)无法核实 → 保留人工,fail-closed。
        if manual_check == "failing_test_or_trace" and test_evidence_ok is not None:
            continue
        needs_human_checks.append(manual_check)

    # diff-coverage:启用时,改动的可执行行没被测试执行到 → gap。默认标 uncovered(不阻断);
    # preset require_diff_coverage 时升级为 blocking。fail-closed:工具不可用 → uncovered,不静默通过。
    require_dc = bool(request.verify_params.get("require_diff_coverage"))
    if require_dc or diff_cov is not None:
        if diff_cov is None or not diff_cov.get("available"):
            reason = (diff_cov or {}).get("reason", "not run")
            uncovered_checks.append(f"diff-coverage (coverage tool unavailable: {reason})")
        else:
            gap = sum(len(v) for v in (diff_cov.get("uncovered_lines") or {}).values())
            if gap:
                msg = f"diff-coverage: {gap} changed executable line(s) not executed by tests"
                if require_dc:
                    blocking_reasons.append(msg)
                else:
                    uncovered_checks.append(msg)

    blocking_reasons = sorted(set(blocking_reasons))
    uncovered_checks = sorted(set(uncovered_checks))
    needs_human_checks = sorted(set(needs_human_checks))
    # 两个不同的信号,都如实给出:
    # - can_merge:没有已知阻断问题(测试没失败 / 没安全发现 / 文档已填)
    # - coverage_complete:所有 required 检查都真正运行并通过(没有未覆盖 / 不需人工)
    # 绿灯(can_merge)但 coverage 不全时,报告必须列出未覆盖项,不静默放行
    can_merge = not blocking_reasons
    coverage_complete = not uncovered_checks and not needs_human_checks
    return {
        "required_checks": required,
        "executed_checks": executed,
        "blocking_reasons": blocking_reasons,
        "uncovered_checks": uncovered_checks,
        "needs_human_checks": needs_human_checks,
        # 兼容旧字段(聚合端读取):未覆盖 + 需人工
        "skipped_required_checks": sorted(set(uncovered_checks + needs_human_checks)),
        "can_merge": can_merge,
        "coverage_complete": coverage_complete,
    }


def command_available(command: list[str], target: Path) -> bool:
    # command 已由调用方(run_command)resolve;此处不再重复 resolve,
    # 否则会把 ./gradlew.bat 再加一次后缀变成 ./gradlew.bat.bat,导致命令被误判不可用
    if not command:
        return False
    executable = command[0]
    if executable.startswith("./"):
        return (target / executable[2:]).exists()
    return shutil.which(executable) is not None


def resolve_local_command(command: list[str], target: Path) -> list[str]:
    if not command:
        return command
    executable = command[0]
    if not executable.startswith("./"):
        return command
    local = target / executable[2:]
    if sys.platform.startswith("win"):
        if local.with_suffix(".bat").exists():
            return [f"{executable}.bat", *command[1:]]
        if local.with_suffix(".cmd").exists():
            return [f"{executable}.cmd", *command[1:]]
    return command


def terminate_process_tree(proc: "subprocess.Popen") -> None:
    """超时后杀整个进程组(POSIX),回收 wrapper 派生的孙进程;Windows 退化为杀直接子进程。"""
    if sys.platform.startswith("win"):
        proc.kill()
        return
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        proc.kill()


def run_command(name: str, command: list[str], target: Path, timeout: int) -> CommandResult:
    command = resolve_local_command(command, target)
    started = dt.datetime.now()
    if not command_available(command, target):
        return CommandResult(
            name=name,
            command=command,
            status="skipped",
            exit_code=None,
            duration_seconds=0.0,
            stdout="",
            stderr=f"Command not available: {command[0] if command else '<empty>'}",
        )
    # 用独立进程组运行,超时后杀整个组,回收 npm/gradle 等 wrapper fork 出的孙进程
    proc = subprocess.Popen(
        command,
        cwd=target,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=not sys.platform.startswith("win"),
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        duration = (dt.datetime.now() - started).total_seconds()
        return CommandResult(
            name=name,
            command=command,
            status="passed" if proc.returncode == 0 else "failed",
            exit_code=proc.returncode,
            duration_seconds=round(duration, 3),
            stdout=truncate_output(stdout),
            stderr=truncate_output(stderr),
        )
    except subprocess.TimeoutExpired:
        terminate_process_tree(proc)
        stdout, stderr = proc.communicate()
        duration = (dt.datetime.now() - started).total_seconds()
        return CommandResult(
            name=name,
            command=command,
            status="timeout",
            exit_code=None,
            duration_seconds=round(duration, 3),
            stdout=truncate_output(stdout or ""),
            stderr=truncate_output((stderr or "") + f"\nTimed out after {timeout} seconds."),
        )


def node_script_command(target: Path, script_name: str) -> list[str]:
    if (target / "pnpm-lock.yaml").exists():
        return ["pnpm", script_name]
    if (target / "yarn.lock").exists():
        return ["yarn", script_name]
    return ["npm", "run", script_name]


def detect_native_commands(target: Path, request: ManagedRequest) -> list[tuple[str, list[str]]]:
    commands: list[tuple[str, list[str]]] = []
    package_json = target / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
            scripts = data.get("scripts", {})
            if isinstance(scripts, dict):
                for name in ["lint", "typecheck", "test"]:
                    if name in scripts:
                        commands.append((f"node:{name}", node_script_command(target, name)))
                if request.verify_params.get("require_build") and "build" in scripts:
                    commands.append(("node:build", node_script_command(target, "build")))
        except json.JSONDecodeError:
            # package.json 损坏:不臆测 test 脚本是否存在,跳过 node 检查
            pass

    if (target / "go.mod").exists():
        commands.append(("go:test", ["go", "test", "./..."]))
        if request.verify_params.get("require_build"):
            commands.append(("go:build", ["go", "build", "./..."]))

    if (target / "pyproject.toml").exists() or (target / "requirements.txt").exists() or (target / "pytest.ini").exists():
        # 优先 pytest(若项目用 pytest 或本机已装),否则回退标准库 unittest(总能跑)
        if (target / "pytest.ini").exists() or shutil.which("pytest"):
            commands.append(("python:pytest", [sys.executable, "-m", "pytest"]))
        else:
            commands.append(("python:unittest", [sys.executable, "-m", "unittest", "discover"]))

    if (target / "Cargo.toml").exists():
        commands.append(("rust:cargo-test", ["cargo", "test"]))
        if request.verify_params.get("require_build"):
            commands.append(("rust:cargo-build", ["cargo", "build"]))

    if (target / "pom.xml").exists():
        commands.append(("java:mvn-test", ["mvn", "test"]))

    if (target / "build.gradle").exists() or (target / "build.gradle.kts").exists():
        if (target / "gradlew").exists() or (target / "gradlew.bat").exists():
            commands.append(("java:gradle-test", ["./gradlew", "test"]))
        else:
            commands.append(("java:gradle-test", ["gradle", "test"]))

    return commands


SEVERITY_LEVELS = ["info", "warning", "error"]


def semgrep_command(request: ManagedRequest) -> list[str]:
    config = request.verify_params.get("semgrep_config", "auto")
    if not isinstance(config, str) or not config:
        config = "auto"
    command = ["semgrep", "scan", "--config", config, "--json"]
    # preset 的 severity 表示"最低严重度",展开成 semgrep 的逐级过滤(该级及以上)
    severity = request.verify_params.get("severity")
    if isinstance(severity, str) and severity.lower() in SEVERITY_LEVELS:
        for level in SEVERITY_LEVELS[SEVERITY_LEVELS.index(severity.lower()):]:
            command.extend(["--severity", level.upper()])
    command.append(".")
    return command


def parse_semgrep_summary(raw_output: str) -> dict[str, object]:
    try:
        data = json.loads(raw_output) if raw_output.strip() else {}
    except json.JSONDecodeError:
        return {"parse_error": True, "findings": 0, "errors": 0, "severity_counts": {}}
    results = data.get("results", []) if isinstance(data, dict) else []
    errors = data.get("errors", []) if isinstance(data, dict) else []
    severity_counts: dict[str, int] = {}
    if isinstance(results, list):
        for item in results:
            if not isinstance(item, dict):
                continue
            extra = item.get("extra", {})
            severity = "unknown"
            if isinstance(extra, dict):
                severity = str(extra.get("severity", "unknown")).lower()
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
    return {
        "parse_error": False,
        "findings": len(results) if isinstance(results, list) else 0,
        "errors": len(errors) if isinstance(errors, list) else 0,
        "severity_counts": severity_counts,
    }


def run_semgrep(target: Path, request: ManagedRequest, timeout: int, actions: list[str]) -> CommandResult:
    result = run_command("semgrep", semgrep_command(request), target, timeout)
    output_file = target / "docs" / "verify" / "semgrep-results.json"
    if result.status in {"passed", "failed"} and result.stdout.strip():
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(result.stdout, encoding="utf-8")
        result.output_path = rel(output_file, target)
        actions.append(f"write: {output_file}")
    return result


def result_to_dict(result: CommandResult) -> dict[str, object]:
    return {
        "name": result.name,
        "command": result.command,
        "status": result.status,
        "exit_code": result.exit_code,
        "duration_seconds": result.duration_seconds,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "output_path": result.output_path,
    }


def count_test_cases(native: list[CommandResult]) -> tuple[int, int, bool]:
    """从测试命令输出解析通过/失败的用例数(pytest / unittest)。
    parsed=False 表示没解析到真实数字,调用方应改用更保守的措辞。"""
    passed = failed = 0
    parsed = False
    for item in native:
        if item.name == "native:detect":
            continue
        out = f"{item.stdout or ''}\n{item.stderr or ''}"
        mp = re.search(r"(\d+)\s+passed", out)        # pytest: "4 passed"
        mf = re.search(r"(\d+)\s+failed", out)        # pytest: "1 failed"
        if mp or mf:
            if mp:
                passed += int(mp.group(1))
            if mf:
                failed += int(mf.group(1))
            parsed = True
            continue
        mr = re.search(r"Ran\s+(\d+)\s+test", out)    # unittest: "Ran 4 tests"
        if mr:
            total = int(mr.group(1))
            fcount = sum(int(m.group(1)) for m in re.finditer(r"(?:failures|errors)=(\d+)", out))
            failed += fcount
            passed += max(0, total - fcount)
            parsed = True
    return passed, failed, parsed


def humanize_uncovered(item: str) -> str:
    low = item.lower()
    if low.startswith("semgrep"):
        return "A security scan did not run — the scanner isn't installed on this machine. It's an optional check."
    if low.startswith("build"):
        return "There's no separate build step for this kind of project, so nothing to build."
    if low.startswith("native_checks"):
        return "No automatic test command was found to run."
    if low.startswith("test-coverage"):
        return "The project isn't a git repo, so the framework couldn't check whether a test was added."
    return item


def humanize_needs_human(item: str) -> str:
    labels = {
        "regression_tests": "Someone should manually confirm existing behavior still works.",
        "failing_test_or_trace": "Someone should confirm the bug reproduction / failing test.",
        "manual_validation": "Someone should do a manual check.",
        "source_consistency": "Someone should confirm the docs/sources are consistent.",
    }
    return labels.get(item, item)


def humanize_blocking(item: str) -> str:
    low = item.lower()
    if "without a matching test" in low:
        return "Code was changed but no test was added or updated."
    if "impact analysis incomplete" in low:
        return "The spec's Impact Analysis isn't filled in yet."
    if "regression incomplete" in low:
        return "The spec's Regression Plan isn't filled in yet."
    if "semgrep findings" in low:
        return "The security scan found issues that need attention."
    if "failed" in low or "timeout" in low:
        return f"A check did not pass: {item}"
    return item


def write_user_summary(
    target: Path,
    request: ManagedRequest,
    gate_details: dict[str, object],
    native: list[CommandResult],
    actions: list[str],
) -> None:
    """框架机制兜底:把门禁结果转成大白话写进 SUMMARY.md,不依赖 agent 自律转述。"""
    coverage = bool(gate_details.get("coverage_complete"))
    blocking = [str(x) for x in (gate_details.get("blocking_reasons") or [])]
    uncovered = [str(x) for x in (gate_details.get("uncovered_checks") or [])]
    needs_human = [str(x) for x in (gate_details.get("needs_human_checks") or [])]

    test_items = [i for i in native if i.name != "native:detect"]
    case_passed, case_failed, parsed = count_test_cases(native)

    lines = [f"# Summary: {request.name}", ""]
    if not test_items:
        lines.append("- Tests: none ran")
    elif parsed:
        lines.append(f"- Tests: {case_passed} passed, {case_failed} failed")
    else:
        cmd_passed = sum(1 for i in test_items if i.status == "passed")
        cmd_failed = sum(1 for i in test_items if i.status in {"failed", "timeout"})
        lines.append(f"- Tests: {cmd_passed} of {len(test_items)} check(s) passed, {cmd_failed} failed")

    if blocking:
        lines.append("- Status: NOT DONE YET — needs fixing:")
        lines.extend(f"  - {humanize_blocking(b)}" for b in blocking)
    elif not coverage:
        lines.append("- Status: Works — tests pass and nothing is blocking; some optional checks were skipped (listed below).")
    else:
        lines.append("- Status: DONE — everything required was checked and passed.")

    extras = [humanize_uncovered(u) for u in uncovered] + [humanize_needs_human(h) for h in needs_human]
    if extras:
        lines.append("")
        lines.append("Not covered (optional or unavailable — these are not failures):")
        lines.extend(f"- {e}" for e in extras)

    lines.append("")
    lines.append("_Plain-language summary auto-generated by the framework. Technical detail: docs/verify/verification-results.json._")

    path = target / "docs" / "ai-engineering" / "SUMMARY.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(GENERATED + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    actions.append(f"write: {path}")


def record_run_data(
    target: Path,
    request: ManagedRequest,
    gate_details: dict[str, object],
    native: list[CommandResult],
    actions: list[str],
) -> None:
    """把每次验证的统计 + 问题持续沉淀到目标项目的 data/:
    - data/run-stats.jsonl :每次一行机器可读统计(时间/task/can_merge/覆盖/测试数/问题计数);
    - data/issues-log.md   :有阻断/未覆盖/需人工时,追加成人可读台账。
    框架被用得越多,data/ 里的真实数据和问题台账就越全。"""
    blocking = [str(x) for x in (gate_details.get("blocking_reasons") or [])]
    uncovered = [str(x) for x in (gate_details.get("uncovered_checks") or [])]
    needs_human = [str(x) for x in (gate_details.get("needs_human_checks") or [])]
    case_passed, case_failed, _ = count_test_cases(native)
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    data_dir = target / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    stat = {
        "ts": now,
        "task": request.task,
        "name": request.name,
        "risk": request.risk,
        "can_merge": bool(gate_details.get("can_merge")),
        "coverage_complete": bool(gate_details.get("coverage_complete")),
        "tests_passed": case_passed,
        "tests_failed": case_failed,
        "blocking_count": len(blocking),
        "uncovered_count": len(uncovered),
        "needs_human_count": len(needs_human),
    }
    stats_path = data_dir / "run-stats.jsonl"
    with stats_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(stat, ensure_ascii=False) + "\n")
    actions.append(f"append: {stats_path}")

    issues = (
        [("阻断", b) for b in blocking]
        + [("未覆盖", u) for u in uncovered]
        + [("需人工", h) for h in needs_human]
    )
    if issues:
        log_path = data_dir / "issues-log.md"
        if not log_path.exists():
            log_path.write_text(
                "# 问题台账\n\n_框架每次验证遇到的阻断 / 未覆盖 / 需人工项,自动追加。_\n",
                encoding="utf-8",
            )
        entry = [f"\n## {now} · {request.task} · {request.name}"]
        entry.extend(f"- [{kind}] {detail}" for kind, detail in issues)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write("\n".join(entry) + "\n")
        actions.append(f"append: {log_path}")

    _write_run_summary(data_dir, actions)


def _write_run_summary(data_dir: Path, actions: list[str]) -> None:
    """从 run-stats.jsonl 重算汇总,写 data/run-summary.md(每次验证后刷新)。"""
    rows = []
    try:
        lines = (data_dir / "run-stats.jsonl").read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:  # 跳过损坏的半行(进程中断/并发 append 写坏),不让一行卡死整份汇总
            rows.append(json.loads(line))
        except ValueError:
            continue
    if not rows:
        return
    n = len(rows)
    mergeable = sum(1 for r in rows if r.get("can_merge"))
    covered = sum(1 for r in rows if r.get("coverage_complete"))
    with_blocking = sum(1 for r in rows if r.get("blocking_count", 0) > 0)
    tp = sum(int(r.get("tests_passed", 0)) for r in rows)
    tf = sum(int(r.get("tests_failed", 0)) for r in rows)
    by_task: dict[str, int] = {}
    for r in rows:
        key = str(r.get("task", "?"))
        by_task[key] = by_task.get(key, 0) + 1

    def pct(x):
        return f"{(100 * x / n):.0f}%"

    lines = [
        "# 运行数据汇总",
        "",
        f"_由框架自动统计自 `run-stats.jsonl`,每次验证后刷新。共 {n} 次运行。_",
        "",
        f"- 可合并 (can_merge): {mergeable}/{n} ({pct(mergeable)})",
        f"- 完全覆盖 (coverage_complete): {covered}/{n} ({pct(covered)})",
        f"- 有阻断问题的运行: {with_blocking}/{n} ({pct(with_blocking)})",
        f"- 测试用例累计: {tp} passed, {tf} failed",
        "",
        "## 按任务类型",
        "",
        "| task | 次数 |",
        "|---|---|",
    ]
    for task, cnt in sorted(by_task.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {task} | {cnt} |")
    summary_path = data_dir / "run-summary.md"
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    actions.append(f"write: {summary_path}")


def write_verification_results(
    target: Path,
    request: ManagedRequest,
    semgrep: CommandResult | None,
    native: list[CommandResult],
    actions: list[str],
    diff_cov: dict | None = None,
):
    if semgrep is None and not native:
        return None
    verify_dir = target / "docs" / "verify"
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    semgrep_summary = parse_semgrep_summary(semgrep.stdout) if semgrep else None
    overall_status, overall_reason = verification_rollup(semgrep, native)
    gate_details = verification_gate_details(request, semgrep, native, diff_cov)
    payload: dict[str, object] = {
        "created": now,
        "request": {
            "name": request.name,
            "task": request.task,
            "preset": request.preset,
            "risk": request.risk,
        },
        "overall_status": overall_status,
        "overall_reason": overall_reason,
        **gate_details,
        "semgrep": result_to_dict(semgrep) if semgrep else None,
        "semgrep_summary": semgrep_summary,
        "native_checks": [result_to_dict(item) for item in native],
        "diff_coverage": diff_cov,
    }
    write_json_artifact(verify_dir / "verification-results.json", payload, actions)

    lines = [
        f"# Verification Results: {request.name}",
        "",
        f"Created: {now}",
        "",
        "## Summary",
        "",
        f"- Overall status: `{overall_status}`",
        f"- Reason: {overall_reason}",
        f"- Can merge (no blocking issues): `{str(gate_details['can_merge']).lower()}`",
        f"- Fully verified (all required checks covered): `{str(gate_details.get('coverage_complete', False)).lower()}`",
        f"- Blocking reasons: `{', '.join(gate_details['blocking_reasons']) if gate_details['blocking_reasons'] else 'none'}`",
        f"- Uncovered required checks (tool missing / not run): `{', '.join(gate_details.get('uncovered_checks', [])) if gate_details.get('uncovered_checks') else 'none'}`",
        f"- Needs human verification: `{', '.join(gate_details.get('needs_human_checks', [])) if gate_details.get('needs_human_checks') else 'none'}`",
        "",
        "| Check | Status | Exit | Duration |",
        "|---|---|---|---|",
    ]
    if semgrep:
        lines.append(
            f"| {md_cell('semgrep')} | {md_cell(semgrep.status)} | "
            f"{md_cell(semgrep.exit_code if semgrep.exit_code is not None else '')} | "
            f"{md_cell(f'{semgrep.duration_seconds}s')} |"
        )
    for item in native:
        lines.append(
            f"| {md_cell(item.name)} | {md_cell(item.status)} | "
            f"{md_cell(item.exit_code if item.exit_code is not None else '')} | "
            f"{md_cell(f'{item.duration_seconds}s')} |"
        )
    if semgrep_summary:
        lines.extend([
            "",
            "## Semgrep Summary",
            "",
            f"- Command: `{command_to_text(semgrep.command) if semgrep else ''}`",
            f"- Status: `{semgrep.status if semgrep else ''}`",
            f"- Parse error: `{semgrep_summary.get('parse_error')}`",
            f"- Findings: `{semgrep_summary.get('findings')}`",
            f"- Errors: `{semgrep_summary.get('errors')}`",
            f"- Severity counts: `{json.dumps(semgrep_summary.get('severity_counts', {}), ensure_ascii=False)}`",
        ])
        if semgrep and semgrep.output_path:
            lines.append(f"- Raw JSON: `{semgrep.output_path}`")
        if semgrep and semgrep.stderr:
            lines.extend([
                "",
                "```text",
                semgrep.stderr.strip(),
                "```",
            ])
    lines.extend(["", "## Native Check Commands", ""])
    if native:
        for item in native:
            lines.extend([
                f"### {item.name}",
                "",
                f"- Command: `{command_to_text(item.command)}`",
                f"- Status: `{item.status}`",
                f"- Exit code: `{item.exit_code if item.exit_code is not None else ''}`",
                "",
                "Stdout:",
                "",
                "```text",
                (item.stdout or "No stdout.").strip(),
                "```",
                "",
                "Stderr:",
                "",
                "```text",
                (item.stderr or "No stderr.").strip(),
                "```",
                "",
            ])
    else:
        lines.append("- None run.")
    safe_write(verify_dir / "verification-results.md", "\n".join(lines), force=True, actions=actions)

    plan = verify_dir / "current-request-verify.md"
    if plan.exists():
        plan_text = plan.read_text(encoding="utf-8")
        summary_line = f"- Structured results written at `{now}`: `docs/verify/verification-results.json`, `docs/verify/verification-results.md`"
        if summary_line not in plan_text:
            plan.write_text(plan_text.rstrip() + "\n" + summary_line + "\n", encoding="utf-8")
            actions.append(f"update: {plan}")

    write_user_summary(target, request, gate_details, native, actions)
    try:  # data 沉淀是 nice-to-have,失败只记 skip,绝不拖垮验证主流程
        record_run_data(target, request, gate_details, native, actions)
    except Exception as exc:  # noqa: BLE001
        actions.append(f"skip run-data: {exc}")
    from build_test_index import refresh_test_index  # 局部 import:避免与本模块的循环依赖
    refresh_test_index(target, actions)
    return gate_details


def verification_rollup(semgrep: CommandResult | None, native: list[CommandResult]) -> tuple[str, str]:
    results = ([semgrep] if semgrep else []) + native
    if not results:
        return "pending", "No verification command was run."
    if any(item.status in {"failed", "timeout"} for item in results):
        return "blocked", "At least one verification command failed or timed out."
    if any(item.status == "skipped" for item in results):
        return "pending", "At least one requested verification command was skipped or unavailable."
    if semgrep:
        summary = parse_semgrep_summary(semgrep.stdout)
        if summary.get("parse_error"):
            return "blocked", "Semgrep output could not be parsed as JSON."
        if summary.get("findings", 0) or summary.get("errors", 0):
            return "blocked", "Semgrep reported findings or scan errors."
    if any(item.status == "passed" for item in results):
        return "verified", "All executed verification commands passed."
    return "pending", "Verification commands were skipped or unavailable."


def update_test_matrix_with_results(
    target: Path,
    request: ManagedRequest,
    semgrep: CommandResult | None,
    native: list[CommandResult],
    actions: list[str],
) -> None:
    if semgrep is None and not native:
        return
    matrix_path = request.verify_matrix_path
    status, reason = verification_rollup(semgrep, native)

    evidence_rows = []
    if semgrep:
        evidence_rows.append(
            f"| {md_cell('semgrep')} | {md_cell(f'`{command_to_text(semgrep.command)}`')} | "
            f"{md_cell(semgrep.status)} | {md_cell(semgrep.exit_code if semgrep.exit_code is not None else '')} |"
        )
    for item in native:
        evidence_rows.append(
            f"| {md_cell(item.name)} | {md_cell(f'`{command_to_text(item.command)}`')} | "
            f"{md_cell(item.status)} | {md_cell(item.exit_code if item.exit_code is not None else '')} |"
        )
    evidence_section = f"""Status: `{status}`

Reason: {reason}

| Check | Command | Status | Exit |
|---|---|---|---|
{chr(10).join(evidence_rows) if evidence_rows else "| None |  | pending |  |"}

Structured results:

- `docs/verify/verification-results.json`
- `docs/verify/verification-results.md`
"""

    # 已存在(框架生成的):保留 agent 填好的需求映射表与 Regression Matrix,只刷新 Verification Evidence
    # (旧实现每次都把需求行重写成 TBD,会冲掉 agent 的手填成果)
    if matrix_path.exists():
        existing = matrix_path.read_text(encoding="utf-8")
        if GENERATED not in existing:
            actions.append(f"skip human file: {matrix_path}")
            return
        head = existing.split("## Verification Evidence", 1)[0].replace(GENERATED, "").strip()
        content = f"{head}\n\n## Verification Evidence\n\n{evidence_section}"
        safe_write(matrix_path, content, force=True, actions=actions)
        return

    # 首次(矩阵尚不存在):生成 TBD 模板,由 agent 填需求映射与回归
    rows = []
    for idx, source in enumerate(request.requirements or [Path("none")], start=1):
        requirement = requirement_title(source) if source != Path("none") else request.name
        rows.append(
            f"| {md_cell(f'R{idx}')} | {md_cell(requirement)} | {md_cell('TBD')} | "
            f"{md_cell('TBD')} | {md_cell('TBD')} | {md_cell(status)} |"
        )
    content = f"""# Test Matrix

Request: `{request.name}`
Spec: `{rel(request.spec_path, target)}`

## Requirement Traceability

| Requirement ID | Requirement | Unit Test | Integration Test | Manual / Release Check | Status |
|---|---|---|---|---|---|
{chr(10).join(rows)}

## Regression Matrix

| Existing Behavior | Related Module / API | Regression Check | Required | Status |
|---|---|---|---|---|
| Existing behavior identified from `docs/memory/module-map.md` | TBD | TBD | yes | {status} |

## Verification Evidence

{evidence_section}"""
    safe_write(matrix_path, content, force=True, actions=actions)


def write_loop_run_log(
    target: Path,
    request: ManagedRequest,
    semgrep: CommandResult | None,
    native: list[CommandResult],
    actions: list[str],
) -> None:
    loop_dir = target / "docs" / "loops"
    path = loop_dir / "current-loop-run.md"
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status, reason = verification_rollup(semgrep, native)
    gate_details = verification_gate_details(request, semgrep, native)
    verify_state = "pending"
    if semgrep or native:
        verify_state = "blocked" if status == "blocked" else "done" if status == "verified" else "pending"
    next_action = "Review generated spec and loop before implementation."
    if status == "blocked":
        next_action = "Fix blocking verification issues, then rerun `/ai-verify`."
    elif status == "verified" and gate_details["can_merge"]:
        next_action = "Prepare PR evidence and review memory candidates."
    elif status == "verified":
        next_action = "Complete skipped required evidence before merge."

    content = f"""# Current Loop Run: {request.name}

Created: {now}

## Request

- Request: `{rel(request.path, target)}`
- Loop: `{rel(request.loop_path, target)}`
- Task: `{request.task}`
- Risk: `{request.risk}`

## State Progress

| State | Status | Evidence |
|---|---|---|
| load_context | done | `docs/ai-engineering/current-request.md` |
| map_impact | pending | Impact analysis in `{rel(request.spec_path, target)}` |
| plan | done | `{rel(request.spec_path, target)}`, `{rel(request.loop_path, target)}` |
| implement | pending | Safe executor does not edit business code. |
| verify | {verify_state} | `docs/verify/verification-results.json` when present |
| memory | pending | `docs/memory/memory-candidates.md` |
| done | pending | Requires accepted spec, verification evidence, and reviewed memory. |

## Loop Controls

- Max retries: `{request.loop_params.get("max_retries", "preset")}`
- Current retry count: `0`
- Human gate: `{request.loop_params.get("human_gate", "preset")}`
- Checkpoint: `{request.loop_params.get("checkpoint", "preset")}`

## Gate Summary

- Verification status: `{status}`
- Reason: {reason}
- Can merge (no blocking issues): `{str(gate_details["can_merge"]).lower()}`
- Fully verified (all required checks covered): `{str(gate_details.get("coverage_complete", False)).lower()}`
- Blocking reasons: `{", ".join(gate_details["blocking_reasons"]) if gate_details["blocking_reasons"] else "none"}`
- Uncovered required checks (tool missing / not run): `{", ".join(gate_details.get("uncovered_checks", [])) if gate_details.get("uncovered_checks") else "none"}`
- Needs human verification: `{", ".join(gate_details.get("needs_human_checks", [])) if gate_details.get("needs_human_checks") else "none"}`

## Next Action

{next_action}
"""
    safe_write(path, content, force=True, actions=actions)


def write_memory_candidates(
    target: Path,
    request: ManagedRequest,
    semgrep: CommandResult | None,
    native: list[CommandResult],
    actions: list[str],
) -> None:
    memory_dir = request.memory_path if request.memory_path.suffix == "" else request.memory_path.parent
    path = memory_dir / "memory-candidates.md"
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status, reason = verification_rollup(semgrep, native)
    gate_details = verification_gate_details(request, semgrep, native)
    candidate_sections = [
        "## Candidate Project Rule",
        "",
        "- Status: `needs-review`",
        "- Candidate: No durable project rule proposed automatically.",
        "- Evidence required before accepting: link to spec, verification result, PR review, or incident.",
        "",
        "## Candidate Module Map Update",
        "",
        "- Status: `needs-review`",
        "- Candidate: No module boundary update proposed automatically.",
        "- Evidence required before accepting: changed module ownership or dependency boundary.",
        "",
    ]
    if gate_details["blocking_reasons"]:
        candidate_sections.extend([
            "## Candidate Pitfall",
            "",
            "- Status: `needs-review`",
            f"- Context: `{request.name}` verification had blocking issues.",
            f"- Problem: {reason}",
            f"- Blocking reasons: `{', '.join(gate_details['blocking_reasons']) if gate_details['blocking_reasons'] else 'none'}`",
            f"- Skipped required checks: `{', '.join(gate_details['skipped_required_checks']) if gate_details['skipped_required_checks'] else 'none'}`",
            "- Rule / Lesson: Do not mark AI-generated work complete until required verification evidence is present.",
            "- Verification to add next time: rerun `/ai-verify` after fixing skipped or blocked gates.",
            "",
        ])
    else:
        candidate_sections.extend([
            "## Candidate Pitfall",
            "",
            "- Status: `none`",
            "- Candidate: No failure pattern observed in this run.",
            "",
        ])

    content = f"""# Memory Candidates: {request.name}

Created: {now}

## Policy

```json
{json.dumps(request.memory_params, ensure_ascii=False, indent=2)}
```

These are candidate memory writes only. Review before copying anything into `project-rules.md`, `module-map.md`, or `pitfalls.md`.

## Evidence

- Request: `{rel(request.path, target)}`
- Spec: `{rel(request.spec_path, target)}`
- Loop run: `docs/loops/current-loop-run.md`
- Verification results: `docs/verify/verification-results.json`
- Verification status: `{status}`

{chr(10).join(candidate_sections)}
"""
    safe_write(path, content, force=True, actions=actions)


def write_blocked_report(target: Path, request_path: Path, reason: str) -> Path:
    report = target / "docs" / "ai-engineering" / "execution-report.md"
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = f"""# Execution Report: blocked

Created: {now}

## Request

- Request: `{rel(request_path, target)}`
- Status: `blocked`

## Reason

{reason}

## Next Step

Create a managed request before running `/ai-execute` or `/ai-verify`.

Claude Code:

```text
/ai-request --task feature --name "<name>" --requirements docs/requirements/<name>.md --risk medium
```

Shell:

```bash
python .claude/skills/ai-engineering-discipline/scripts/run_request.py . --task feature --name "<name>" --requirements docs/requirements/<name>.md --risk medium
```
"""
    safe_write(report, content, force=True, actions=[])
    return report


def write_execution_report(target: Path, request: ManagedRequest, actions: list[str]) -> Path:
    report = target / "docs" / "ai-engineering" / "execution-report.md"
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = [
        f"# Execution Report: {request.name}",
        "",
        f"Created: {now}",
        "",
        "## Request",
        "",
        f"- Request: `{rel(request.path, target)}`",
        f"- Task: `{request.task}`",
        f"- Preset: `{request.preset}`",
        f"- Risk: `{request.risk}`",
        f"- Execute implementation now: `{str(request.execute).lower()}`",
        "",
        "## Safe Actions",
        "",
    ]
    content.extend(f"- {action}" for action in actions)
    content.extend([
        "",
        "## Next Human/Agent Step",
        "",
        "Review the generated spec, loop, loop run log, verify plan, memory candidates, and any structured verification results. Implementation may start only after the spec and loop are accepted.",
    ])
    safe_write(report, "\n".join(content), force=True, actions=[])
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", help="Target project path.")
    parser.add_argument("--request", help="Managed request path. Defaults to docs/ai-engineering/current-request.md.")
    parser.add_argument("--force", action="store_true", help="Overwrite generated artifacts.")
    parser.add_argument("--skip-init", action="store_true", help="Do not run init_project.py or inspect_project.py.")
    parser.add_argument("--run-semgrep", action="store_true", help="Run Semgrep and write structured results to docs/verify/.")
    parser.add_argument("--run-native-checks", action="store_true", help="Run detected native test/lint/typecheck/build commands.")
    parser.add_argument("--run-diff-coverage", action="store_true", help="Run diff-coverage: check changed lines are executed by tests (needs a coverage tool; degrades to uncovered if absent).")
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS, help="Timeout per verification command.")
    parser.add_argument("--fail-on-verify-failure", action="store_true", help="Exit non-zero after writing results if overall verification is blocked.")
    args = parser.parse_args()

    target = Path(args.target).expanduser().resolve()
    if not target.exists() or not target.is_dir():
        raise SystemExit(f"Target project does not exist: {target}")

    request_path = Path(args.request).expanduser().resolve() if args.request else target / "docs" / "ai-engineering" / "current-request.md"
    try:
        request = parse_request(target, request_path)
    except (FileNotFoundError, ValueError) as exc:
        report = write_blocked_report(target, request_path, str(exc))
        print(str(exc))
        print(f"report: {report}")
        return 1

    actions: list[str] = []
    if not args.skip_init:
        run_script_if_available("init_project.py", target, actions)
        run_script_if_available("inspect_project.py", target, actions)

    write_requirements_index(target, request, args.force, actions)
    write_spec(target, request, args.force, actions)
    write_loop(target, request, args.force, actions)
    write_verify_artifacts(target, request, args.force, actions)
    write_memory_plan(target, request, args.force, actions)

    semgrep_result = None
    native_results: list[CommandResult] = []
    if args.run_semgrep:
        semgrep_result = run_semgrep(target, request, args.timeout_seconds, actions)
        actions.append(f"verify semgrep: {semgrep_result.status}")
    if args.run_native_checks:
        native_commands = detect_native_commands(target, request)
        if native_commands:
            for name, command in native_commands:
                result = run_command(name, command, target, args.timeout_seconds)
                native_results.append(result)
                actions.append(f"verify {name}: {result.status}")
        else:
            native_results.append(
                CommandResult(
                    name="native:detect",
                    command=[],
                    status="skipped",
                    exit_code=None,
                    duration_seconds=0.0,
                    stdout="",
                    stderr="No recognized native verification commands.",
                )
            )
            actions.append("verify native: skipped no recognized commands")
    diff_cov = None
    if args.run_diff_coverage or request.verify_params.get("require_diff_coverage"):
        changed = git_changed_files(target)
        code_changed = [f for f in (changed or []) if is_code_file(f) and not is_test_file(f) and not is_framework_artifact(f)]
        if code_changed:
            from diff_coverage import diff_coverage_result
            diff_cov = diff_coverage_result(target, code_changed)
            actions.append(f"diff-coverage: {'available' if diff_cov.get('available') else 'unavailable'}")
    gate = write_verification_results(target, request, semgrep_result, native_results, actions, diff_cov)
    update_test_matrix_with_results(target, request, semgrep_result, native_results, actions)
    write_loop_run_log(target, request, semgrep_result, native_results, actions)
    write_memory_candidates(target, request, semgrep_result, native_results, actions)

    report = write_execution_report(target, request, actions)
    print(f"executed safe request setup: {request.name}")
    print(f"report: {report}")
    for action in actions:
        print(action)
    if args.fail_on_verify_failure:
        # 退出码必须反映完整门禁(测试配套 / impact / 回归),而不只是 semgrep/native 进程状态;
        # 复用 write_verification_results 已算的 gate,不重复跑 git diff
        if gate is None:  # 没跑 semgrep/native(无可验证结果)→ 现算一次(带上 diff_cov)
            gate = verification_gate_details(request, semgrep_result, native_results, diff_cov)
        if not gate["can_merge"]:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
