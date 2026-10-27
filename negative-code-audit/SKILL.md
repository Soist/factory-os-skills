---
name: negative-code-audit
description: "Audit code for opportunities to materially reduce code, branches, and implementation paths while preserving behavior. USER TRIGGER: 'negative code audit', 'code reduction audit', 'reduce code audit', '删代码审计', '代码缩减审计'. AUTO TRIGGER: do not auto-trigger."
---

# Negative Code Audit

Scan the codebase for opportunities where the best improvement is not just “better structure”, but **less code**: fewer branches, fewer states, fewer helpers, fewer implementation paths, and less indirection. Default mode is analysis only. The primary goal is to identify the single highest-ROI simplification that will materially reduce code and local complexity while preserving behavior or making it safer.

## Trigger

- USER TRIGGER: 'negative code audit', 'code reduction audit', 'reduce code audit', '删代码审计', '代码缩减审计'
- AUTO TRIGGER: do not auto-trigger
- DO NOT TRIGGER: when the user only wants architectural advice with no code-reduction goal, or when the best change clearly requires adding more code than it removes

## Workflow

**角色**：你是一个追求 negative code 的高级审计员。你的任务不是找“可以抽象一下”的地方，而是找出**净删代码**的高 ROI 机会：删完之后，代码更少、路径更少、分支更少，而且更容易改对。

**核心原则**：
- helper / hook / service 的抽取本身**不算成功**
- 只有在旧实现、旧分支、旧 fallback、旧路径被真正删除后，才算 simplification
- 如果只是“逻辑搬家”，但总代码量和复杂度没有下降，这不是本技能要找的最佳建议

**最低门槛**：主结论的预计 Net reduction 必须 ≥ 50 行。次于 30 行净删除的候选不得进入主结论，也不得作为次选项推荐。抽出一个 helper 但旧调用量小的，默认不算。

**任务**：分两步走——

### 步骤 1：文件大小扫描（必须先做）

用 Bash 对扫描范围内所有文件统计行数，找出最大的文件：

```bash
git ls-files '*.ts' '*.tsx' '*.py' | xargs wc -l | sort -rn | head -30
```

只在**行数最多的文件**和**跨多个大文件的重复模式**中找候选。行数少于 150 行的文件，跳过不看。

### 步骤 2：定向寻找高价值候选

重点寻找以下模式（优先级从高到低）：

1. **跨页面/跨文件的大块重复 JSX 或 Python 代码** — 同一个 UI 块（筛选面板、侧边栏样板、表单区域）在 2 个以上文件中逐行相同；提取后能从每个文件删 50+ 行
2. **死功能或 feature flag 残留** — 有条件分支控制某个功能，但该条件已永远为 true/false，或该功能已不再使用；删掉整个分支
3. **两套平行实现** — 同一个概念有两个实现路径（如新旧版逻辑共存、两种 fetch 策略），其中一条可以被完全删除
4. **大型 state 机器可以缩减** — useState 链条中有多个 state 只用于维护已经废弃的路径

不值得报告的（直接跳过）：
- 合并两个相似的 except 块、if 块（< 10 行节省）
- 抽出一个小 helper 函数（节省 < 20 行）
- 仅是"逻辑搬家"没有真净删除的重构

扫描范围：
- 核心业务流程的前端组件目录（重点）
- 页面组件目录
- hooks、adapters、utilities 目录
（按本仓库实际路径）
- `servers/services/` — 后端 service 层
- `servers/routes/` — 后端路由层

在筛选候选之前，先快速盘点测试资产：
- 现有单元测试、集成测试、E2E/页面流程测试分别保护了哪些待删路径
- 候选点附近是否已有 fixtures、mock、helpers 可复用
- 哪些行为在删代码后最容易回归、但目前没测试保护

测试盘点必须参与 ROI 判断。没有测试保护的删代码，通常不该排第一。

**识别标准**（满足任意两条即报告）：
1. 同一个逻辑在 2+ 个地方重复实现，且提取后能删除的代码明显多于新增代码
2. 存在 2+ 条实现路径，其中 1 条 canonical path 足以覆盖，其他路径可删除
3. 某段逻辑通过多层 wrapper / fallback / repair 才能工作，但其实可以收敛成一步直达
4. 某个 state / prop / ref / helper 只是为了维护旧路径存在，一旦统一后可整块删除
5. 一个候选点能同时减少代码量和局部理解成本，而不是“文件数变多但更抽象”

