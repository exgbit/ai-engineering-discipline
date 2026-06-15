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
claude-code-skills/
  ai-engineering-discipline/ # Claude Code orchestrator skill
  ai-spec/                   # Spec step skill, default: GitHub Spec Kit
  ai-loop/                   # Loop step skill, default: LangGraph
  ai-verify/                 # Verify step skill, default: Semgrep
  ai-memory/                 # Memory step skill, default: Mem0
adapters/
  default-stack.json        # Default open-source framework choices
framework/
  spec-verify-memory.md     # 核心框架
  integrated-workflow.md    # One-entry integrated workflow
  loop-engineering.md       # Loop Engineering 执行模型
  adoption-roadmap.md       # 公司落地路线
  operating-model.md        # 团队协作模型
  company-pilot-playbook.md # 公司试点操作手册
templates/
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
examples/
  project-memory.example.md # 项目记忆示例
  test-matrix.example.md    # 需求到测试映射示例
  loop-runbook.example.md   # Loop runbook 示例
scripts/
  bootstrap.sh              # macOS / Linux 项目安装脚本
  bootstrap.bat             # Windows 项目安装脚本
  install_default_adapters.py # Plan/install Spec Kit, LangGraph, Semgrep, Mem0
  summarize_metrics.py      # 指标摘要脚本
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

By default, existing files are not overwritten. To reinstall framework files, add `--force`:

```bash
./scripts/bootstrap.sh /path/to/target-project --force
```

```bat
scripts\bootstrap.bat C:\path\to\target-project --force
```

To also install the default open-source adapter stack automatically:

```bash
./scripts/bootstrap.sh /path/to/target-project --install-adapters
```

```bat
scripts\bootstrap.bat C:\path\to\target-project --install-adapters
```

This installs:

- Spec: GitHub Spec Kit
- Loop: LangGraph
- Verify: Semgrep
- Memory: Mem0

The installer creates:

```text
CLAUDE.md
.claude/skills/ai-engineering-discipline/
.claude/skills/ai-spec/
.claude/skills/ai-loop/
.claude/skills/ai-verify/
.claude/skills/ai-memory/
.codex/skills/ai-engineering-discipline/
.codex/skills/ai-spec/
.codex/skills/ai-loop/
.codex/skills/ai-verify/
.codex/skills/ai-memory/
docs/specs/spec-template.md
docs/verify/verify-checklist.md
docs/verify/test-matrix.md
docs/memory/memory-entry.md
docs/memory/project-rules.md
docs/memory/module-map.md
docs/memory/pitfalls.md
docs/loops/loop-template.md
docs/loops/bugfix-loop.md
.github/pull_request_template.md
```

After install, open the target project in Claude Code and say:

```text
Use ai-engineering-discipline to inspect this project and enter development.
```

The Claude Code skill will:

1. ensure framework files exist;
2. scan stack signals and candidate commands into `docs/memory/project-scan.md`;
3. guide Claude through `Spec -> Loop -> Verify -> Memory`;
4. stop before unsafe or unverifiable work.

## Integrated Workflow

Users should normally use one skill only:

```text
Use ai-engineering-discipline to inspect this project and enter development.
```

The orchestrator skill calls the step skills internally:

```text
ai-spec   -> GitHub Spec Kit
ai-loop   -> LangGraph
ai-verify -> Semgrep + native tests
ai-memory -> Mem0 + docs/memory
```

This is the difference from using the four frameworks directly: the user does not decide when to run each tool or how to pass artifacts between them. The framework owns the sequence, files, and handoffs. See `framework/integrated-workflow.md`.

## Default Open-Source Adapter Stack

The framework uses one opinionated default GitHub/open-source framework per layer:

| Layer | Default | Purpose |
|---|---|---|
| Spec | GitHub Spec Kit | Spec-driven development and agent-facing spec workflow |
| Loop | LangGraph | Stateful agent loop and graph orchestration |
| Verify | Semgrep | Cross-language static analysis and security verification |
| Memory | Mem0 | Durable agent memory layer |

Plan installation without changing the machine:

```bash
python scripts/install_default_adapters.py /path/to/target-project
```

Install missing adapters:

```bash
python scripts/install_default_adapters.py /path/to/target-project --execute
```

This writes `docs/adapters/default-stack.md` in the target project with detected status and install commands.

## How To Use

1. 在目标项目中创建 `docs/specs/`、`docs/verify/`、`docs/memory/`、`docs/loops/`。
2. 将 `.claude/skills/ai-engineering-discipline/` 安装到目标项目，让 Claude Code 可以直接调用 skill。
3. 将 `CLAUDE.md` 复制到目标项目根目录，让 Claude Code 自动按四层协议执行。
4. 将 `templates/` 中的模板复制到项目中。
5. 每个需求先补 `spec`，每个 PR 必须过 `verify`，每次事故或踩坑必须更新 `memory`。
6. 将重复任务改造成 loop，明确状态机、退出条件、重试策略和预算。
7. 用 `data/metrics-schema.csv` 跟踪 AI 编程的真实收益与风险。

## If Requirements Already Exist

Use the orchestrator:

```text
Use ai-engineering-discipline.
I already have requirement documents.
Import them into specs, create a requirements index, select the first feature loop, and do not code until the spec and loop are ready.
```

Advanced users may call the step skills directly:

```text
Use ai-spec to import existing requirement documents into docs/specs/.
Then use ai-loop to select the first implementation loop.
Do not write code until the spec and loop are ready.
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
