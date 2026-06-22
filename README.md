# Spec / Verify / Memory + Loop Engineering Framework

一套面向公司工程团队的 AI 编程开发框架。核心目标是把 AI 编程从“提示词驱动的即时产出”升级为“规格驱动、验证闭环、记忆沉淀、循环编排”的工程体系。

## Core Thesis

AI 编程必须具备三件套，并通过 loop 跑起来：

- **Spec**: 先定义规格，再生成代码。需求、设计、接口、验收标准必须可版本化、可审查、可追溯。
- **Verify**: 代码必须通过验证门。AI 生成内容不能靠“看起来合理”进入主干。
- **Memory**: 项目知识必须沉淀。模块边界、历史决策、踩坑记录和团队规则要成为 AI 与工程师共同使用的上下文。
- **Loop**: 把 agent 视为 stateless function，把状态机、策略、重试、退出条件、预算和 memory 组成可度量的 orchestration layer。

## Repository Layout

```text
CLAUDE.md                    # Agent operating protocol
AGENTS.md                    # Repository contributor guide for agents
claude-code-skills/
  ai-engineering-discipline/ # Claude Code orchestrator skill
  ai-spec/                   # Spec step skill (framework's own spec template)
  ai-loop/                   # Loop step skill (framework's own loop runbook)
  ai-verify/                 # Verify step skill (native tests + optional Semgrep)
  ai-memory/                 # Memory step skill (local docs/memory)
claude-code-commands/
  ai-start.md                # Claude Code slash command: initialize/inspect
  ai-request.md              # Claude Code slash command: create managed request
  ai-execute.md              # Claude Code slash command: execute safe setup
  ai-verify.md               # Claude Code slash command: run explicit verification
  ai-doctor.md               # Claude Code slash command: diagnose installation
adapters/
  default-stack.json        # Default open-source framework choices
presets/
  *.json                    # Task/risk presets that hide framework parameters
framework/
  spec-verify-memory.md     # 核心框架
  integrated-workflow.md    # One-entry integrated workflow
  loop-engineering.md       # Loop Engineering 执行模型
  adoption-roadmap.md       # 公司落地路线
  operating-model.md        # 团队协作模型
  company-pilot-playbook.md # 公司试点操作手册
templates/
  ai-discipline-config.json # Target-project defaults for CLI behavior
  github-ai-discipline.yml  # GitHub Actions verify/report workflow
  agents-template.md        # Target-project AGENTS.md operating protocol
  start-here.md             # Installed as docs/AI_ENGINEERING_START_HERE.md
  spec-template.md          # 需求 / 设计规格模板
  adr-template.md           # 架构决策记录模板
  pr-template.md            # AI 编程 PR 模板
  verify-checklist.md       # 验证门清单
  memory-entry.md           # 项目记忆记录模板
  loop-template.md          # Agent loop 设计模板
data/
  methodology-signals.csv   # 方法论信号样本
  metrics-schema.csv        # 推广效果指标
  sample-adoption-metrics.csv # synthetic 示例指标
  scorecard.md              # 采用度评分卡
examples/
  project-memory.example.md # 项目记忆示例
  test-matrix.example.md    # 需求到测试映射示例
  loop-runbook.example.md   # Loop runbook 示例
scripts/
  ai_discipline.py          # Unified CLI: start/request/run/execute/verify/report/config/metrics/doctor
  ai-discipline.sh          # macOS / Linux unified CLI wrapper
  ai-discipline.bat         # Windows unified CLI wrapper
  bootstrap.sh              # macOS / Linux 项目安装脚本
  bootstrap.bat             # Windows 项目安装脚本
  install_default_adapters.py # Plan/install the optional Semgrep gate (other layers are style-reference only)
  run_request.py            # Create managed request from task/risk/requirements
  execute_request.py        # Execute safe setup steps from current-request.md
  init_project.py           # Create framework files in a target project
  inspect_project.py        # Scan target stack/commands into docs/memory
  doctor.py                 # Diagnose installation (used by /ai-doctor and CLI start)
  summarize_metrics.py      # 指标摘要脚本
  sync_skills.py            # Sync top-level source into the two skill copies (CI-checked)
  # 每个 run_request / execute_request / install_default_adapters 均有 .sh / .bat 包装
  # scripts/ 是 skill 副本的唯一权威源,改动后须跑 sync_skills.py(见 CONTRIBUTING.md)
skills/
  ai-engineering-discipline/ # Codex orchestrator skill
  ai-spec/
  ai-loop/
  ai-verify/
  ai-memory/
writing/
  source-notes.md           # 发布前来源核验
  article-brief.md          # 文章策划
  article-draft.md          # 中文文章草案
```

## Quick Install

