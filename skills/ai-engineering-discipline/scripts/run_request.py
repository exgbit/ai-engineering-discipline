#!/usr/bin/env python3
"""Create a managed AI engineering request for a target project."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_PRESETS_DIR = Path(__file__).resolve().parents[1] / "presets"
REPO_PRESETS_DIR = ROOT / "presets"
PRESETS_DIR = LOCAL_PRESETS_DIR if LOCAL_PRESETS_DIR.exists() else REPO_PRESETS_DIR


TASK_LOOPS = {
    "feature": "feature-slice-loop",
    "bugfix": "bugfix-loop",
    "refactor": "refactor-loop",
    "migration": "migration-loop",
    "docs": "docs-loop",
    "verify": "verify-loop",
    "memory": "memory-loop",
}

DEFAULT_RISK = {
    "feature": "medium",
    "bugfix": "medium",
    "refactor": "medium",
    "migration": "high",
    "docs": "low",
    "verify": "medium",
    "memory": "low",
}
PRESET_ALIASES = {"auto", "default", "standard"}


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


def run_script(script: Path, target: Path) -> None:
    subprocess.run([sys.executable, str(script), str(target)], check=True)


def skill_script(name: str) -> Path:
    repo_script = ROOT / "skills" / "ai-engineering-discipline" / "scripts" / name
    local_script = Path(__file__).resolve().parent / name
    if repo_script.exists():
        return repo_script
    if local_script.exists():
        return local_script
    raise SystemExit(f"Cannot locate required script: {name}")


def load_preset(task: str, risk: str, preset_name: str | None) -> dict[str, object]:
    requested = preset_name.strip().lower() if preset_name else ""
    name = None if requested in PRESET_ALIASES else requested
    name = name or f"{task}-{risk}"
    path = PRESETS_DIR / f"{name}.json"
    if not path.exists():
        available = ", ".join(sorted(p.stem for p in PRESETS_DIR.glob("*.json")))
        raise SystemExit(f"Preset not found: {name}. Available presets: {available}")
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_requirement_source(source: Path, target: Path) -> Path:
    source = source.expanduser()
    if source.is_absolute():
        return source.resolve()
    candidates = [
        (Path.cwd() / source).resolve(),
        (target / source).resolve(),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def unique_copy_destination(destination: Path, used: set[Path]) -> Path:
    if destination not in used and not destination.exists():
        return destination
    suffix = 2
    while True:
        candidate = destination.with_name(f"{destination.stem}-{suffix}{destination.suffix}")
        if candidate not in used and not candidate.exists():
            return candidate
        suffix += 1


def unique_copy_root(destination: Path, used: set[Path]) -> Path:
    if destination not in used and not destination.exists():
        return destination
    suffix = 2
    while True:
        candidate = destination.with_name(f"{destination.name}-{suffix}")
        if candidate not in used and not candidate.exists():
            return candidate
        suffix += 1


def copy_requirements(requirements: list[Path], target: Path) -> list[Path]:
    dest_dir = target / "docs" / "requirements"
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    seen_sources: set[Path] = set()
    reserved_destinations: set[Path] = set()
    for source in requirements:
        raw_source = source
        source = resolve_requirement_source(source, target)
        resolved_source = source.resolve()
        if resolved_source in seen_sources:
            continue
        seen_sources.add(resolved_source)
        if not source.exists():
            if raw_source.expanduser().is_absolute():
                raise SystemExit(f"Requirement path does not exist: {source}")
            raise SystemExit(
                "Requirement path does not exist: "
                f"{raw_source} (tried {Path.cwd() / raw_source} and {target / raw_source})"
            )
        if source == dest_dir or path_is_relative_to(source, dest_dir):
            if source.is_dir():
                for item in sorted(source.rglob("*")):
                    if item.is_file() and item.suffix.lower() in {".md", ".txt", ".rst", ".json", ".yaml", ".yml"}:
                        copied.append(item)
            else:
                copied.append(source)
            continue
        if source.is_dir():
            dst_root = unique_copy_root((dest_dir / source.name).resolve(), reserved_destinations)
            reserved_destinations.add(dst_root)
            for item in sorted(source.rglob("*")):
                if item.is_file() and item.suffix.lower() in {".md", ".txt", ".rst", ".json", ".yaml", ".yml"}:
                    rel = item.relative_to(source)
                    dst = dst_root / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dst)
                    reserved_destinations.add(dst.resolve())
                    copied.append(dst)
        else:
            dst = unique_copy_destination((dest_dir / source.name).resolve(), reserved_destinations)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dst)
            reserved_destinations.add(dst)
            copied.append(dst)
    return copied


def ensure_loop(target: Path, task: str) -> Path:
    loop_name = TASK_LOOPS[task]
    loop_path = target / "docs" / "loops" / f"{loop_name}.md"
    if loop_path.exists():
        return loop_path
    loop_path.parent.mkdir(parents=True, exist_ok=True)
    template = target / "docs" / "loops" / "loop-template.md"
    if template.exists():
        content = template.read_text(encoding="utf-8")
    else:
        content = "# Loop Template\n\n"
    loop_path.write_text(
        "<!-- ai-engineering:generated -->\n" + content.replace("# Loop Template", f"# {loop_name}"),
        encoding="utf-8",
    )
    return loop_path


def render_json_block(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def write_request(
    target: Path,
    task: str,
    name: str,
    copied_requirements: list[Path],
    notes: str,
    execute: bool,
    preset: dict[str, object],
) -> Path:
    request_dir = target / "docs" / "ai-engineering"
    request_dir.mkdir(parents=True, exist_ok=True)
    request_path = request_dir / "current-request.md"
    slug = slugify(name)
    spec_path = target / "docs" / "specs" / f"{slug}.md"
    loop_config = preset.get("loop", {})
    runbook = loop_config.get("runbook") if isinstance(loop_config, dict) else None
    if isinstance(runbook, str) and runbook:
        loop_path = target / "docs" / "loops" / f"{runbook}.md"
        if not loop_path.exists():
            loop_path = ensure_loop(target, task)
    else:
        loop_path = ensure_loop(target, task)
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    req_lines = "\n".join(
        f"- `{p.relative_to(target)}`" if path_is_relative_to(p, target) else f"- `{p}`"
        for p in copied_requirements
    ) or "- None"

    request_path.write_text(
        f"""# Current AI Engineering Request

