---
name: implementation-path-audit
description: "Umbrella audit for wrong owner, multiple implementation paths, scattered logic, and unclear code placement. USER TRIGGER: 'implementation path audit', 'path audit', 'architecture path audit', 'how should this be built audit', '实现路径审计'. AUTO TRIGGER: do not auto-trigger."
---

# Implementation Path Audit

Scan the codebase for cases where there is no single obvious way to implement or modify a behavior. This skill intentionally consolidates several adjacent concerns into one audit: wrong owner, multiple implementation paths, scattered logic, and unclear code placement. Default mode is analysis only. The primary goal is to identify the single highest-ROI path correction that will make future feature work and bug fixes quicker, easier to place, and harder to get wrong.

## Trigger

- USER TRIGGER: 'implementation path audit', 'path audit', 'architecture path audit', 'how should this be built audit', '实现路径审计'
- `/implementation-path-audit:feature <FEATURE>` — feature-focused mode (see below)
- AUTO TRIGGER: do not auto-trigger
- DO NOT TRIGGER: when the user already wants a precise code change, or when a narrower existing audit is explicitly requested and clearly sufficient

## Workflow

**角色**：你是一个高级架构审计员。你的任务不是找“代码哪里不优雅”，而是找出代码库中**实现路径不清晰**的问题：同类修改可以走多条路、真正 owner 不明确、逻辑散落在多个位置、或者新代码很难判断该放在哪。

**这不是大而空的架构评论**。你必须只输出 1 个最高 ROI 建议，并且证明它能明显降低未来 AI/人工修改成本。

**本技能合并关注 4 类问题**：
- **Wrong owner**：逻辑被写在 caller / page / route，而不是真正 owner
- **Multiple paths**：同类功能已有 2+ 套实现方式，大家可以绕过 canonical path
- **Scattered logic**：同一个概念散在多个位置才能看懂或改对
- **Placement ambiguity**：新逻辑到底应进 hook / utility / service / component / route 不清楚

**任务**：扫描以下目录，找出最值得先统一的一条实现路径。

扫描范围：
- 核心业务流程的前端组件目录（重点）
- 页面组件目录
- hooks、adapters、utilities 目录
（按本仓库实际路径）
- `servers/services/` — 后端 service 层
- `servers/routes/` — 后端路由层

在识别候选之前，先快速盘点测试资产：
- 现有单元测试、集成测试、E2E/页面流程测试分别保护了哪些实现路径
- 候选改动点附近是否已有 fixtures、mock、helpers 可复用
- 如果把实现路径收敛到 canonical path，哪些行为目前没有测试保护

测试盘点必须参与 ROI 判断。没有测试保护的“路径统一”通常不该排第一。

**识别标准**（满足任意两条即报告）：
1. 同一类修改可以通过 2+ 套不同路径完成，且没有明确 canonical path
2. 调用方在承担本应由 shared hook / utility / service / adapter 负责的规则
3. 同一个概念分散在 3+ 个位置，删除或修改时必须联动多处
4. 新需求来了，合理人类/AI 也很难立刻判断“代码应该放哪”
5. 为了兼容历史写法，代码中出现 repair / fallback / duplicate branches，说明路径没有收敛

## 输出要求

先筛选候选，再只给出**1 个最高 ROI 建议**作为主结论。必要时可附带 1-2 个次选项，但主结论必须明确回答：

- 这类修改未来应该走哪一条 canonical path
- 现在有哪些实现路径在竞争
- 为什么先统一这里，对未来开发/修 bug 最有帮助
- 现有测试能兜住多少风险，还缺什么测试

### 主结论格式

```text
## Highest ROI Suggestion

### [概念名] — [当前存在 N 条实现路径 / 散在 N 个位置]

**Canonical path**：[`hook / utility / service / component / adapter / form model`]

**现有路径清单**：
- `file:line` — 当前这条路径在做什么
- `file:line` — 当前这条路径在做什么
- ...

**为什么它是最高 ROI**：
- [收益] 统一后会减少什么放置歧义、重复实现、补丁式修复
- [范围] 为什么 canonical path 边界相对清晰
- [对比] 为什么它优先于其他候选

**路径问题说明**：
- 现状：现在为什么有多条路、错层 owner、或散布逻辑
- 正解：以后同类修改应该默认走哪条路
- 结果：为什么这会让未来修改更快、更稳、更不容易写歪

**建议收敛方向**：[统一到 hook / utility / service / component / adapter / form model]

**改动方案草图**：
- [canonical path 应承担的职责]
- [调用方如何变薄]
- [哪些旧路径、重复 helper、fallback 分支应被删除]

**实现风险评估**：
- 风险等级：[High / Medium / Low]
- 风险原因：[跨层耦合、兼容性假设、时序、副作用、隐式契约等]
- 受影响面：[用户流程 / 页面 / API / 后端流程]

**测试套件评估**：
- 现有测试保护：[列出已有测试及其能覆盖的 canonical path 行为]
- 当前缺口：[列出路径统一后最容易回归的行为]
- 建议补充测试：[优先写哪些单测 / 集成 / E2E，为什么]
- 测试后的风险判断：[如果补上建议测试，风险会如何下降]

**预估改动量**：[小 = <30行 | 中 = 30-100行 | 大 = >100行]

**实施后必须追加的清理检查**：
- 检查旧路径是否真的被删掉，而不是和新路径并存
- 检查 caller / page / route 中的 repair / fallback / duplicate branches 是否已 stale
- 检查命名、注释、测试夹具是否仍暗示旧实现路径
```

