"""第二轮复盘修复的回归测试。

锁住两个真实逻辑 bug 的修复:
- code_graph._changed_symbols 的 per-file 兜底(原先用跨文件累加集合,导致后续文件漏兜底);
- summarize_metrics.parse_float 对 None(短行 CSV 缺列)的容错。
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import code_graph as cg  # noqa: E402
import summarize_metrics as sm  # noqa: E402


def git(target: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(target), "-c", "user.email=t@t", "-c", "user.name=t", *args],
        check=True, capture_output=True, text=True,
    )


class ParseFloatTest(unittest.TestCase):
    def test_none_value_treated_as_zero(self):
        # 短行 CSV 缺列时 DictReader 给 None;应按空值返回 0.0,不抛 AttributeError
        self.assertEqual(sm.parse_float(None, "spec_coverage_rate"), 0.0)

    def test_percent_and_plain(self):
        self.assertEqual(sm.parse_float("50%"), 0.5)
        self.assertEqual(sm.parse_float("1.5"), 1.5)
        self.assertEqual(sm.parse_float("n/a"), 0.0)


class ChangedSymbolsPerFileTest(unittest.TestCase):
    def test_module_level_change_falls_back_per_file(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            git(target, "init", "-q")
            # file_a:有可提取符号,改其函数体(本文件会贡献 bar)
            (target / "a.py").write_text("def bar():\n    return 1\n", encoding="utf-8")
            # file_b:有 foo,但本次只改 foo 之前的模块级 X(不落在任何 def 行范围,
            # 且 Python 裸赋值不被符号正则识别)→ 必须靠 per-file 整文件兜底才能补出 foo
            (target / "b.py").write_text("X = 1\n\n\ndef foo():\n    return 1\n", encoding="utf-8")
            git(target, "add", "-A")
            git(target, "commit", "-q", "-m", "base")
            (target / "a.py").write_text("def bar():\n    return 2\n", encoding="utf-8")
            (target / "b.py").write_text("X = 2\n\n\ndef foo():\n    return 1\n", encoding="utf-8")

            syms = cg._changed_symbols(target, ["a.py", "b.py"], "HEAD")
            # a.py 贡献 bar;b.py 只有模块级改动 → 本文件兜底应补 foo。
            # 修复前 foo 会因「全局集合已非空」而被漏掉。
            self.assertIn("bar", syms)
            self.assertIn("foo", syms)


if __name__ == "__main__":
    unittest.main()