Created: {now}

## Task

- Type: `{task}`
- Name: `{name}`
- Execute implementation now: `{str(execute).lower()}`
- Preset: `{preset.get("name", "unknown")}`
- Risk: `{preset.get("risk", "unknown")}`

## Requirement Sources

{req_lines}

## Target Artifacts

- Spec: `{spec_path.relative_to(target)}`
- Loop: `{loop_path.relative_to(target)}`
- Verify matrix: `docs/verify/test-matrix.md`
- Memory: `docs/memory/`

## Resolved Framework Parameters

The user should not provide low-level framework parameters. This preset resolves them.

### Spec

```json
{render_json_block(preset.get("spec", {}))}
```

### Loop

```json
{render_json_block(preset.get("loop", {}))}
```

### Verify

```json
{render_json_block(preset.get("verify", {}))}
```

### Memory

```json
{render_json_block(preset.get("memory", {}))}
```

## Instructions For Orchestrator

Use `ai-engineering-discipline` as the only user-facing workflow.

1. Run `execute_request.py` first to convert this request into concrete spec, loop, verify, and memory artifacts.
2. Use the resolved Spec parameters; do not ask the user for Spec Kit flags unless blocked.
3. Use `ai-spec` internally to import the requirement sources and create/update the target spec.
4. Use the resolved Loop parameters; do not ask the user for LangGraph/state-machine flags unless blocked.
5. Use `ai-loop` internally to finalize the selected loop.
6. Do not implement code until the spec and loop are ready.
7. If `Execute implementation now` is `true`, implement in small scoped steps.
8. Use the resolved Verify parameters; run Semgrep and native checks as applicable.
9. Use `ai-verify` internally to run evidence gates.
10. Use the resolved Memory parameters.
11. Use `ai-memory` internally to update only real, evidence-backed memory.

## Additional Notes

{notes or "None"}
""",
        encoding="utf-8",
    )
    return request_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", help="Target project path.")
    parser.add_argument("--task", choices=sorted(TASK_LOOPS), required=True)
    parser.add_argument("--name", required=True, help="Feature/bugfix/request name.")
    parser.add_argument("--risk", choices=["low", "medium", "high"], help="Risk level. Defaults by task type.")
    parser.add_argument(
        "--preset",
        help="Preset name, e.g. feature-medium. Use standard/default/auto to select the task+risk default.",
    )
    parser.add_argument(
        "--requirements",
        action="append",
        default=[],
        help=(
            "Requirement file or directory. Can be passed multiple times. "
            "Relative paths are resolved from the current directory, then the target project."
        ),
    )
    parser.add_argument("--notes", default="", help="Additional instructions.")
    parser.add_argument("--execute", action="store_true", help="Allow implementation after spec and loop are ready.")
    parser.add_argument("--skip-init", action="store_true", help="Do not run init_project/inspect_project.")
    args = parser.parse_args()

    target = Path(args.target).expanduser().resolve()
    if not target.exists() or not target.is_dir():
        raise SystemExit(f"Target project does not exist: {target}")

    risk = args.risk or DEFAULT_RISK[args.task]
    preset = load_preset(args.task, risk, args.preset)

    if not args.skip_init:
        run_script(skill_script("init_project.py"), target)
        run_script(skill_script("inspect_project.py"), target)

    copied = copy_requirements([Path(p) for p in args.requirements], target)
    request_path = write_request(target, args.task, args.name, copied, args.notes, args.execute, preset)

    print(f"wrote: {request_path}")
    print()
    print("Next command:")
    print(f"{sys.executable} {skill_script('execute_request.py')} {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
