# AI Engineering Discipline

> 给"用 AI agent 写代码"的人的一层**工程纪律**——把 AI 编程从"提示词驱动、看起来对就算完成",变成"先有规格、改完必须有真测试、完成信号由机制生成而不是 AI 自己说了算"。

一条命令装进任意项目,之后用**一句大白话**就能跑完"规格 → 实现 → 验证 → 记忆"的完整闭环。**运行框架不需要任何外部工具**——唯一可选的是 Semgrep 安全扫描,没装就跳过,其余照常工作。

---

## 它解决什么

AI 写代码最大的信任缺口是:**agent 说"做好了",但没有可信证据**。它容易不写规格直接生成、拿"看起来合理"当验证、改完不写测试、知识不沉淀。

这个框架用**机制**(而不是更用力地提示 agent)堵住这些:

- **改了业务代码,就必须有配套的、真覆盖改动的测试**——否则门禁不放行。支持 Python / Go / Java / JS / TS,空测试、测错函数都拦得住。
- **完成信号由框架脚本生成,不靠 agent 自律**——即使 agent 嘴上说"完成了",`SUMMARY.md` 也会如实写"哪些过了、哪些没过、哪些没跑",而且是大白话。
- **动手前先有规格**——影响分析、验收标准、回归计划没填完就红灯。
- **踩坑和规则沉淀到 `docs/memory/`**,下次 agent 和人都能用。

---

## 项目起源

这个框架始于一个观察:**AI 写代码最像"一个不写测试的开发者"**——它写得飞快,但"看起来对"和"真的对"之间没有任何关卡。

TDD(测试驱动开发)几十年前就给过答案:**先有可验证的标准,再写代码**。这恰好是治 AI"看起来对就算完成"的解药。但把 TDD 直接套到 AI 上还不够——AI 还有三个 TDD 没覆盖的毛病:

- 它**记不住上下文**:每次从零开始,重复踩同样的坑;
- 它**拿解释当证据**:"我跑过了,应该没问题"不是验证;
- 它**会无边界发散**:一个小需求改出一堆不相关的东西。

所以这个框架从 TDD 的内核出发,把它扩展成**四件必须结合、缺一不可**的事:

- **Spec** — 把 TDD 的"先有标准"扩成完整规格(目标 / 边界 / 验收标准 / 测试计划),实现前先定义清楚;
- **Verify** — 把"测试通过"做成**机制门禁**:改代码必须配套真测试,完成信号由程序生成而不是 AI 自报;
- **Memory** — 把规则、模块边界、踩坑沉淀下来,AI 和人共用,不再每次从零;
- **Loop** — 把 agent 当 stateless function,用受控的状态机管 scope、重试、退出条件。

一句话:**AI 时代的工程纪律,是把"测试驱动"扩展成"规格驱动 + 验证闭环 + 记忆沉淀 + 循环编排"——这四件事必须一起上,单独哪一件都兜不住 AI。**

---

## 快速上手

把框架装进你的目标项目(默认不覆盖已有文件):

```bash
git clone https://github.com/exgbit/ai-engineering-discipline
cd ai-engineering-discipline
./scripts/bootstrap.sh /path/to/your-project      # Windows: scripts\bootstrap.bat
```

然后在目标项目里打开 Claude Code,用**一句大白话**:

```text
/ai-build 加一个退款审批功能
```

`/ai-build` 会自动:推断任务类型 → 读你的代码、写并填规格 → 小步实现(带测试)→ 跑验证 → 全程用大白话跟你汇报。你**不需要懂下面的 Spec/Loop/Verify/Memory,也不需要填任何参数**。

> 用 Codex 也一样:框架同时装了 `.codex/skills/`。需要 Semgrep 安全扫描的话,`bootstrap.sh <target> --install-adapters` 只会装 Semgrep 这一个工具。

---

## 工作原理

每个任务走四个相连的层,**全部由框架自带的 Markdown 模板 + AI agent 实现**:

```text
Spec   → 把需求变成规格(目标 / 边界 / 验收标准 / 测试计划)
Loop   → 用受控的循环跑(scope / 重试 / 退出条件)
Verify → 用测试 + 可选 Semgrep 扫描证明结果,生成诚实的完成信号
Memory → 把规则 / 边界 / 踩坑写回 docs/memory/
```

**只有 Verify 这一步会调用一个外部工具(Semgrep),而且可选**——没装就记为"跳过",不算失败。Spec / Loop / Memory 三层零外部依赖,纯模板 + agent。用户面对的是"一句话 + 大白话回复",框架在背后接管步骤顺序、文件和交接,**你不用自己决定何时跑哪个工具、怎么在工具间传产物**。

完成信号分两档,都如实给:

- `can_merge`:有没有阻断项(红灯)。
- `coverage_complete`:所有该跑的检查是否都跑了;没跑的可选项(如未安装 Semgrep)会列出来,但不阻断。

### 测试门禁怎么工作

框架用 `git diff` 找出你改动的代码符号(函数 / 类名,含 JS/TS 的 `const f = () => {}` 箭头函数),再检查"改动的测试是否真的引用了这些符号":

- 改了代码、没动测试 → 拦。
- 改了测试、但测试跟改动的代码毫不相干(空测试 / 测错函数)→ 拦。
- 测试真的引用了改动的函数 / 类 → 放行。

---

## 诚实的能力边界

这个框架刻意只承诺它能兑现的:

- **测试门禁是"测试有没有真覆盖改动符号"的检查,不是真覆盖率。** 它拦得住"完全不写测试""空测试""测错函数";但一个引用了改动符号、断言却没意义的测试,理论上还能过。**它防的是无意的偷懒,不是蓄意的绕过。** 真 diff-coverage 是后续方向(见 `framework/framework-assessment.md`)。
- **智力活(读代码、填规格、判断影响)是 AI agent 做的,框架不读代码语义。** 框架提供的是纪律和门禁,质量上限取决于你用的 agent。脱离 Claude Code / Codex 这类能执行的 agent,它就只是一套模板。
- **指标数据是合成示例。** `data/` 里的采用指标是占位样本,对外引用前请换成你自己的真实 pilot 数据。
- **单租户、纯本地文件 + CLI。** 没有云端、没有多租户 / 权限模型。适合个人和小团队,不是企业级治理平台。

---

## 适合谁

**适合**:用 Claude Code 或 Codex、做**需要长期维护**的项目、且怕 AI 偷懒糊弄的个人或小团队;也适合当团队"AI 协作 SOP"的起点。

**不那么适合**:一次性脚本 / 原型(纪律开销 > 收益);已有成熟 CI(Semgrep diff-aware + SonarQube + 必过测试)的公司质量链路(增量有限)。

---

## 深入阅读

- [`USAGE.md`](USAGE.md) — 完整 CLI 用法(`start` / `run` / `execute` / `verify` / `report` / `metrics` / `doctor`)、单步调试、CI 集成、已有需求文档的接入。
- [`framework/integrated-workflow.md`](framework/integrated-workflow.md) — 一键背后的编排设计。
- [`framework/framework-assessment.md`](framework/framework-assessment.md) — 架构、当前限制、要证明价值还需要的数据(诚实自评)。
- [`framework/integration-levels.md`](framework/integration-levels.md) — 工具名归属与商标声明。
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — 改动须知(`scripts/` 是 skill 副本的唯一权威源,改后跑 `sync_skills.py`)。
- 装进目标项目后,`CLAUDE.md` / `AGENTS.md` 是给 agent 的完整操作协议。

---

## 关于工具名

框架的 Spec / Loop / Memory 模板在风格上参考了 GitHub Spec Kit、LangGraph、Mem0,但**框架不调用它们,也不需要安装**——它们只是模板的风格参照。唯一在运行期真正调用的外部工具是 Semgrep(Verify 步的安全扫描,可选)。本项目独立,与上述项目无隶属或背书关系。

## 作者

果比AI · [guobi.ai](https://guobi.ai)

## License

[MIT](LICENSE) © 2026 果比AI (guobi.ai)