After cloning this repository, point the bootstrap script at the project you want to develop.

macOS / Linux:

```bash
cd /path/to/ai-engineering-discipline
./scripts/bootstrap.sh /path/to/target-project
```

Windows:

```bat
cd C:\path\to\ai-engineering-discipline
scripts\bootstrap.bat C:\path\to\target-project
```

The shell wrappers prefer `python3` and fall back to `python`. Windows wrappers prefer `py -3` and fall back to `python`. Bootstrap excludes `__pycache__`, `.pyc`, and `.DS_Store` files when installing skills.

By default, existing files are not overwritten. To reinstall framework files, add `--force`:

```bash
./scripts/bootstrap.sh /path/to/target-project --force
```

```bat
scripts\bootstrap.bat C:\path\to\target-project --force
```

The framework needs no external tools to run. The only optional one is **Semgrep** (the security-scan gate). Install it with:

```bash
./scripts/bootstrap.sh /path/to/target-project --install-adapters
```

```bat
scripts\bootstrap.bat C:\path\to\target-project --install-adapters
```

`--install-adapters` installs **only Semgrep** (the one tool the framework actually calls). If Semgrep is absent the scan is reported as skipped, not failed — everything else still works.

Spec Kit, LangGraph, and Mem0 are **not installed and not needed**: the framework does not call them; they are only the style references that the Spec / Loop / Memory Markdown templates follow.

The installer creates:

```text
.ai-discipline.json
CLAUDE.md
AGENTS.md
.claude/skills/ai-engineering-discipline/
.claude/skills/ai-spec/
.claude/skills/ai-loop/
.claude/skills/ai-verify/
.claude/skills/ai-memory/
.claude/commands/ai-start.md
.claude/commands/ai-build.md
.claude/commands/ai-request.md
.claude/commands/ai-execute.md
.claude/commands/ai-verify.md
.claude/commands/ai-doctor.md
.codex/skills/ai-engineering-discipline/
.codex/skills/ai-spec/
.codex/skills/ai-loop/
.codex/skills/ai-verify/
.codex/skills/ai-memory/
docs/specs/spec-template.md
docs/AI_ENGINEERING_START_HERE.md
docs/verify/verify-checklist.md
docs/verify/test-matrix.md
docs/memory/memory-entry.md
docs/memory/project-rules.md
docs/memory/module-map.md
docs/memory/pitfalls.md
docs/loops/loop-template.md
docs/loops/bugfix-loop.md
.github/pull_request_template.md
.github/workflows/ai-discipline.yml
```

After install, open the target project in Claude Code. The simplest way to use the framework is one plain sentence — you do not need to learn task types, risk, presets, or the Spec/Loop/Verify/Memory workflow:

```text
/ai-build add a refund approval flow
```

`/ai-build` infers the task, writes and fills the spec, implements the change in small steps, and verifies it — talking to you in plain language the whole time. You can also just describe what you want in chat; the `ai-engineering-discipline` skill picks it up automatically.

The remaining commands are the explicit/advanced entry points, installed under `.claude/commands/`:

```text
/ai-start                                  # initialize / inspect the repo
/ai-build <plain-language request>         # plain-sentence entry (recommended)
/ai-request --task feature --name "..." --requirements docs/requirements/...  # explicit managed request
/ai-execute
/ai-verify
/ai-doctor
```

The Claude Code workflow will:

1. ensure framework files exist;
2. scan stack signals and candidate commands into `docs/memory/project-scan.md`;
3. guide Claude through `Spec -> Loop -> Verify -> Memory`;
4. stop before unsafe or unverifiable work.

## Integrated Workflow

Users should normally use the unified CLI instead of calling the step scripts directly:

```bash
./scripts/ai-discipline.sh start --project /path/to/target-project
./scripts/ai-discipline.sh run --project /path/to/target-project --task feature --name "refund approval" --requirements docs/requirements/refund.md --risk medium --verify
```

The `run` command creates the managed request, generates Spec / Loop / Verify / Memory artifacts, optionally runs verification with `--verify`, and writes the pilot report.

For debugging or CI, use the same workflow as separate steps:

```bash
./scripts/ai-discipline.sh request --project /path/to/target-project --task feature --name "refund approval" --requirements docs/requirements/refund.md --risk medium
./scripts/ai-discipline.sh execute --project /path/to/target-project
./scripts/ai-discipline.sh verify --project /path/to/target-project --fail-on-verify-failure
./scripts/ai-discipline.sh report --project /path/to/target-project
```

Windows:

```bat
scripts\ai-discipline.bat start --project C:\path\to\target-project
scripts\ai-discipline.bat run --project C:\path\to\target-project --task feature --name "refund approval" --requirements docs\requirements\refund.md --risk medium --verify
```

