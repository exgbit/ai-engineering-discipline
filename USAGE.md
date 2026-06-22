# 使用指南 · AI 工程纪律框架

> 一句话:你用**一句话**说需求,AI 在「规格 → 循环 → 验证 → 记忆」(Spec/Loop/Verify/Memory)的纪律下**自动实现 + 自动验证**,全程不用你懂这套术语。

---

## 一、这是什么

它是套在 Claude Code / Codex 之上的**工程纪律层**,不是另一个 AI。你提需求,它保证 AI:

1. 先写清规格(要做什么、影响哪些代码、怎么验收)
2. 按受控步骤实现(小步改、配套写测试)
3. 真的跑测试和门禁验证(不靠"看着对就说完成")
4. 把状态用**大白话**汇报给你

**四层的真实分工**(诚实说明):

| 层 | 做什么 | 谁执行 |
|---|---|---|
| **Spec 规格** | 生成规格文档,填清需求/影响/验收 | 框架给模板 → **AI 读代码填实** |
| **Loop 循环** | 按"读上下文→计划→实现→验证"的步骤走 | 框架给步骤 → **AI 照着走** |
| **Verify 验证** | 真跑测试 + 安全扫描 + 合并门禁 | **框架自己跑程序**(唯一全自动的一层) |
| **Memory 记忆** | 记下模块边界、踩坑 | 框架给模板 → **AI 填** |

> 也就是说:**真正的智力活(读代码、填规格、判断)由 AI 做;框架保证流程规范、门禁可信、状态说人话。** 你需要在 Claude Code 这类能执行的环境里用它。

---

## 二、安装(每个项目一次)

把框架装进你要开发的项目:

```bash
# macOS / Linux
cd /path/to/ai-engineering-discipline
./scripts/bootstrap.sh /path/to/你的项目

# Windows
scripts\bootstrap.bat C:\path\to\你的项目
```

- 默认**不覆盖**你已有的文件;要强制重装加 `--force`(会先把你的 `CLAUDE.md`/`AGENTS.md`/`.ai-discipline.json` 备份成 `.bak`)。
- **唯一可选的外部工具是 Semgrep**(安全扫描)。想要这道扫描就加 `--install-adapters`(它现在**只装 Semgrep**);不装也完全能用,只是少一道可选的安全扫描。
- **Spec Kit / LangGraph / Mem0 不用装** —— 框架不调用它们,它们只是规格/循环/记忆模板的风格参考。装了也不会被用到。

装完后,你的项目里会多出 `.claude/`(技能和命令)、`docs/`(规格/验证/记忆等目录)。

---

## 三、最简用法(推荐)

在你的项目里打开 Claude Code,**一句话**说需求:

```
/ai-build 给待办列表加一个按优先级排序的功能
```

或者干脆在对话里直接说"帮我加个 XX 功能 / 修一下 YY",框架会自动接手。

**它会自动做完整条链路**,你不用管中间步骤:

```
你的一句话
   ↓ 自动推断:这是新功能?修 bug?(你不用选)
   ↓ 把你的需求记成文档
   ↓ 读你的现有代码,填好规格(需求/影响/验收)
   ↓ 小步实现 + 配套写测试
   ↓ 真跑测试 + 验证门禁
   ↓ 用大白话告诉你结果
```

**你只需要看两样东西:**

1. AI 发给你的那条**大白话消息**("做好了,加了 XX,测试都过了,某项可选检查没跑")
2. `docs/ai-engineering/SUMMARY.md` —— 框架**自动生成**的大白话状态(下一节细说)

---

## 四、怎么读"完成信号"

每次验证后,框架自动写 `docs/ai-engineering/SUMMARY.md`,**纯大白话、不带术语**,长这样:

```
# Summary: 按优先级排序
- Tests: 4 passed, 0 failed
- Status: Works — tests pass and nothing is blocking; some optional checks were skipped (listed below).

Not covered (optional or unavailable — these are not failures):
- There's no separate build step for this kind of project, so nothing to build.
- A security scan did not run — the scanner isn't installed on this machine. It's an optional check.
```

**三种状态,看 `Status` 一行就懂:**

| Status | 含义 | 你该做什么 |
|---|---|---|
| `DONE` | 做完了,所有该查的都查了、过了 | 放心用 |
| `Works — ...optional checks were skipped` | 功能好了、测试过了,但有**可选**检查没跑(比如安全扫描没装) | 可以用;括号里列的是可选项,不是错误 |
| `NOT DONE YET — needs fixing` | 还有**必须解决**的问题 | 看它列出的原因(大白话),让 AI 接着改 |

> 这份大白话是**框架机制保证**的——就算 AI 一句翻译都不做,你打开这个文件也能看懂。技术细节(如果你想看)在 `docs/verify/verification-results.json`。

---

## 五、质量门禁:什么情况会被"拦住"

框架的验证门禁是**动真格**的,不是走形式。以下情况会让"完成"亮红灯(`NOT DONE YET`):

- **改了代码但没加/改测试**(新功能、修 bug、重构)→ 拦。这是硬规则,光改实现不写测试过不了。
- **规格里的影响分析 / 回归计划没填完** → 拦。
- **测试失败、或安全扫描发现问题** → 拦。

以下情况**不拦**(只在 SUMMARY 里如实提示"没覆盖"):

- 安全扫描工具(Semgrep)没装 → 跳过,标注为可选未跑。
- 这类项目没有独立构建步骤(如纯 Python 脚本)→ 跳过。
- 项目不在 git 里 → 没法核对是否加了测试,提示但不拦。

