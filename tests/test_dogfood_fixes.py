"""Dogfood 端到端测试暴露问题的回归测试。

- detect_native_commands:最小 Python 项目(无 pyproject/pytest.ini,只有 tests/)
  也应识别出测试命令,否则测试闸与 diff-coverage 被静默跳过。
- code_graph.impacted_symbol_names:bootstrap 把整套框架脚本拷进 .claude/.codex,
  这些不是用户源码,不应计入受影响接口(否则 blast radius 计数虚高且有同名假阳风险)。
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import code_graph as cg  # noqa: E402
import execute_request as er  # noqa: E402


def minimal_request(target: Path) -> "er.ManagedRequest":
    return er.ManagedRequest(
        path=target / "docs" / "ai-engineering" / "current-request.md",
        target=target, task="feature", name="t", execute=False, preset="feature", risk="medium",
        change_base="", requirements=[],
        spec_path=target / "docs" / "specs" / "t.md",
        loop_path=target / "docs" / "loops" / "loop.md",
        verify_matrix_path=target / "docs" / "verify" / "test-matrix.md",
        memory_path=target / "docs" / "memory",
        spec_params={}, loop_params={}, verify_params={}, memory_params={},
    )


class DetectNativeCommandsTest(unittest.TestCase):
    def test_configless_python_project_with_tests_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            (target / "order").mkdir()
            (target / "order" / "core.py").write_text("def f():\n    return 1\n", encoding="utf-8")
            (target / "tests").mkdir()
            (target / "tests" / "test_core.py").write_text(
                "def test_f():\n    assert True\n", encoding="utf-8"
            )
            # 无 pyproject.toml / requirements.txt / pytest.ini
            cmds = er.detect_native_commands(target, minimal_request(target))
            names = [name for name, _ in cmds]
            self.assertTrue(
                any(n in ("python:pytest", "python:unittest") for n in names),
                f"config-less Python project with tests/ should yield a test command, got {names}",
            )

    def test_empty_project_yields_no_python_command(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            (target / "README.md").write_text("hi\n", encoding="utf-8")
            cmds = er.detect_native_commands(target, minimal_request(target))
            names = [name for name, _ in cmds]
            self.assertFalse(any(n.startswith("python:") for n in names))


class CountTestCasesNodeTest(unittest.TestCase):
    def test_node_test_tap_output_is_counted(self):
        # node --test 的 TAP 摘要:此前只认 pytest/unittest,Node 项目用例数恒为 0
        tap = "TAP version 13\nok 1 - a\nok 2 - b\n# tests 9\n# pass 8\n# fail 1\n"
        passed, failed, parsed = er.count_test_cases([
            er.CommandResult(name="node:test", command=[], status="failed",
                             exit_code=1, duration_seconds=0.0, stdout=tap, stderr=""),
        ])
        self.assertTrue(parsed)
        self.assertEqual((passed, failed), (8, 1))

    def test_jest_style_still_counted(self):
        out = "Tests: 1 failed, 7 passed, 8 total\n"
        passed, failed, parsed = er.count_test_cases([
            er.CommandResult(name="node:test", command=[], status="failed",
                             exit_code=1, duration_seconds=0.0, stdout=out, stderr=""),
        ])
        self.assertTrue(parsed)
        self.assertEqual((passed, failed), (7, 1))


class ImpactedSymbolNamesTest(unittest.TestCase):
    def test_framework_artifact_symbols_are_filtered(self):
        result = {"impacted_symbols": [
            {"name": "createRefund", "label": "Function", "file": "order/refund.py"},
            {"name": "executeRequest", "label": "Function",
             "file": ".claude/skills/ai-engineering-discipline/scripts/execute_request.py"},
            {"name": "codexThing", "label": "Function",
             "file": "/abs/target/.codex/skills/ai-spec/scripts/x.py"},
            {"name": "testFunc", "label": "Function", "file": "tests/test_refund.py"},
        ]}
        names = cg.impacted_symbol_names(result)
        self.assertIn("createRefund", names)          # 用户源码,保留
        self.assertNotIn("executeRequest", names)     # .claude 框架副本,过滤
        self.assertNotIn("codexThing", names)         # .codex 框架副本,过滤
        self.assertNotIn("testFunc", names)           # 测试文件,过滤


if __name__ == "__main__":
    unittest.main()
