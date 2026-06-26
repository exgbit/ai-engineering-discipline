"""diff-coverage:改动的代码行有没有被测试**真正执行**到(跨语言)。

把"测试引用了改动的符号"升级成"改动的可执行行被测试执行过",根治符号启发式那几个
漏放(纯模块级改动、同名跨文件等)。

零依赖回退:覆盖率工具没装、或语言不支持 → `available=False`,门禁标 uncovered(不静默
通过),绝不强依赖任何外部工具。覆盖率数据写到临时目录(COVERAGE_FILE 等),不污染目标项目。

已知代价:diff-coverage 会带覆盖率再跑一遍测试,与 native check 的测试各自独立——同一次
execute 内测试跑两遍,有副作用的集成测试会执行两次。这是 opt-in 的性能取舍(默认不开)。
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

# @@ -a,b +c,d @@ :取新文件改动起始行 c 和行数 d
_HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def changed_line_numbers(target: Path, code_files: list[str], base_ref: str = "HEAD") -> dict[str, set[int]]:
    """每个改动文件的新增/改动行号集合(git diff --unified=0)。"""
    result: dict[str, set[int]] = {}
    for f in code_files:
        lines: set[int] = set()
        try:
            r = subprocess.run(
                ["git", "-C", str(target), "diff", base_ref, "--unified=0", "--", f],
                capture_output=True, text=True, timeout=30,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        for line in r.stdout.splitlines():
            m = _HUNK_RE.match(line)
            if m:
                start = int(m.group(1))
                count = int(m.group(2)) if m.group(2) is not None else 1
                for ln in range(start, start + count):
                    lines.add(ln)
        if not lines:
            # untracked / 新文件:git diff HEAD 无 hunk → 整文件行号视作改动行(交叉时
            # & executable 会过滤掉非可执行行;与 changed_code_symbols 的回退一致)
            try:
                n = len((target / f).read_text(encoding="utf-8", errors="ignore").splitlines())
                lines = set(range(1, n + 1))
            except OSError:
                pass
        if lines:
            result[f] = lines
    return result


def _run(cmd: list[str], target: Path, env=None, timeout: int = 600):
    try:
        return subprocess.run(cmd, cwd=str(target), capture_output=True, text=True,
                              timeout=timeout, env=env)
    except (OSError, subprocess.SubprocessError):
        return None


def _rel(path: str, target: Path) -> str:
    try:
        if os.path.isabs(path):
            return os.path.relpath(path, str(target)).replace(os.sep, "/")
    except ValueError:
        pass
    p = path.replace(os.sep, "/")
    return p[2:] if p.startswith("./") else p


# 每个收集器返回 {relpath: (executed_lines:set, executable_lines:set)} 或 (None, reason)

def _coverage_python(target: Path):
    if not shutil.which("coverage"):
        return None, "coverage.py not installed (pip install coverage)"
    with tempfile.TemporaryDirectory() as td:
        env = dict(os.environ, COVERAGE_FILE=str(Path(td) / "cov.data"))
        test_mod = "pytest" if shutil.which("pytest") else "unittest"
        run_cmd = ["coverage", "run", "-m", "pytest"] if test_mod == "pytest" \
            else ["coverage", "run", "-m", "unittest", "discover"]
        run_result = _run(run_cmd, target, env=env)
        if run_result is None or run_result.returncode != 0:
            return None, "tests did not pass (coverage not trusted)"
        if not (Path(td) / "cov.data").exists():
            return None, "coverage produced no data"
        jpath = Path(td) / "cov.json"
        out = _run(["coverage", "json", "-o", str(jpath)], target, env=env)
        if out is None or not jpath.exists():
            return None, "coverage json failed"
        try:
            data = json.loads(jpath.read_text(encoding="utf-8"))
        except ValueError:
            return None, "coverage json parse error"
    covered = {}
    for path, info in (data.get("files") or {}).items():
        ex = set(info.get("executed_lines") or [])
        miss = set(info.get("missing_lines") or [])
        covered[_rel(path, target)] = (ex, ex | miss)
    return covered, "coverage.py"


def _is_python_project(target: Path) -> bool:
    if any((target / f).exists() for f in (
        "pyproject.toml", "setup.py", "setup.cfg", "tox.ini", "requirements.txt", "pytest.ini", "conftest.py",
    )):
        return True
    # 无配置文件时,tests/ 或 test/ 下有 Python 测试文件也算(与 detect_native_commands 口径一致)
    return any(
        base.is_dir() and (any(base.rglob("test_*.py")) or any(base.rglob("*_test.py")))
        for base in (target / "tests", target / "test")
    )


def collect_coverage(target: Path):
    """探测项目语言并收集行覆盖。返回 ({relpath:(executed,executable)}, tool) 或 (None, reason)。"""
    if _is_python_project(target):
        return _coverage_python(target)
    if (target / "go.mod").exists():
        return _coverage_go(target)
    if (target / "package.json").exists():
        return _coverage_js(target)
    if (target / "pom.xml").exists() or (target / "build.gradle").exists() \
            or (target / "build.gradle.kts").exists():
        return _coverage_java(target)
    return None, "no supported coverage tool for this project type"


def _parse_go_coverprofile(text: str):
    """go test -coverprofile 文本:`import-path/file.go:sl.sc,el.ec numstmt count`。"""
    covered: dict = {}
    for line in text.splitlines():
        if not line.strip() or line.startswith("mode:"):
            continue
        try:
            loc, _stmts, count = line.rsplit(" ", 2)
            file_part, rng = loc.rsplit(":", 1)
            sl = int(rng.split(",")[0].split(".")[0])
            el = int(rng.split(",")[1].split(".")[0])
            cnt = int(count)
        except (ValueError, IndexError):
            continue
        ex, exe = covered.setdefault(file_part, (set(), set()))
        for ln in range(sl, el + 1):
            exe.add(ln)
            if cnt > 0:
                ex.add(ln)
    return covered


def _coverage_go(target: Path):
    if not shutil.which("go"):
        return None, "go not installed"
    with tempfile.TemporaryDirectory() as td:
        prof = Path(td) / "cover.out"
        run_result = _run(["go", "test", "-coverprofile=" + str(prof), "./..."], target)
        if run_result is None or run_result.returncode != 0:
            return None, "go test did not pass (coverage not trusted)"
        if not prof.exists():
            return None, "go test produced no coverage profile"
        return _parse_go_coverprofile(prof.read_text(encoding="utf-8", errors="ignore")), "go cover"


def _parse_istanbul(data: dict, target: Path):
    """istanbul coverage-final.json:statementMap(行)+ s(命中次数)。"""
    covered: dict = {}
    for path, info in data.items():
        smap = info.get("statementMap") or {}
        hits = info.get("s") or {}
        ex, exe = set(), set()
        for sid, loc in smap.items():
            ln = (loc.get("start") or {}).get("line")
            if ln is None:
                continue
            exe.add(ln)
            if hits.get(sid, 0):
                ex.add(ln)
        covered[_rel(path, target)] = (ex, exe)
    return covered


def _coverage_js(target: Path):
    if shutil.which("c8"):
        runner = ["c8", "--reporter=json", "--reports-dir", "{out}", "npm", "test"]
    elif shutil.which("nyc"):
        runner = ["nyc", "--reporter=json", "--report-dir", "{out}", "npm", "test"]
    else:
        return None, "no js coverage tool (c8/nyc) installed"
    with tempfile.TemporaryDirectory() as td:
        run_result = _run([a.replace("{out}", td) for a in runner], target)
        if run_result is None or run_result.returncode != 0:
            return None, "js tests did not pass (coverage not trusted)"
        final = Path(td) / "coverage-final.json"
        if not final.exists():
            # 工具忽略 --reports-dir 时会写到默认 coverage/ 目录;只认本次新生成的
            # (mtime 不早于临时目录创建时间),避免捡到上次遗留的旧文件当成本次覆盖(假覆盖)。
            alt = target / "coverage" / "coverage-final.json"
            if alt.exists() and alt.stat().st_mtime >= Path(td).stat().st_mtime:
                final = alt
        if not final.exists():
            return None, "no coverage-final.json produced"
        try:
            data = json.loads(final.read_text(encoding="utf-8"))
        except ValueError:
            return None, "coverage-final.json parse error"
    return _parse_istanbul(data, target), "istanbul"


def _parse_jacoco(xml_text: str):
    """jacoco.xml:<sourcefile><line nr= mi= ci=/></sourcefile>。ci>0 覆盖,mi+ci 都是可执行行。"""
    root = ET.fromstring(xml_text)
    covered: dict = {}
    for pkg in root.iter("package"):
        pkg_name = pkg.get("name", "")
        for sf in pkg.findall("sourcefile"):
            name = sf.get("name", "")
            rel = (pkg_name + "/" + name) if pkg_name else name
            ex, exe = set(), set()
            for ln in sf.findall("line"):
                try:
                    nr = int(ln.get("nr", 0))
                    ci = int(ln.get("ci", 0))
                except (TypeError, ValueError):
                    continue
                exe.add(nr)
                if ci > 0:
                    ex.add(nr)
            covered[rel] = (ex, exe)
    return covered


def _coverage_java(target: Path):
    if shutil.which("mvn"):
        _run(["mvn", "-q", "test", "jacoco:report"], target)
    elif (target / "gradlew").exists() or shutil.which("gradle"):
        gw = "./gradlew" if (target / "gradlew").exists() else "gradle"
        _run([gw, "test", "jacocoTestReport"], target)
    else:
        return None, "no java build tool (mvn/gradle) installed"
    reports = list(target.rglob("jacoco.xml"))
    if not reports:
        return None, "no jacoco.xml produced (is the jacoco plugin configured?)"
    merged: dict = {}  # 多模块工程每个 module 一个 jacoco.xml,合并所有,别只取第一个
    for rep in reports:
        try:
            part = _parse_jacoco(rep.read_text(encoding="utf-8", errors="ignore"))
        except ET.ParseError:
            continue
        for k, (ex, exe) in part.items():
            mex, mexe = merged.get(k, (set(), set()))
            merged[k] = (mex | ex, mexe | exe)
    if not merged:
        return None, "jacoco.xml parse error"
    return merged, "jacoco"


def _match_path(covered: dict, f: str):
    """覆盖率报告的路径可能带 module / 绝对 / package 前缀;用**按路径段边界**的后缀匹配回退,
    取最长匹配避免歧义(否则 foobar.go 会误匹配 bar.go,把别的文件覆盖率张冠李戴)。"""
    cf = "/" + f
    best = None
    for k, v in covered.items():
        ck = "/" + k
        if ck.endswith(cf) or cf.endswith(ck):
            if best is None or len(k) > best[0]:
                best = (len(k), v)
    return best[1] if best else None


def diff_coverage_result(target: Path, code_files: list[str], base_ref: str = "HEAD") -> dict:
    """交叉:改动的可执行行里没被测试执行到的(gap)。
    返回 {available, tool, total_changed_executable, covered, covered_ratio, uncovered_lines, reason}。"""
    changed = changed_line_numbers(target, code_files, base_ref)
    if not changed:
        return {"available": True, "tool": None, "total_changed_executable": 0,
                "covered": 0, "covered_ratio": 1.0, "uncovered_lines": {}}
    covered, tool = collect_coverage(target)
    if covered is None:
        return {"available": False, "reason": tool,
                "total_changed_executable": 0, "uncovered_lines": {}}
    uncovered: dict[str, list[int]] = {}
    total = 0
    cov = 0
    for f, lines in changed.items():
        info = covered.get(f) or _match_path(covered, f)
        if info is None:
            # 改动文件完全不在覆盖率报告里 → 没有任何测试执行过它(常见:全新未测文件)。
            # 不能算"已覆盖":整文件的改动行都记为未覆盖(粗略高估,但方向对,不静默放行)。
            miss = sorted(lines)
            total += len(miss)
            uncovered[f] = miss
            continue
        executed, executable = info
        # 只看改动行里的**可执行**行(注释/空行/纯声明不算),避免假 gap
        changed_exec = lines & executable
        total += len(changed_exec)
        cov += len(changed_exec & executed)
        miss = sorted(changed_exec - executed)
        if miss:
            uncovered[f] = miss
    return {"available": True, "tool": tool, "total_changed_executable": total,
            "covered": cov, "covered_ratio": (cov / total) if total else 1.0,
            "uncovered_lines": uncovered}


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: diff_coverage.py <target> [changed_file ...]", file=sys.stderr)
        return 2
    target = Path(sys.argv[1]).expanduser().resolve()
    files = sys.argv[2:]
    if not files:
        # 默认取 git 改动的代码文件
        try:
            r = subprocess.run(["git", "-C", str(target), "status", "--porcelain"],
                              capture_output=True, text=True, timeout=30)
            files = [ln[3:].strip().split(" -> ")[-1] for ln in r.stdout.splitlines() if ln[3:].strip()]
        except (OSError, subprocess.SubprocessError):
            files = []
    res = diff_coverage_result(target, files)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