> 一个小提示:规格里有些复选框(如影响分析的确认项),AI 要在确认后**勾上**才算填完,否则第一次验证可能先亮红灯——这是正常的,AI 会补勾后重跑。

---

## 六、已经有需求文档怎么办

如果你已经攒了一个需求文件夹(多个 `.md` + 截图 / 设计图 / PDF),直接把整个文件夹给它:

```
/ai-build 按 docs/requirements/ 里的需求做
```

或手动指定:

```bash
python .claude/skills/ai-engineering-discipline/scripts/run_request.py . \
  --task feature --name "批量需求" --requirements docs/requirements/
```

框架会把文件夹里的 **md 文档和图片/PDF 都纳入**;AI 会**读所有文档 + 用视觉看所有图片**,综合提取需求再实现。

> 图片里的需求靠 AI 的视觉能力识别(需要在支持多模态的 Claude Code 里用)。

---

## 七、手动 / 高级用法

平时用 `/ai-build` 就够了。需要细控时,有统一 CLI(分步执行):

```bash
S=.claude/skills/ai-engineering-discipline/scripts/ai_discipline.py

python $S run     .  --task feature --name "退款审批" --requirements docs/req.md   # 一条龙:建请求+生成产物+验证+报告
python $S request .  --task feature --name "退款审批" --requirements docs/req.md   # 只建请求+生成产物
python $S execute .  --run-native-checks                                          # 跑验证
python $S verify  .                                                               # 强制跑全部检查
python $S report  .                                                               # 刷新汇总报告
python $S metrics .                                                               # 聚合多次/多项目的指标
python $S doctor  .                                                               # 自检安装是否正常
```

**任务类型(`--task`,AI 会自动推断,手动时可指定):**
`feature`(新功能) `bugfix`(修 bug) `refactor`(重构) `migration`(迁移) `docs`(文档) `verify`(验证) `memory`(记忆)

**风险等级(`--risk`,可选,不填按任务类型默认):** `low` / `medium` / `high`。不同任务+风险对应不同的检查严格度(预设里定好,你不用关心细节)。

**项目默认配置** `.ai-discipline.json`(可选,控制是否默认开验证、超时等):

```bash
python $S config . --init   # 生成默认配置
python $S config .          # 查看当前配置
```

---

## 八、产物地图(框架在 `docs/` 下生成什么)

| 路径 | 是什么 |
|---|---|
| `docs/ai-engineering/SUMMARY.md` | **给你看的大白话状态**(最重要) |
| `docs/ai-engineering/current-request.md` | 当前这次需求的解析结果 |
| `docs/specs/<名字>.md` | 规格(需求/影响/验收,AI 填) |
| `docs/loops/<名字>.md` | 这次工作的步骤/状态机 |
| `docs/verify/verification-results.json` / `.md` | 验证结果(技术细节) |
| `docs/verify/test-matrix.md` | 需求 ↔ 测试映射 + 回归矩阵 |
| `docs/memory/module-map.md` 等 | 模块边界、踩坑、项目规则 |
| `docs/reports/pilot-report.md` | 试点汇总报告(给团队看趋势) |
| `data/run-stats.jsonl` | **每次验证的统计**(累积,机器可读) |
| `data/run-summary.md` | 运行数据汇总(自动刷新) |
| `data/issues-log.md` | 问题台账(阻断 / 未覆盖 / 需人工) |

> 普通使用你只需关心 `SUMMARY.md`,其余是给工程/审计/团队复盘用的。

> **`data/` 是框架自动累积的实证数据**:每次验证后,框架把这次的统计(`run-stats.jsonl`)、汇总(`run-summary.md`)和遇到的问题(`issues-log.md`)追加/刷新到目标项目的 `data/`。框架被用得越多,数据和问题台账越全——这是给"想用真实数据看框架表现"准备的。注意区分"门禁机制有效性"与"生产 ROI"。

---

## 九、跨平台 / 团队 / CI

- **平台**:macOS / Linux / Windows 都支持(每个命令都有 `.sh` 和 `.bat`,纯 Python 逻辑跨平台)。
- **CI**:框架自带 `.github/workflows/`,会在三平台跑端到端冒烟测试,并校验技能副本一致性。
- **团队复盘**:`metrics` 子命令能聚合多次运行/多个项目的指标(规格覆盖率、验证通过率等)到 `docs/reports/pilot-summary.*`。

---

## 十、常见问题

**Q: 第一次验证就红灯,正常吗?**
A: 常见。多半是规格里的确认复选框还没勾,或影响分析没填完。AI 会补好重跑。它是"必须填清楚才放行",不是出错。

**Q: 显示 `Status: Works` 但不是 `DONE`,能用吗?**
A: 能。`Works` 表示功能好了、测试过了、没有阻断问题,只是有**可选**检查没跑(比如机器没装安全扫描)。括号里列的都是可选项,不是失败。

**Q: 它会自动改我的业务代码吗?**
A: 用 `/ai-build` 时会(这就是"实现")。但有红线:涉及破坏性操作、生产数据、密钥、权限时它会停下来问你。

**Q: 我是纯新手,完全不懂工程,能用吗?**
A: 能用 `/ai-build` 说需求、看大白话结果。但要知道:**真正的代码理解和判断是 AI 在背后做的**,框架保证流程和门禁。它适合"让 AI 在纪律下帮你干活",不是"教你写代码"。

---

## 一句话总结

**装一次 → 一句话提需求 → 看一句大白话结果。** 中间的规格、测试、验证门禁,框架替你盯着;AI 替你干活;你只管说需求、看结果。
