---
name: cleanup-followthrough
description: "Post-change audit for stale fallback logic, dead branches, duplicate helpers, and incomplete cleanup after fixes or refactors. USER TRIGGER: 'cleanup followthrough', 'followthrough audit', 'cleanup audit', 'post fix cleanup', '收尾清理审计'. AUTO TRIGGER: do not auto-trigger."
---

# Cleanup Followthrough

Run a short, targeted second pass after a fix, refactor, or path consolidation. The goal is to catch the common AI failure mode where the main behavior is fixed, but old branches, fallback logic, duplicate helpers, stale parameters, or misleading tests remain behind. **Auto-fix low-LOE findings inline**; only pause to ask the user when a finding requires design judgment or is structurally risky.

## Trigger

- USER TRIGGER: 'cleanup followthrough', 'followthrough audit', 'cleanup audit', 'post fix cleanup', '收尾清理审计'
- AUTO TRIGGER: do not auto-trigger
- DO NOT TRIGGER: tiny typo fixes, copy edits, or changes where no logic moved and no old path was displaced

## Workflow

**角色**：你是一个收尾审计员。你的任务不是重复主修复，而是在主修复完成后检查：旧世界是否真的被清掉了，还是只是“新逻辑搬进来了，但垃圾还留着”。

**适用场景**：
- 抽取 hook / utility / service 后
- 把逻辑从 page/route/caller 收回真正 owner 后
- 统一实现路径、删除重复逻辑后
- 修 bug 时新增了新规则、新分支或新 helper

**检查范围**：优先只查本次变更及其直接相邻调用点，不做全仓大扫除。

**核心检查项**：
1. 旧 fallback / repair / compatibility branches 是否已失去用途
2. 旧 helper / duplicated transform / duplicated validation 是否仍残留
3. 旧 props / params / refs / state / imports 是否已变成 stale
4. tests / fixtures / comments / names 是否仍描述旧行为或旧路径
5. 是否出现“双轨制”实现：新方法已存在，但旧方法仍在被继续使用

## 输出要求

如果没有发现问题，要明确写“未发现收尾遗漏”，并说明检查范围。

如果发现问题，**先按 LOE 分流**，再按严重性排序：

### Auto-fix policy

| LOE | 范围 | 行为 |
|-----|------|------|
| **低** | 改名 / 删 dangling pointer / 改 stale comment / 删未引用 import / 改 stale docstring / 单文件 ≤10 行机械替换 | 直接修，不问 |
| **低** | 删除明确已无 consumer 的 helper / dead branch（已验证 0 调用方） | 直接修，不问 |
| **中** | 改测试夹具结构 / 跨文件 rename / 改公共 API 签名 | 报告 finding + 给出修复方案，等用户确认 |
| **高** | 需要决定 owner / 需要产品/业务判断 / 改 DB schema / 行为变更 | 只报告，不修 |

任何会改变运行时行为、跨文件牵涉超过 2 个模块、或需要补/改测试断言的，都不算低 LOE。

### 输出格式

```text
## Cleanup Followthrough

### Scope checked
- `file`
- `file`
- ...

### Auto-fixed (low LOE)
- `file:line` — [改了什么]
- `file:line` — [改了什么]

### Findings requiring confirmation
- [High/Medium] `file:line` — [残留内容]
  为什么它是收尾遗漏：[一句话说明]
  建议动作：[删除 / 合并 / 改名 / 补测试 / 补文档]
  LOE 判断：[为什么不是低 LOE]

### Result
- [若无问题] 未发现收尾遗漏
- [若全部已 auto-fix] 本次主修复已完成清场（N 处低 LOE 已就地修复）
- [若有 Medium/High] 本次主修复已成立，剩 N 处需用户决策才能完成清场
```

## 排序与判断规则

- 优先报“会制造第二条实现路径”的残留
- 优先报“看起来还能用，但其实已经不该存在”的 fallback / compatibility 代码
- 优先报会误导未来 AI 的命名、测试、夹具、文档残留
- 不为追求整洁而报告边际收益很低的格式/样式问题

## 约束

- 默认只分析，不写代码
- 不做大范围 dead-code 扫描；只看本次改动相关范围
- 每个 finding 必须给出具体文件和行号
- 不把“也许以后能删”当 finding；必须说明为什么现在已经 stale
