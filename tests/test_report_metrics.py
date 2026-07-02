"""第二轮实战评估修复的回归:红灯证据链进终态结果、pilot 指标排除框架产物。"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import ai_discipline  # noqa: E402
import execute_request as er  # noqa: E402


class RedPhaseSummaryTest(unittest.TestCase):
    def test_missing_file_returns_none(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertIsNone(er.red_phase_summary(Path(td)))

    def test_summary_carries_observed_and_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            verify_dir = Path(td) / "docs" / "verify"
            verify_dir.mkdir(parents=True)
            (verify_dir / "red-phase-results.json").write_text(
                '{"created": "2026-07-02 10:00:00", "red_phase_observed": true}',
                encoding="utf-8",
            )
            summary = er.red_phase_summary(Path(td))
            self.assertTrue(summary["observed"])
            self.assertEqual(summary["created"], "2026-07-02 10:00:00")
            self.assertIn("red-phase-results.md", summary["evidence"])


class GitChangedFilesMetricTest(unittest.TestCase):
    def _git(self, cwd, *args):
        subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)

    def test_framework_artifacts_excluded_from_count(self):
        # 指标只数业务改动:docs/.claude 生成产物、data/ 累积文件、bootstrap 根级协议文件都不计入
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._git(root, "init", "-q")
            (root / "app.py").write_text("x = 1\n", encoding="utf-8")
            (root / "docs" / "specs").mkdir(parents=True)
            (root / "docs" / "specs" / "s.md").write_text("spec\n", encoding="utf-8")
            (root / ".claude").mkdir()
            (root / ".claude" / "settings.json").write_text("{}\n", encoding="utf-8")
            (root / "data").mkdir()
            (root / "data" / "run-stats.jsonl").write_text("{}\n", encoding="utf-8")
            (root / "CLAUDE.md").write_text("protocol\n", encoding="utf-8")
            (root / "AGENTS.md").write_text("protocol\n", encoding="utf-8")
            self.assertEqual(ai_discipline.git_changed_files(root), 1)


class ChangedSymbolsForGraphTest(unittest.TestCase):
    def _git(self, cwd, *args):
        subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)

    def test_static_extraction_fills_graph_coloring(self):
        # MCP detect 结果不带改动符号时,静态提取兜底给图着色;只保留图节点集内的符号
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "app.py").write_text(
                "def alpha():\n    return 1\n\n\ndef beta():\n    return 2\n",
                encoding="utf-8",
            )
            self._git(root, "init", "-q")
            self._git(root, "add", ".")
            self._git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
            (root / "app.py").write_text(
                "def alpha():\n    return 10\n\n\ndef beta():\n    return 2\n",
                encoding="utf-8",
            )
            changed = er.changed_symbols_for_graph(root, "HEAD", {"alpha", "beta"})
            self.assertEqual(changed, ["alpha"])
            self.assertEqual(er.changed_symbols_for_graph(root, "HEAD", {"beta"}), [])


if __name__ == "__main__":
    unittest.main()
