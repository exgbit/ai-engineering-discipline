"""封装 codebase-memory-mcp CLI:给框架"建知识图谱 + 影响分析(blast radius)"能力。

框架对它是**硬依赖**(用户要求强制安装,见 adapters/default-stack.json 的 impact 层):
- graph_available() 检测二进制,没装则 doctor / 影响分析门禁报错并要求先装。
- 直接调 CLI(`codebase-memory-mcp cli ...`),不依赖 MCP session 加载;首次自动建 cache 目录
  (否则 index 的 persist 会静默失败)。
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

from code_analysis import git_changed_files

CACHE_DIR = Path.home() / ".cache" / "codebase-memory-mcp"
# 与 execute_request.GENERATED 同一标记(不 import,避免与 execute_request 的懒加载形成环)
GENERATED = "<!-- ai-engineering:generated -->"
INSTALL_HINT = (
    "codebase-memory-mcp is required but not installed. Build and install it:\n"
    "  git clone https://github.com/win4r/codebase-memory-mcp-pro && cd codebase-memory-mcp-pro\n"
    "  ./scripts/build.sh && mkdir -p ~/.local/bin && cp build/c/codebase-memory-mcp ~/.local/bin/\n"
    "  claude mcp add codebase-memory -s user -- ~/.local/bin/codebase-memory-mcp"
)


def graph_binary():
    """codebase-memory-mcp 二进制路径(PATH 或 ~/.local/bin);没装返回 None。"""
    found = shutil.which("codebase-memory-mcp")
    if found:
        return found
    local = Path.home() / ".local" / "bin" / "codebase-memory-mcp"
    return str(local) if local.is_file() else None


def graph_available():
    return graph_binary() is not None


def _run(args, timeout=600):
    binary = graph_binary()
    if not binary:
        return None
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)  # 首次必须建,否则 persist 静默失败
        result = subprocess.run(
            [binary, "cli"] + args, capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",  # 二进制输出 UTF-8;非 UTF-8 locale 的 Windows 否则解码失败
        )
    except (OSError, subprocess.SubprocessError):
        return None
    # CLI 把 JSON 结果输出在最后一行(前面是 level=info 日志);不同构建版本可能写
    # stdout 或 stderr,两边都要解析,否则会把可用图谱误判成 None。
    combined = f"{result.stdout}\n{result.stderr}"
    for line in reversed(combined.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except ValueError:
                return None
    return None


def index_repository(target):
    """建/刷新项目知识图谱(新项目也从头建)。返回 {project, status, nodes, edges} 或 None。"""
    return _run(["index_repository", json.dumps({"repo_path": str(Path(target).resolve())})])


def detect_changes(target, since="HEAD", depth=2):
    """先建图拿 project 标识,再 detect_changes:git diff(since)→ 受影响符号 blast radius。
    返回 {impacted_symbols: [...], impacted_count, changed_files, ...} 或 None。"""
    idx = index_repository(target)
    if not idx or not idx.get("project") or idx.get("status") == "error":
        return _static_detect_changes(target, since=since, depth=depth, reason="index_repository failed")
    payload = {"project": idx["project"], "depth": depth, "since": since}
    result = _run(["detect_changes", json.dumps(payload)])
    # 按"过滤后是否还有可用接口"判定,而非原始结果非空:MCP 只看 git diff(不含 untracked),
    # 新建实现文件时它可能只返回测试/模块符号——过滤后为空,同样要回退到静态分析。
    if not result or not impact_graph_data(result)["nodes"]:
        return _static_detect_changes(target, since=since, depth=depth,
                                      reason="detect_changes returned no usable interfaces")
    return result


CODE_EXTS = {".py", ".js", ".jsx", ".ts", ".tsx"}
DEF_RE = re.compile(
    r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?"
    r"(?:def|class|function)\s+([A-Za-z_$][\w$]*)\b"
)
ASSIGN_RE = re.compile(
    r"^\s*(?:export\s+)?(?:default\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*"
    r"(?:async\s+)?(?:\([^)]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>|function\b|class\b)"
)


def _is_code_path(path):
    return Path(path).suffix in CODE_EXTS


def _is_generated_or_vendor(path):
    parts = set(Path(path).parts)
    return bool(parts & {
        "node_modules", "vendor", "dist", "build", "target", ".git", "__pycache__",
        ".claude", ".codex", ".github",  # 框架装进目标项目的产物,不是用户源码
    })


def _is_framework_artifact_path(path):
    """框架装进目标项目的目录(skill 副本 / 命令 / docs / CI)——不是用户源码,不应计入受影响接口。
    bootstrap 会把整套框架脚本拷进 .claude/.codex,否则知识图谱会把它们算进 blast radius。"""
    p = "/" + str(path or "").replace("\\", "/").strip("/")
    return any(seg in p for seg in ("/.claude/", "/.codex/", "/.github/", "/docs/"))


def _git_lines(target, args):
    try:
        result = subprocess.run(
            ["git", "-C", str(Path(target).resolve()), *args],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    return result.stdout.splitlines()


def _symbol_from_line(line):
    match = DEF_RE.match(line) or ASSIGN_RE.match(line)
    return match.group(1) if match else None


def _line_indent(line):
    return len(line) - len(line.lstrip(" "))


def _extract_defs(path):
    try:
        lines = Path(path).read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []
    starts = []
    for idx, line in enumerate(lines):
        name = _symbol_from_line(line)
        if name:
            starts.append((idx, name, _line_indent(line)))
    defs = []
    for pos, (idx, name, indent) in enumerate(starts):
        end = len(lines)
        for next_idx, _, next_indent in starts[pos + 1:]:
            if next_indent <= indent:
                end = next_idx
                break
        defs.append({
            "name": name,
            "file": str(path),
            "start": idx + 1,
            "end": end,
            "body": "\n".join(lines[idx:end]),
        })
    return defs


def _changed_files(target, since):
    """改动的业务代码文件。与测试配套门禁同口径(git_changed_files:diff + status,
    含 untracked/staged)——否则新建文件的功能开发对图谱不可见,必撞 impact 闸。
    测试文件排除:测试自身是守护者,不是受影响接口。"""
    files = git_changed_files(Path(target), since or "HEAD")
    if files is None:
        return []
    return [
        f for f in files
        if _is_code_path(f) and not _is_generated_or_vendor(f) and not _looks_like_test(f)
    ]


def _changed_symbols(target, changed_files, since):
    symbols = set()
    for rel_path in changed_files:
        path = Path(target) / rel_path
        defs = _extract_defs(path)
        file_syms: set = set()  # 必须 per-file:整文件兜底要看「本文件」是否提到符号,不是全局累加
        for line in _git_lines(target, ["diff", "--unified=0", since, "--", rel_path]):
            if line.startswith("@@"):
                match = re.search(r"\+(\d+)", line)
                if not match:
                    continue
                lineno = int(match.group(1))
                owner = None
                for item in defs:
                    if item["start"] <= lineno <= item["end"]:
                        owner = item["name"]
                        break
                if owner:
                    file_syms.add(owner)
            elif line.startswith("+") and not line.startswith("+++"):
                name = _symbol_from_line(line[1:])
                if name:
                    file_syms.add(name)
        if not file_syms:
            file_syms.update(item["name"] for item in defs)
        symbols |= file_syms
    return symbols


def _all_source_files(target):
    root = Path(target)
    files = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in CODE_EXTS:
            continue
        rel = path.relative_to(root)
        if _is_generated_or_vendor(rel) or _looks_like_test(str(rel)):
            continue
        files.append(path)
    return files


def _static_detect_changes(target, since="HEAD", depth=2, reason="fallback"):
    target = Path(target).resolve()
    changed = _changed_files(target, since)
    changed_symbols = _changed_symbols(target, changed, since)
    if not changed_symbols:
        return {
            "status": "fallback",
            "fallback_reason": reason,
            "changed_files": changed,
            "impacted_count": 0,
            "impacted_symbols": [],
            "changed_symbols": [],
            "edges": [],
        }

    defs = []
    for path in _all_source_files(target):
        defs.extend(_extract_defs(path))

    callers_by_callee = {name: set() for name in changed_symbols}
    symbol_files = {}
    for item in defs:
        symbol_files.setdefault(item["name"], item["file"])
    all_names = {item["name"] for item in defs}
    for item in defs:
        body = item["body"]
        caller = item["name"]
        for callee in all_names:
            if caller == callee:
                continue
            if re.search(rf"\b{re.escape(callee)}\s*\(", body):
                callers_by_callee.setdefault(callee, set()).add(caller)

    impacted = set(changed_symbols)
    frontier = set(changed_symbols)
    for _ in range(max(0, int(depth))):
        next_frontier = set()
        for name in frontier:
            next_frontier.update(callers_by_callee.get(name, set()))
        next_frontier -= impacted
        impacted.update(next_frontier)
        frontier = next_frontier
        if not frontier:
            break

    symbols = [
        {"name": name, "label": "Function", "file": symbol_files.get(name, "")}
        for name in sorted(impacted)
    ]
    # 导出受影响子图内的调用边(caller → callee),供自动生成 Mermaid 依赖图;
    # MCP 路径没有等价边数据,只有静态回退能画出真边。
    edges = sorted(
        (
            {"caller": caller, "callee": callee}
            for callee in impacted
            for caller in callers_by_callee.get(callee, set())
            if caller in impacted
        ),
        key=lambda e: (e["caller"], e["callee"]),
    )
    return {
        "status": "fallback",
        "fallback_reason": reason,
        "changed_files": changed,
        "impacted_count": len(symbols),
        "impacted_symbols": symbols,
        "changed_symbols": sorted(changed_symbols),
        "edges": edges,
    }


def _looks_like_test(path):
    p = str(path or "").lower()
    return any(t in p for t in ("test_", "_test", ".test.", ".spec.", "tests/", "/test/", "spec/"))


def impacted_symbol_names(detect_result):
    """从 detect_changes 结果提取受影响的函数/类/接口名。过滤口径(测试文件、框架产物、
    label 白名单)只在 impact_graph_data 实现一份,这里取其节点名,保证名单与图节点不漂移。"""
    return [node["name"] for node in impact_graph_data(detect_result)["nodes"]]


def impact_graph_data(detect_result):
    """从 detect_changes 结果提取受影响接口的节点/边/改动符号——"哪些符号算受影响接口"的
    过滤口径(测试路径、框架产物、label 白名单)的唯一实现,impacted_symbol_names 也取此结果。
    节点按 (name, file) 去重:同名符号分属不同文件时都保留,不静默合并。
    MCP 路径没有边数据时 edges 为空数组,不造假。"""
    if not detect_result:
        return {"nodes": [], "edges": [], "changed": []}
    nodes = []
    seen = set()
    for sym in detect_result.get("impacted_symbols") or []:
        if _looks_like_test(sym.get("file")) or _is_framework_artifact_path(sym.get("file")):
            continue
        label = str(sym.get("label", ""))
        if label not in {"Function", "Method", "Class", "Interface", "Struct", "Type", "Enum"}:
            continue
        name = sym.get("name")
        file = str(sym.get("file") or "")
        if not name or (name, file) in seen:
            continue
        seen.add((name, file))
        nodes.append({"name": name, "file": file, "label": label})
    names = {node["name"] for node in nodes}
    edges = [
        edge for edge in (detect_result.get("edges") or [])
        if edge.get("caller") in names and edge.get("callee") in names
    ]
    changed = [n for n in (detect_result.get("changed_symbols") or []) if n in names]
    return {"nodes": nodes, "edges": edges, "changed": changed}


def _mermaid_node_id(name, index):
    # Mermaid 节点 ID 对 . / $ 等字符敏感;消毒后加序号保证唯一,显示名保留原符号名
    clean = re.sub(r"[^0-9A-Za-z_]", "_", str(name))
    return f"n{index}_{clean}"


def _mermaid_label(name):
    """引号 label 内仍有害的字符转成 Mermaid 实体(泛型 <>、引号、# 等);
    先转 # 防止把转出的实体二次转义。"""
    return (
        str(name)
        .replace("#", "#35;")
        .replace('"', "#quot;")
        .replace("<", "#lt;")
        .replace(">", "#gt;")
    )


def render_impact_mermaid(nodes, edges, changed, untested):
    """节点+边 → Mermaid flowchart 文本。有边画调用关系(caller --> callee);
    无边(MCP 路径)按文件分组只呈现节点。改动符号与无测试守护符号用样式区分。"""
    node_ids = [(node, _mermaid_node_id(node["name"], i)) for i, node in enumerate(nodes)]
    ids = {}
    for node, node_id in node_ids:
        ids.setdefault(node["name"], node_id)  # 同名节点都画;名字挂的边/样式落到首个

    def node_line(node, node_id, indent="    "):
        return f'{indent}{node_id}["{_mermaid_label(node["name"])}"]'

    lines = ["flowchart LR"]
    if edges:
        lines += [node_line(node, node_id) for node, node_id in node_ids]
        lines += [f'    {ids[edge["caller"]]} --> {ids[edge["callee"]]}' for edge in edges]
    else:
        by_file = {}
        for node, node_id in node_ids:
            by_file.setdefault(node.get("file") or "(unknown file)", []).append((node, node_id))
        for gi, (file, group) in enumerate(sorted(by_file.items())):
            lines.append(f'    subgraph g{gi}["{_mermaid_label(file)}"]')
            lines += [node_line(node, node_id, indent="        ") for node, node_id in group]
            lines.append("    end")
    lines.append("    classDef changed fill:#ffe0b2,stroke:#e65100,stroke-width:2px;")
    lines.append("    classDef untested fill:#ffcdd2,stroke:#b71c1c,stroke-width:2px;")
    changed_ids = [ids[n] for n in changed if n in ids]
    untested_ids = [ids[n] for n in untested if n in ids]
    if changed_ids:
        lines.append(f"    class {','.join(changed_ids)} changed;")
    if untested_ids:
        lines.append(f"    class {','.join(untested_ids)} untested;")
    return "\n".join(lines)


def write_impact_diagram(target, impact):
    """自动生成的 Mermaid 依赖图 → docs/diagrams/<slug>-impact.md(统一图目录,每次刷新)。"""
    slug = impact.get("slug") or "current-request"
    out = Path(target) / "docs" / "diagrams"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{slug}-impact.md"
    nodes = impact.get("nodes") or []
    lines = [
        GENERATED,
        f"# Impact Diagram: {slug}",
        "",
        "自动生成:本次改动的 blast radius 依赖图(每次 execute 刷新,勿手改;"
        "设计图请画在同目录的 `-design.md`)。",
        "橙色 = 本次改动的符号;红色 = 受影响但没有测试守护。",
        "",
    ]
    if nodes:
        lines += [
            "```mermaid",
            render_impact_mermaid(
                nodes,
                impact.get("edges") or [],
                impact.get("changed") or [],
                impact.get("untested") or [],
            ),
            "```",
        ]
    else:
        lines.append(
            "(no affected interfaces detected — nothing to draw;"
            "尚无代码改动时本图为空属正常,实现后重跑 verify 会自动刷新)"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def impacted_untested(target, impacted_names):
    """受影响接口 ∩ test-index 盲区(没测试守护的)= 受影响但没测的接口。
    没有 test-index(还没建)时返回空,不误判。"""
    blind = _impacted_blind_rows(target, impacted_names)
    return sorted(row["symbol"] for row in blind if not _ignored_impact_reason(target, row))


def ignored_impact_symbols(target, impacted_names):
    """返回已降噪的受影响盲区符号,用于报告透明呈现(不参与阻断)。"""
    ignored = []
    for row in _impacted_blind_rows(target, impacted_names):
        reason = _ignored_impact_reason(target, row)
        if reason:
            ignored.append({"symbol": row["symbol"], "reason": reason})
    return sorted(ignored, key=lambda row: row["symbol"])


def _impacted_blind_rows(target, impacted_names):
    if not impacted_names:
        return []
    ti = Path(target) / "docs" / "verify" / "test-index.json"
    try:
        data = json.loads(ti.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    impacted = set(impacted_names)
    rows = []
    seen = set()
    for row in data.get("blind_spots") or []:
        symbol = row.get("symbol")
        if not symbol or symbol not in impacted or symbol in seen:
            continue
        rows.append(row)
        seen.add(symbol)
    return rows


def _ignored_impact_reason(target, row):
    name = str(row.get("symbol") or "")
    if not name:
        return "empty symbol"
    if name.startswith("_"):
        return "private implementation detail"
    if row.get("kind") == "class" and _is_python_dataclass(target, row):
        return "dataclass DTO"
    return ""


def _is_python_dataclass(target, row):
    rel = row.get("defined_in")
    name = row.get("symbol")
    if not rel or not name or not str(rel).endswith(".py"):
        return False
    path = Path(target) / str(rel)
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return False
    class_re = re.compile(rf"^\s*class\s+{re.escape(str(name))}\b")
    for idx, line in enumerate(lines):
        if not class_re.match(line):
            continue
        for prev in range(idx - 1, max(-1, idx - 8), -1):
            stripped = lines[prev].strip()
            if not stripped:
                continue
            if stripped.startswith("@"):
                if stripped.startswith("@dataclass") or stripped.endswith(".dataclass"):
                    return True
                continue
            break
    return False


def write_impact_report(target, impact):
    """把图谱影响分析写成 docs/verify/impact-graph.{md,json}(给 agent 看,据此先补测试),
    并在 docs/diagrams/<slug>-impact.md 生成自动 Mermaid 依赖图。"""
    out = Path(target) / "docs" / "verify"
    out.mkdir(parents=True, exist_ok=True)
    impacted = impact.get("impacted") or []
    untested = impact.get("untested") or []
    ignored = impact.get("ignored_untested") or []
    diagram = write_impact_diagram(target, impact)
    lines = [
        GENERATED,
        "# Impact Analysis (knowledge-graph blast radius)",
        "",
        "由 codebase-memory 的 detect_changes 算出:本次改动传递性影响到的接口/函数。",
        "**受影响但没有测试守护的接口,应在开发前先补测试**(交叉 test-index 盲区)。",
        "",
        f"- Affected interfaces: {len(impacted)}",
        f"- Affected **without** a guarding test: {len(untested)}",
        f"- Noise-filtered affected symbols: {len(ignored)}",
        f"- Diagram: `docs/diagrams/{diagram.name}`(自动生成的 Mermaid 依赖图)",
        # 分析来源必须透出:静态回退是正则近似,不能让用户误以为拿到的是真图谱结果
        f"- Source: {impact.get('graph_source') or 'knowledge-graph'}"
        + (f" — {impact['fallback_reason']}" if impact.get("fallback_reason") else ""),
        "",
        "## Affected but untested (add tests first)",
    ]
    lines += ([f"- `{n}`" for n in untested]
              or ["- (none — all affected interfaces have tests, or no test-index yet)"])
    lines += ["", "## Noise-filtered affected symbols", ""]
    lines += ([f"- `{row.get('symbol')}` — {row.get('reason')}" for row in ignored]
              or ["- (none)"])
    lines += ["", "## All affected interfaces", ""]
    lines += [f"- `{n}`" for n in impacted] or ["- (none)"]
    (out / "impact-graph.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "impact-graph.json").write_text(
        json.dumps(impact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    import sys
    args = sys.argv[1:]
    if not args:
        print("usage: code_graph.py <target> [since]   |   code_graph.py index <target>")
        return 2
    # index 模式:建/刷新知识图谱(新项目从头建图也走这里)
    if args[0] == "index":
        if len(args) < 2:
            print("usage: code_graph.py index <target>")
            return 2
        if not graph_available():
            print(INSTALL_HINT)
            return 1
        idx = index_repository(Path(args[1]).expanduser().resolve())
        print(json.dumps(idx, ensure_ascii=False) if idx else "index failed")
        return 0 if idx else 1
    # 默认:影响分析(detect_changes blast radius)
    target = Path(args[0]).expanduser().resolve()
    since = args[1] if len(args) > 1 else "HEAD"
    if not graph_available():
        print(INSTALL_HINT)
        return 1
    result = detect_changes(target, since=since)
    print(json.dumps({"available": True, "detect": result,
                      "impacted": impacted_symbol_names(result)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
