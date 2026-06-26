#!/usr/bin/env python3
"""知识图谱影响分析的端到端冒烟:验证 codebase-memory 算跨文件 blast radius +
受影响接口 ∩ test-index 盲区。固化两次人工端到端验证(Python + JS)防回归。

需要 codebase-memory 二进制;没装则 SKIP(CI 无二进制不失败)。
用法:python scripts/graph_smoke_test.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"GRAPH SMOKE FAIL: {msg}")


def _git(target: Path, *args: str) -> None:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "-C", str(target), *args], capture_output=True, text=True, env=env)


def _assert_closure(target: Path, upstream: list[str], untested_sym: str, tested_sym: str) -> None:
    """改了底层函数后:upstream 应在 blast radius(跨文件传递性);untested_sym 受影响且没测;
    tested_sym 受影响但有真测试(不在 untested,且没被注释/字符串里的同名污染)。"""
    from build_test_index import refresh_test_index
    from code_graph import CACHE_DIR, detect_changes, impacted_symbol_names, impacted_untested, index_repository
    proj = (index_repository(target) or {}).get("project", "")
    try:
        refresh_test_index(target, [])
        names = impacted_symbol_names(detect_changes(target))
        for up in upstream:
            check(up in names, f"{target.name}: {up} should be in blast radius (transitive), got {names}")
        untested = impacted_untested(target, names)
        check(untested_sym in untested,
              f"{target.name}: {untested_sym} should be affected-but-untested, got {untested}")
        check(tested_sym not in untested,
              f"{target.name}: {tested_sym} has a real test, should not be untested, got {untested}")
    finally:
        if proj:
            (CACHE_DIR / f"{proj}.db").unlink(missing_ok=True)


def _python_case(td: Path) -> None:
    t = td / "py"
    (t / "order").mkdir(parents=True)
    (t / "tests").mkdir()
    (t / "order" / "__init__.py").write_text("", encoding="utf-8")
    (t / "order" / "core.py").write_text(
        "def validate_order(o):\n    return bool(o)\n\n"
        "def create_order(o):\n    return validate_order(o)\n", encoding="utf-8")
    (t / "order" / "payment.py").write_text(
        "from order.core import validate_order\n\n"
        "def charge(o):\n    return validate_order(o)\n\n"
        "def refund(o):\n    return False\n", encoding="utf-8")
    # 只真测 create_order;charge 仅出现在 docstring/注释/字符串(剥离后必须仍判盲区)
    (t / "tests" / "test_core.py").write_text(
        "from order.core import create_order\n\n"
        "def test_create():\n"
        "    '''exercises create_order; mentions charge and refund (not tested here)'''\n"
        "    # charge refund in a comment\n"
        "    note = 'charge refund in a string'\n"
        "    assert create_order({'x': 1})\n", encoding="utf-8")
    _git(t, "init", "-q")
    _git(t, "add", "-A")
    _git(t, "commit", "-qm", "init")
    # 改底层 validate_order(create_order、charge 传递性依赖它)
    (t / "order" / "core.py").write_text(
        "def validate_order(o):\n    return bool(o) and len(o) > 0\n\n"
        "def create_order(o):\n    return validate_order(o)\n", encoding="utf-8")
    _assert_closure(t, ["create_order", "charge"], "charge", "create_order")


def _js_case(td: Path) -> None:
    t = td / "js"
    (t / "src").mkdir(parents=True)
    (t / "tests").mkdir()
    (t / "src" / "core.js").write_text(
        "export function validateOrder(o){ return !!o; }\n"
        "export function createOrder(o){ return validateOrder(o); }\n", encoding="utf-8")
    (t / "src" / "payment.js").write_text(
        "import { validateOrder } from './core.js';\n"
        "export function charge(o){ return validateOrder(o); }\n"
        "export function refund(o){ return false; }\n", encoding="utf-8")
    # 只真测 createOrder;charge 在 // 行注释 / 块注释 / 模板字符串(剥离后必须仍判盲区)
    (t / "tests" / "core.test.js").write_text(
        "import { createOrder } from '../src/core.js';\n"
        "// charge refund in a line comment\n"
        "/* charge refund in a block comment */\n"
        "test('c', () => { const s = `charge refund template`; createOrder({x:1}); });\n",
        encoding="utf-8")
    _git(t, "init", "-q")
    _git(t, "add", "-A")
    _git(t, "commit", "-qm", "init")
    (t / "src" / "core.js").write_text(
        "export function validateOrder(o){ return !!o && Object.keys(o).length>0; }\n"
        "export function createOrder(o){ return validateOrder(o); }\n", encoding="utf-8")
    _assert_closure(t, ["createOrder", "charge"], "charge", "createOrder")


def main() -> int:
    from code_graph import graph_available
    if not graph_available():
        print("GRAPH SMOKE SKIP: codebase-memory not installed (build the binary to run this)")
        return 0
    with tempfile.TemporaryDirectory() as td:
        _python_case(Path(td))
        _js_case(Path(td))
    print(f"GRAPH SMOKE OK on {sys.platform} "
          "(Python + JS: cross-file blast radius + affected-but-untested, stripping enforced)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