Separate-step Windows usage:

```bat
scripts\ai-discipline.bat request --project C:\path\to\target-project --task feature --name "refund approval" --requirements docs\requirements\refund.md --risk medium
scripts\ai-discipline.bat execute --project C:\path\to\target-project
scripts\ai-discipline.bat verify --project C:\path\to\target-project --fail-on-verify-failure
scripts\ai-discipline.bat report --project C:\path\to\target-project
```

`report` writes `docs/reports/pilot-report.md` and `docs/reports/pilot-report.json` with artifact coverage, required/executed/skipped checks, merge readiness, memory-candidate count, loop-state coverage, and changed-file count when Git is available. By default, every run is also archived under `docs/reports/runs/` so one project can accumulate trend data over time.

Aggregate multiple pilot reports for team review or external writeups:

```bash
./scripts/ai-discipline.sh metrics --project /path/to/target-project
./scripts/ai-discipline.sh metrics --project /path/to/summary-repo --input /path/to/project-a --input /path/to/project-b
```

This writes:

```text
docs/reports/pilot-summary.md
docs/reports/pilot-summary.json
docs/reports/pilot-summary.csv
```

When a project contains `docs/reports/runs/`, `metrics` uses archived run reports first and avoids double-counting the latest `pilot-report.json`.

Project defaults live in `.ai-discipline.json`. Initialize or inspect them with:

```bash
./scripts/ai-discipline.sh config --project /path/to/target-project --init
./scripts/ai-discipline.sh config --project /path/to/target-project
```

For mature teams, set these defaults in the target project:

```json
{
  "defaults": {
    "verify": true,
    "run_semgrep": true,
    "run_native_checks": true,
    "fail_on_verify_failure": true
  },
  "reports": {
    "archive_runs": true
  }
}
```

The installed `.github/workflows/ai-discipline.yml` runs the same verify/report gate in CI.

The lower-level request script remains available for installed Claude/Codex skills:

```bash
python .claude/skills/ai-engineering-discipline/scripts/run_request.py . \
  --task feature \
  --name "refund approval" \
  --requirements docs/requirements/refund.md \
  --risk medium
```

The orchestrator runs the four steps internally:

```text
ai-spec   -> framework's own spec template, filled by the agent
ai-loop   -> framework's own loop runbook
ai-verify -> native tests + optional Semgrep security scan
ai-memory -> local docs/memory
```

The value is that the user does not decide when to run each step or how to pass artifacts between them — the framework owns the sequence, files, and handoffs. Only the Verify step calls an external tool (Semgrep), and only if it is installed. See `framework/integrated-workflow.md`.

The managed request resolves low-level parameters from presets:

```text
task=feature risk=medium requirements=refund.md
  -> spec:   mode and required spec sections
  -> loop:   runbook/retry/human-gate settings
  -> verify: Semgrep config/severity (if installed) + native checks
  -> memory: local-memory write policy
```

The resolved plan is written to `docs/ai-engineering/current-request.md`.

For the simplest entry, omit `--preset` or pass `--preset standard`, `--preset default`, or `--preset auto`; all select the task+risk default preset.

Requirement paths may be absolute, relative to your current shell directory, or relative to the target project.
`run_request.py` imports external requirement files into the target project; `execute_request.py` only reads requirement sources that are already inside the target project.

For existing projects, every managed request is treated as a controlled change against the current codebase. The generated spec includes existing-project baseline artifacts, impact analysis, coupling constraints, and a regression plan. The verify matrix includes a regression matrix so new work is checked against behavior that must not break.

Then execute the safe setup steps:

```bash
python .claude/skills/ai-engineering-discipline/scripts/execute_request.py .
```

This creates or updates generated spec, loop, verify, memory-plan, loop-run, memory-candidate, and execution-report artifacts. It does not edit business code, install packages, run destructive commands, or claim implementation success.

To run explicit verification and write structured results:

```bash
python .claude/skills/ai-engineering-discipline/scripts/execute_request.py . --run-semgrep
python .claude/skills/ai-engineering-discipline/scripts/execute_request.py . --run-native-checks
```

Results are written to `docs/verify/verification-results.json` and `docs/verify/verification-results.md`. Semgrep raw JSON is saved as `docs/verify/semgrep-results.json` when Semgrep runs successfully. Native checks are limited to detected local test, lint, typecheck, and required build commands. The structured JSON includes `can_merge`, `required_checks`, `skipped_required_checks`, and `blocking_reasons`.

Note: `execute_request.py` itself does not edit business code or install packages. But `--run-native-checks` (and the `verify`/`run --verify` paths) execute the target project's own `test` / `lint` / `typecheck` / `build` scripts, which may have side effects (e.g. `npm run build` can write files or hit the network). Only enable native checks for projects whose scripts you trust.