### 次选项格式（可选，最多 2 个）

用简短格式说明：
- `概念名`
- canonical path 应该是什么
- 为什么次于主结论
- 风险等级
- 如果主结论不做，它是否是第二顺位

## 排序与判断规则

- ROI = 预期收益 ÷ 实施与验证成本，不是单看“架构不完美程度”
- 同等收益时，优先选择 canonical path 清晰、调用点集中、容易补测试的候选
- 如果一个候选需要先创造全新抽象、跨太多层重写、且没有测试，不应排第一
- 优先抓“以后还会反复改”的高频路径，而不是一次性冷门代码

## Fix Follow-through

如果后续用户让 AI 实施你提出的主结论，实施完成后必须追加 `/cleanup-followthrough`，至少检查：
- 旧路径、旧 helper、旧 fallback 是否已删除
- 是否出现“双轨制”实现：新 canonical path 已有，但旧调用方式还在继续活着
- 是否需要同步更新 tests / runbook / coding practices，让未来 AI 知道只走新路径

## 约束

- 只分析，不写代码
- 不报告”可能”问题，每个主结论或次选项都必须指出具体文件和行号
- 不报告纯命名或样式问题——只关注实现路径清晰度
- 不默认列很多候选；默认只输出 1 个主结论
- 不脱离测试上下文谈风险；如果没查测试，就不能声称”低风险”

---

## `:feature` 模式 — 追踪单个 feature 的散落逻辑

### 触发
`/implementation-path-audit:feature <FEATURE>` — 用户指定一个具体 feature/concept，审计它的逻辑散落在哪里、哪里是 owner、哪里应该收敛。

### 和默认模式的区别
| 维度 | 默认模式 | `:feature` 模式 |
|------|---------|----------------|
| 起点 | 扫全库，发现问题 | 从已知 feature 出发，追踪散落 |
| 目标 | 找最高 ROI 的统一机会 | 枚举该 feature 所有散落点 |
| 输出 | 1 个主建议 | 散落点清单 + owner 建议 |

### 执行流程

1. **搜索**：在所有层（前端 hooks/components/types，后端 services/schemas/routes，tests，runbooks）搜索 `<FEATURE>` 相关的关键词、类型名、注释。

2. **分类每个出现点**：

   | 类别 | 含义 |
   |------|------|
   | **OWNER** | 唯一决策来源，其他地方应读它 |
   | **CONSUMER** | 正确消费 owner 的调用方 |
   | **DUPLICATE** | 独立重新计算了相同逻辑，应删除 |
   | **COMPAT** | 向后兼容/迁移代码，应有明确退出条件 |

3. **识别跨层重复**（重点）：同一个决策被后端 + 前端各自独立实现是 OK（防线层次不同），但前端组件 A 和前端组件 B 各算一次就是 DUPLICATE。

4. **输出**：

```text
## Feature Scatter Audit: [FEATURE]

### Scatter Map
| 位置 | 类型 | 做了什么 |
|------|------|---------|
| `file:line` | OWNER / CONSUMER / DUPLICATE / COMPAT | 一句话说明 |

### Owner Assessment
当前 owner 是：[file] — [是否合适，理由]
建议 canonical owner：[file，若需要调整]

### Consolidation Opportunities
- [HIGH/MEDIUM/LOW] `file:line` — [为什么是 DUPLICATE，应改为消费 owner]
- [HIGH/MEDIUM/LOW] `file:line` — [COMPAT 代码的退出条件是什么]

### 维护负担评估
删除哪些文件/函数可以让 feature 完全可追踪：[列表]
删完后要改一个 feature 只需改几处：[数字]
```

### 约束（`:feature` 模式特有）
- 不把跨层重复（backend guard + frontend hint）标为问题 — 它们服务不同目的
- COMPAT 代码只标记”应有退出条件”，不要求立即删除
- 优先找”前端内部”或”后端内部”的重复，这是真正的维护负担
