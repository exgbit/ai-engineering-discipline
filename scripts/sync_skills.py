#!/usr/bin/env python3
"""把顶层权威源同步到两份 skill 副本,并校验无漂移。

背景:装到目标项目的 skill 必须自带脚本/参考资料(Claude Code 从 .claude/skills、
Codex 从 .codex/skills 运行时调用),所以副本的存在是运行时硬需求。本工具消除的不是
"副本",而是"副本靠人手同步导致的漂移":顶层为唯一权威源,副本由本工具单向生成。

权威源(框架顶层):
  scripts/                     10 个核心 .py(见 SCRIPT_FILES)
  presets/                     *.json
  templates/ examples/ claude-code-commands/
  CLAUDE.md  adapters/default-stack.json
副本(每份 skill 内):
  scripts/  presets/  references/...

策略:以副本现有文件为驱动,从顶层同名源覆盖。副本独有、无顶层源的文件
(references/operation.md、SKILL.md、agents/openai.yaml)自动跳过。SCRIPT_FILES
与 SINGLE_FILES 为必须项,缺失会被创建(sync)或报为漂移(--check)。

用法:
  python scripts/sync_skills.py            # 同步(写副本)
  python scripts/sync_skills.py --check    # 只校验,有漂移则 exit 1(供 CI)
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = [
    ROOT / "claude-code-skills" / "ai-engineering-discipline",
    ROOT / "skills" / "ai-engineering-discipline",
]

# 顶层 scripts/ → skill/scripts/(必须项,显式清单)
SCRIPT_FILES = [
    "ai_discipline.py",
    "run_request.py",
    "execute_request.py",
    "install_default_adapters.py",
    "doctor.py",
    "init_project.py",
    "inspect_project.py",
    "build_test_index.py",
    "diff_coverage.py",
    "code_graph.py",
]

# 单文件映射:顶层相对路径 → skill 内相对路径(必须项)
SINGLE_FILES = {
    "CLAUDE.md": "references/CLAUDE.md",
    "adapters/default-stack.json": "references/default-stack.json",
}

# 源驱动(全量同步):skill 内相对目录 ← 顶层源目录。顶层有的副本必须都有,
# 新增文件也会被同步/在 --check 中报漂移。
SRC_DRIVEN_DIRS = {
    "presets": "presets",
    "references/claude-code-commands": "claude-code-commands",
}

# 副本驱动(精选镜像,只刷新副本已存在的文件):references 下是有意精选的参考资料
# (如 examples 只收录部分),不应把顶层目录全量推过去。
DST_DRIVEN_DIRS = {
    "references/templates": "templates",
    "references/examples": "examples",
}

# SKILL.md 平台路径互斥:该平台目录下的 SKILL.md 不应出现对方平台的安装路径
FORBIDDEN_IN_SKILL_MD = {
    "claude-code-skills": ".codex/skills",
    "skills": ".claude/skills",
}


def planned_pairs(skill: Path) -> list[tuple[Path, Path]]:
    """返回该 skill 的 (顶层源文件, 副本目标文件) 列表;仅含顶层源存在者。"""
    pairs: list[tuple[Path, Path]] = []
    for name in SCRIPT_FILES:
        src = ROOT / "scripts" / name
        if src.exists():
            pairs.append((src, skill / "scripts" / name))
    for src_rel, dst_rel in SINGLE_FILES.items():
        src = ROOT / src_rel
        if src.exists():
            pairs.append((src, skill / dst_rel))
    for dst_dir_rel, src_dir_rel in SRC_DRIVEN_DIRS.items():
        src_dir = ROOT / src_dir_rel
        if not src_dir.is_dir():
            continue
        # 源驱动:顶层每个文件都必须同步到副本(dst 不存在则 sync 创建 / --check 报漂移)
        for src_file in sorted(src_dir.rglob("*")):
            if src_file.is_file():
                pairs.append((src_file, skill / dst_dir_rel / src_file.relative_to(src_dir)))
    for dst_dir_rel, src_dir_rel in DST_DRIVEN_DIRS.items():
        dst_dir = skill / dst_dir_rel
        src_dir = ROOT / src_dir_rel
        if not dst_dir.is_dir():
            continue
        # 副本驱动:只刷新副本里已存在、且顶层有同名源的文件
        for dst_file in sorted(dst_dir.rglob("*")):
            if not dst_file.is_file():
                continue
            src_file = src_dir / dst_file.relative_to(dst_dir)
            if src_file.exists():
                pairs.append((src_file, dst_file))
    return pairs


def orphan_files(skill: Path) -> list[Path]:
    """副本里存在、但顶层源已无对应的文件(孤儿:源端删除/改名后副本残留)。只查"应当全等"
    的受管范围:SCRIPT_FILES 的 scripts/*.py 和 SRC_DRIVEN_DIRS 的整目录。DST_DRIVEN
    (templates/examples 是精选子集)与副本独有文件(SKILL.md / references/operation.md / agents/)不算。"""
    orphans: list[Path] = []
    scripts_dir = skill / "scripts"
    if scripts_dir.is_dir():
        for dst_file in sorted(scripts_dir.glob("*.py")):
            if dst_file.name not in SCRIPT_FILES:
                orphans.append(dst_file)
    for dst_dir_rel, src_dir_rel in SRC_DRIVEN_DIRS.items():
        dst_dir = skill / dst_dir_rel
        src_dir = ROOT / src_dir_rel
        if not dst_dir.is_dir():
            continue
        for dst_file in sorted(dst_dir.rglob("*")):
            if dst_file.is_file() and not (src_dir / dst_file.relative_to(dst_dir)).exists():
                orphans.append(dst_file)
    return orphans


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只校验,有漂移则 exit 1")
    args = parser.parse_args()

    drift: list[str] = []
    updated: list[str] = []
    errors: list[str] = []

    for skill in SKILLS:
        if not skill.is_dir():
            errors.append(f"skill 目录不存在: {skill}")
            continue
        for src, dst in planned_pairs(skill):
            if dst.exists() and filecmp.cmp(src, dst, shallow=False):
                continue
            label = f"{dst.relative_to(ROOT)} ⇐ {src.relative_to(ROOT)}"
            if args.check:
                drift.append(label)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                updated.append(label)

        # 孤儿:副本多出、顶层源已无的文件(否则源端删除/改名后副本静默残留,--check 假绿)
        for orphan in orphan_files(skill):
            label = f"{orphan.relative_to(ROOT)} (orphan: 顶层源已无对应)"
            if args.check:
                drift.append(label)
            else:
                orphan.unlink()
                updated.append(f"remove orphan: {orphan.relative_to(ROOT)}")

        skill_md = skill / "SKILL.md"
        if skill_md.exists():
            text = skill_md.read_text(encoding="utf-8")
            forbidden = FORBIDDEN_IN_SKILL_MD.get(skill.parent.name)
            if forbidden and forbidden in text:
                errors.append(f"{skill_md.relative_to(ROOT)} 含错误平台路径 '{forbidden}'")

    for line in errors:
        print(f"ERROR: {line}")
    if args.check:
        for line in drift:
            print(f"DRIFT: {line}")
        if drift:
            print(f"\n{len(drift)} 处副本与顶层源漂移。运行 `python scripts/sync_skills.py` 修复。")
        elif not errors:
            print("no drift: 所有 skill 副本与顶层源一致。")
    else:
        for line in updated:
            print(f"sync: {line}")
        print(f"\n同步完成,更新 {len(updated)} 个文件。" if updated else "无需更新,已全部一致。")

    return 1 if errors or (args.check and drift) else 0


if __name__ == "__main__":
    raise SystemExit(main())
