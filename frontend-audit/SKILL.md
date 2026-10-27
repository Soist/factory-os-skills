---
name: frontend-audit
description: "Skill: frontend-audit"
---

> 注：下文 `frontend/src/...`、`.interface-design/` 等路径是 React + 设计系统项目的示例，按当前仓库实际结构替换；仓库没有对应物就跳过该项。

# Skill: frontend-audit

Role: Senior Frontend Architect & Design System Lead.

Objective: Audit the frontend codebase to identify technical debt and UI/UX fragmentation. Find redundant implementations and propose a unified component strategy.

## 触发条件

**USER TRIGGER**：用户说「审计前端」「前端审计」「查前端技术债」「frontend audit」，或调用 `/frontend-audit`。
**AUTO TRIGGER**：无（此审计成本较高，仅按需执行）。
**DO NOT TRIGGER**：构建具体功能时不触发。

## 审计维度

### 1. 组件重复与碎片化（CRITICAL）

- 扫描同一 UI 模式的多重实现（如多种 Alert、Modal wrapper、Input 变体）
- 识别应由全局 design token 或共享组件替代的一次性样式
- 为核心元素（Button、Input、Feedback 状态）提出「单一来源」方案
- **参照 `frontend/src/index.css` 的 `@layer components` 已有组件类**，找出未复用的地方

### 2. 视觉与交互一致性（HIGH）

- 检查偏离主题的间距、圆角、颜色用法
- 审计反馈组件（Loader、Toast、Error State）在所有视图中是否外观和行为一致
- 对照 `.interface-design/system.md` 和 `ui-design` skill 中的 token 表

### 3. 状态管理与逻辑同步（HIGH）

- 识别 Prop Drilling vs 应使用共享 State/Context 的场景（如统一通知队列）
- 检查表单校验逻辑是否在多个页面重复而非集中管理

### 4. 性能与渲染（MEDIUM）

- 找出重量级列表组件中的不必要重渲染
- 识别缺失 `useMemo` / `useCallback` 导致 prop 不稳定的位置

### 5. 类型安全与 Props API（MEDIUM）

- 审计组件 Props interface 的一致性（如同类组件 `onClick` vs `onPress`）
- 建议 props 严格类型化、可预测

### 6. 无障碍（a11y）与语义（HIGH）

- 确认统一组件使用正确的 ARIA role 和键盘焦点管理（尤其 Modal、Tabs）
- 检查 icon-only button 是否有 `aria-label`
- 检查表单 input 是否有关联 label

## 执行步骤

### Phase 1: 建立基线

1. 读取 `frontend/src/index.css` — 提取所有 `@layer components` 中的组件类
2. 读取 `.interface-design/system.md` — 获取 design token 基准
3. 读取 `frontend/src/types.ts` — 了解类型定义
4. 列出 `frontend/src/components/` 下所有组件文件

### Phase 2: 逐维度扫描

对上述 6 个维度依次扫描：

- **组件重复**：Grep 相似模式（如 `className=.*rounded.*border.*bg-`），与已有组件类交叉比对
- **Token 偏离**：Grep 原始 Tailwind 颜色类（`bg-zinc-`, `bg-gray-`, `text-slate-` 等）在 JSX 中的使用
- **Prop Drilling**：追踪从 App.tsx 向下传递超过 2 层的 props
- **重渲染风险**：查找内联对象/函数作为 props 传递的模式
- **类型一致性**：审计 `interface.*Props` 定义
- **a11y**：Grep `<button` 和 icon 组件，检查 `aria-label` 覆盖率

### Phase 3: 输出报告

按以下格式输出：

```markdown
# 前端审计报告

## 概要
- 审计范围：X 个文件，Y 个组件
- 发现问题：N 个（Critical: a, High: b, Medium: c）
- 低风险：<列 1-3 个可直接改的项>
- 高风险：<列 1-3 个需确认的高 ROI 项>
- 安全执行：<如何在拿到用户确认后安全落地高风险项>

## 发现详情

### [维度名] — [严重级别]

**问题**：<描述>
**位置**：`file:line`
**现状**：<代码片段>
**建议**：<修复方案>
**优先级**：Critical / High / Medium

## 统一组件策略建议

### 需要抽取的新组件
| 组件名 | 替代现有 | 所在文件 |
|--------|---------|---------|

### 需要推广的已有组件
| 组件/类 | 未使用位置 | 应替换的代码 |
|---------|-----------|------------|

## 行动计划
1. [最高优先级修复]
2. ...
```

## 注意

- 不主动修改代码，仅输出分析报告
- 发现问题时给出具体文件路径和行号
- 对照项目已有的 design system（`system.md`、`ui-design`）评判，不引入外部标准
- 关注实际影响，不报告无实际危害的 lint 级问题
- `低风险` 优先收录：局部样式或 token 对齐、已有组件复用、a11y 补充、局部 props 规范化
- `高风险` 优先收录：共享组件收敛、状态管理迁移、会波及多个页面或流程的结构性调整

## Fix Follow-through

如果后续用户让 AI 实施本审计中的建议，凡是会抽取共享组件、统一样式 token、迁移状态管理、删除重复 UI 模式或收敛 props API 的改动，实施完成后必须追加 `/cleanup-followthrough`。

最低检查项：
- 旧组件 / 旧样式组合 / 旧 props 变体是否已真正删除
- 页面里是否还残留旧实现路径或临时兼容分支
- tests / stories / fixtures / 注释是否仍引用旧组件名或旧交互
- 是否出现“双轨制”UI：新共享组件已加，但旧 ad-hoc 实现仍在继续活着
