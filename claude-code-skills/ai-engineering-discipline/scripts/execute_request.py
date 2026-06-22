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

- Spec generator: ai-engineering-discipline (this spec is generated by execute_request, not by Spec Kit)
- Preset spec-framework label: `{request.spec_params.get("framework", "unknown")}` (label only; not invoked directly)
- Spec mode: `{request.spec_params.get("mode", request.task)}`
- Implementation should be planned in small, reviewable steps.

## Impact Analysis

Complete this before editing code in an existing project.

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


def verification_gate_details(
    request: ManagedRequest,
    semgrep: CommandResult | None,
    native: list[CommandResult],
) -> dict[str, object]:
    required = required_verify_checks(request)
    executed: list[dict[str, object]] = []
    blocking_reasons: list[str] = []   # 真问题(测试失败/安全发现/文档未填)→ 阻断 can_merge
    uncovered_checks: list[str] = []   # 自动工具不可用或未运行 → 仅提示,不阻断
    needs_human_checks: list[str] = []  # 人工类检查 → 仅提示,不阻断

    # 文档类(agent 能补)未完成 → 阻断
    impact_missing = impact_analysis_missing_parts(request)
    if impact_missing:
        blocking_reasons.append(f"impact analysis incomplete: {', '.join(impact_missing)}")
    if "regression_matrix" in required and not regression_matrix_complete(request):
        blocking_reasons.append("regression incomplete (fill the spec's Regression Plan)")

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

    for manual_check in sorted(HUMAN_CHECKS):
        if manual_check in required:
            needs_human_checks.append(manual_check)

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
            commands.append(("python:pytest", ["pytest"]))
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


def write_verification_results(
    target: Path,
    request: ManagedRequest,
    semgrep: CommandResult | None,
    native: list[CommandResult],
    actions: list[str],
) -> None:
    if semgrep is None and not native:
        return
    verify_dir = target / "docs" / "verify"
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    semgrep_summary = parse_semgrep_summary(semgrep.stdout) if semgrep else None
    overall_status, overall_reason = verification_rollup(semgrep, native)
    gate_details = verification_gate_details(request, semgrep, native)
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
    existing_regression = ""
    if matrix_path.exists():
        existing = matrix_path.read_text(encoding="utf-8")
        if GENERATED not in existing:
            actions.append(f"skip human file: {matrix_path}")
            return
        candidate_regression = markdown_section(existing, "Regression Matrix")
        if section_is_complete(candidate_regression):
            existing_regression = candidate_regression

    status, reason = verification_rollup(semgrep, native)
    rows = []
    for idx, source in enumerate(request.requirements or [Path("none")], start=1):
        requirement = requirement_title(source) if source != Path("none") else request.name
        rows.append(
            f"| {md_cell(f'R{idx}')} | {md_cell(requirement)} | {md_cell('TBD')} | "
            f"{md_cell('TBD')} | {md_cell('See verification evidence below')} | {md_cell(status)} |"
        )

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

    regression_section = existing_regression or f"""| Existing Behavior | Related Module / API | Regression Check | Required | Status |
|---|---|---|---|---|
| Existing behavior identified from `docs/memory/module-map.md` | TBD | TBD | yes | {status} |"""

    content = f"""# Test Matrix

Request: `{request.name}`
Spec: `{rel(request.spec_path, target)}`

| Requirement ID | Requirement | Unit Test | Integration Test | Manual / Release Check | Status |
|---|---|---|---|---|---|
{chr(10).join(rows)}

## Regression Matrix

{regression_section}

## Verification Evidence

Status: `{status}`

Reason: {reason}

| Check | Command | Status | Exit |
|---|---|---|---|
{chr(10).join(evidence_rows) if evidence_rows else "| None |  | pending |  |"}

Structured results:

- `docs/verify/verification-results.json`
- `docs/verify/verification-results.md`
"""
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
    if status == "blocked" or gate_details["blocking_reasons"] or gate_details["skipped_required_checks"]:
        candidate_sections.extend([
            "## Candidate Pitfall",
            "",
            "- Status: `needs-review`",
            f"- Context: `{request.name}` verification did not produce merge-ready evidence.",
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


def has_verify_failure(semgrep: CommandResult | None, native: list[CommandResult]) -> bool:
    status, _ = verification_rollup(semgrep, native)
    return status == "blocked"


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
    write_verification_results(target, request, semgrep_result, native_results, actions)
    update_test_matrix_with_results(target, request, semgrep_result, native_results, actions)
    write_loop_run_log(target, request, semgrep_result, native_results, actions)
    write_memory_candidates(target, request, semgrep_result, native_results, actions)

    report = write_execution_report(target, request, actions)
    print(f"executed safe request setup: {request.name}")
    print(f"report: {report}")
    for action in actions:
        print(action)
    if args.fail_on_verify_failure and has_verify_failure(semgrep_result, native_results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