For CI-style usage, add `--fail-on-verify-failure`; the command exits non-zero after results are written when the overall verification status is `blocked`.

For a deeper assessment of the current architecture, limitations, and data needed to prove value, see `framework/framework-assessment.md`. For public wording, integration depth, and compatibility policy, see `framework/integration-levels.md`.

## Tools Per Layer (only one is actually used)

Each layer names an open-source tool, but **only Verify (Semgrep) is invoked by the framework at runtime, and even that is optional.** The other three names are only *style references* for the Markdown templates — the framework does not call them and you do not need to install them.

| Layer | Tool | Called by the framework? | Need to install? |
|---|---|---|---|
| Spec | GitHub Spec Kit | No — style reference only | No |
| Loop | LangGraph | No — style reference only | No |
| Verify | Semgrep | Yes — runs it as the security-scan gate | Optional (skipped if absent) |
| Memory | Mem0 | No — style reference only | No |

Plan installation without changing the machine:

```bash
python scripts/install_default_adapters.py /path/to/target-project
```

Install missing adapters:

```bash
python scripts/install_default_adapters.py /path/to/target-project --execute
```

With `--execute` this installs **only Semgrep** (the one tool the framework calls); Spec Kit / LangGraph / Mem0 are listed as `reference-only` and are not installed. It writes `docs/adapters/default-stack.md` in the target project with the detected status.

This project is independent. The Spec / Loop / Memory templates take stylistic inspiration from GitHub Spec Kit, LangGraph, and Mem0, and the Verify gate runs Semgrep; it is not affiliated with or endorsed by those projects, and it does not call Spec Kit, LangGraph, or Mem0.

## How To Use

Use scripts first; manual setup is only a fallback.

1. Run `scripts/bootstrap.sh <target>` or `scripts/bootstrap.bat <target>`.
2. Create a managed request with `run_request.py`.
3. Run `execute_request.py` to generate the safe working artifacts.
4. Open Claude Code or Codex in the target project and use the generated spec, loop, verify plan, and memory plan.
5. Track adoption with `data/metrics-schema.csv`.

Claude Code users can use slash commands instead of remembering script paths:

```text
/ai-request --task feature --name "refund approval" --requirements docs/requirements/refund.md
/ai-execute --run-native-checks
/ai-doctor
```

Minimum example:

```bash
./scripts/bootstrap.sh /path/to/project
python scripts/run_request.py /path/to/project --task feature --name "refund approval" --requirements /path/to/refund.md
python scripts/execute_request.py /path/to/project
python scripts/execute_request.py /path/to/project --run-native-checks --run-semgrep
```

## If Requirements Already Exist

Use the Claude Code command:

```text
/ai-request --task feature --name "first feature" --requirements docs/requirements --risk medium
/ai-execute
```

Equivalent script command:

```bash
python .claude/skills/ai-engineering-discipline/scripts/run_request.py . \
  --task feature \
  --name "first feature" \
  --requirements docs/requirements \
  --risk medium
python .claude/skills/ai-engineering-discipline/scripts/execute_request.py .
```

This creates a `docs/specs/requirements-index.md` and converts existing requirement docs into feature specs. See `framework/existing-requirements-workflow.md`.

Manual bootstrap example:

```bash
mkdir -p docs/specs docs/verify docs/memory docs/loops .github
cp /path/to/ai-engineering-discipline/CLAUDE.md .
cp /path/to/ai-engineering-discipline/templates/spec-template.md docs/specs/
cp /path/to/ai-engineering-discipline/templates/verify-checklist.md docs/verify/
cp /path/to/ai-engineering-discipline/templates/memory-entry.md docs/memory/
cp /path/to/ai-engineering-discipline/templates/loop-template.md docs/loops/
cp /path/to/ai-engineering-discipline/templates/pr-template.md .github/pull_request_template.md
```

## Minimum Viable Adoption

如果只能先做三件事：

1. 所有 AI 代码任务必须先有验收标准。
2. 所有 AI 生成 PR 必须附验证证据。
3. 每周更新一次项目记忆，包括反模式、模块边界和高频问题。
4. 选择一个重复任务，改造成可复用 loop。

## Positioning

这个框架不是某个 AI IDE、Agent 或模型的替代品，而是它们之上的工程纪律层。工具可以替换，纪律必须保留。

## Metrics Summary

Run the sample report:

```bash
python scripts/summarize_metrics.py data/sample-adoption-metrics.csv
```

The bundled sample data is synthetic. Replace it with your team's pilot metrics before using the results in internal reports or public writing.
