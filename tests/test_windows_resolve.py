"""Windows 命令解析的单测(在非 Windows 机器上用 mock 强制 win32 分支)。

Windows 上 npm/pnpm/mvn/gradle/c8/nyc 是 .cmd/.bat shim,subprocess(无 shell)的
CreateProcess 不认 → 必须经 `cmd /c` 启动。resolve_local_command / _resolve_win 负责
把它们解析成可启动形式。这些逻辑只在 win32 触发,故用 mock.patch 模拟平台来锁住。
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import diff_coverage as dc  # noqa: E402
import execute_request as er  # noqa: E402


class ResolveLocalCommandTest(unittest.TestCase):
    def test_posix_passthrough(self):
        with mock.patch.object(er.sys, "platform", "linux"):
            self.assertEqual(er.resolve_local_command(["npm", "run", "test"], Path("/x")),
                             ["npm", "run", "test"])

    def test_windows_cmd_shim_wrapped_via_cmd_c(self):
        with mock.patch.object(er.sys, "platform", "win32"), \
             mock.patch.object(er.shutil, "which", return_value=r"C:\tools\npm.cmd"):
            self.assertEqual(er.resolve_local_command(["npm", "run", "test"], Path("/x")),
                             ["cmd", "/c", r"C:\tools\npm.cmd", "run", "test"])

    def test_windows_exe_uses_full_path_no_cmd(self):
        with mock.patch.object(er.sys, "platform", "win32"), \
             mock.patch.object(er.shutil, "which", return_value=r"C:\go\bin\go.exe"):
            self.assertEqual(er.resolve_local_command(["go", "test", "./..."], Path("/x")),
                             [r"C:\go\bin\go.exe", "test", "./..."])

    def test_windows_unresolvable_returns_unchanged(self):
        with mock.patch.object(er.sys, "platform", "win32"), \
             mock.patch.object(er.shutil, "which", return_value=None):
            self.assertEqual(er.resolve_local_command(["mvn", "test"], Path("/x")), ["mvn", "test"])

    def test_windows_local_gradlew_resolves_to_bat(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            (target / "gradlew.bat").write_text("@echo off\n", encoding="utf-8")
            with mock.patch.object(er.sys, "platform", "win32"):
                got = er.resolve_local_command(["./gradlew", "test"], target)
            self.assertEqual(got, ["cmd", "/c", str(target / "gradlew.bat"), "test"])


class DiffCovResolveWinTest(unittest.TestCase):
    def test_posix_passthrough(self):
        with mock.patch.object(dc.sys, "platform", "linux"):
            self.assertEqual(dc._resolve_win(["c8", "npm", "test"], Path("/x")),
                             ["c8", "npm", "test"])

    def test_windows_c8_cmd_wrapped(self):
        with mock.patch.object(dc.sys, "platform", "win32"), \
             mock.patch.object(dc.shutil, "which", return_value=r"C:\node\c8.cmd"):
            self.assertEqual(dc._resolve_win(["c8", "--reporter=json"], Path("/x")),
                             ["cmd", "/c", r"C:\node\c8.cmd", "--reporter=json"])

    def test_windows_exe_full_path(self):
        with mock.patch.object(dc.sys, "platform", "win32"), \
             mock.patch.object(dc.shutil, "which", return_value=r"C:\go\go.exe"):
            self.assertEqual(dc._resolve_win(["go", "test"], Path("/x")),
                             [r"C:\go\go.exe", "test"])


if __name__ == "__main__":
    unittest.main()