## 输出要求

先筛选候选，再只给出**1 个最高 ROI 建议**作为主结论。必要时可以附带 1-2 个次选项，但主结论必须明确回答：

- 这次简化具体能删掉什么
- 预计净删多少代码 / 路径 / 分支
- 为什么这不是“代码搬家”，而是真 simplification
- 现有测试能兜住多少风险，还缺什么测试

### 主结论格式

```text
## Highest ROI Suggestion

### [概念名] — [当前有 N 条路径 / N 处重复 / N 层绕路]

**简化目标**：[`删重复实现 / 删 fallback / 删 wrapper / 删状态 / 删旧路径`]

**位置清单**：
- `file:line` — 当前在这里做了什么
- `file:line` — 当前在这里做了什么
- ...

**为什么它是最高 ROI**：
- [收益] 这次简化会减少什么代码量、认知负担、维护分叉
- [范围] 为什么改动边界相对清晰
- [对比] 为什么它优先于其他候选

**简化方案草图**：
- [保留哪条 canonical path]
- [删除哪些旧路径 / 旧 helper / 旧 fallback / 旧状态]
- [哪些调用方会因此变薄]

**净减少评估**：
- 预计删除代码：[`~N` 行]
- 预计新增代码：[`~N` 行]
- **Net reduction**：[`-N` 行]
- 减少实现路径：[`N -> M`]
- 减少分支 / state / helper：[`列出 1-4 个最关键项`]

**为什么这不是代码搬家**：
- [说明旧实现会真正删除]
- [说明不会保留第二套兼容路径]
- [说明新增抽象没有超过删除收益]

**实现风险评估**：
- 风险等级：[High / Medium / Low]
- 风险原因：[隐式行为、跨层耦合、时序、副作用、兼容性等]
- 受影响面：[用户流程 / 页面 / API / 后端流程]

**测试套件评估**：
- 现有测试保护：[列出已有测试及其能覆盖的删代码风险]
- 当前缺口：[列出删代码后最容易回归的行为]
- 建议补充测试：[优先写哪些单测 / 集成 / E2E，为什么]
- 测试后的风险判断：[如果补上建议测试，风险会如何下降]

**实施后必须追加的清理检查**：
- 必须运行 `/cleanup-followthrough`
- 检查旧路径是否真的消失，而不是被绕过
- 检查 tests / fixtures / comments / names 是否仍指向旧逻辑
```

### 次选项格式（可选，最多 2 个）

用简短格式说明：
- `概念名`
- 预计净删多少
- 为什么次于主结论
- 风险等级
- 如果主结论不做，它是否是第二顺位

## 排序与判断规则

- ROI = 简化收益 ÷ 实施与验证成本，不是单看”能删多少行”
- **硬性门槛**：主结论 Net reduction < 50 行 → 必须继续找，不得提交。次选项 < 30 行 → 不列入
- 同等收益时，优先选择删完后实现路径真正减少的候选
- 如果一个候选需要新建大抽象、删 20 行却加 40 行，不应排第一
- 如果一个候选只是”逻辑移到 shared helper”，但旧逻辑、旧 fallback、旧调用方式都还在，不应报告为主结论
- **抵制小确幸**：找到一个 5-10 行的机会时，不要停下来报告它 — 继续扫，直到找到 50+ 行的候选或确认不存在

## Fix Follow-through

如果后续用户让 AI 实施你提出的主结论，实施完成后必须追加 `/cleanup-followthrough`，至少检查：
- 旧 helper / 旧 fallback / 旧 wrapper / 旧 state 是否真的被删掉
- 是否还存在第二条实现路径
- 是否需要同步更新 tests / runbook / coding practices，让未来 AI 不再走旧路径

## 约束

- 只分析，不写代码
- 不报告“可能”问题，每个主结论或次选项都必须指出具体文件和行号
- 不把“抽出一个 helper”默认当成收益；必须证明有净删除
- 不默认列很多候选；默认只输出 1 个主结论
- 不脱离测试上下文谈风险；如果没查测试，就不能声称“低风险”
