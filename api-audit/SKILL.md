---
name: api-audit
description: "Skill: api-audit"
---

# Skill: api-audit

角色：Senior API Architect，专注 REST API 设计质量审计。

## 触发条件

**USER TRIGGER**：用户说「审计 API」「API 设计好吗」「check our API」「api audit」，或调用 `/api-audit`。
**AUTO TRIGGER**：Claude 新增路由文件或大幅修改 API response shape 时，自动审计新增接口的设计质量。
**DO NOT TRIGGER**：修复已有接口的业务逻辑 bug 时不触发。

---

## 审计流程

### Step 1：扫描现有端点

读取路由文件，列出所有端点（方法 + 路径 + 简述）。
本项目路由在 `servers/routes/`。

### Step 2：逐维度评分

对每个端点按下面 7 个维度打标（✅ 合格 / ⚠️ 可改进 / ❌ 违规），汇总后给出优先级。

### Step 3：输出报告

- 按优先级（Critical / High / Medium / Low）分组列出问题
- 每个问题：路径 + 问题描述 + 修改建议 + 理由
- 在概要中额外输出简短风险摘要：
  - 低风险：可直接改的局部、兼容修复
  - 高风险：高 ROI 但会影响 API 契约或调用方行为，需用户确认
  - 补一句如何安全执行高风险项（如版本迁移、灰度、调用方核对、回归验证）
- 最后给出清洁版端点表

---

## 七个审计维度

### 1. HTTP 方法语义

| 方法 | 正确用途 | 常见误用 |
|------|---------|---------|
| GET | 只读，无副作用 | 用 GET 触发写操作 |
| POST | 创建资源 / 触发业务命令 | — |
| PUT | 完整替换（幂等） | 把 PATCH 的语义用在 PUT |
| PATCH | 字段级部分更新，**无副作用** | 用 PATCH 做状态机转换 |
| DELETE | 删除（幂等） | — |

**关键规则**：PATCH 改的是字段，不是业务状态。如果 `status` 字段变化触发邮件/付款/ERP 调用，用 POST 到 action sub-resource，不用 PATCH。

### 2. 资源命名

- 路径段用**名词复数**（`/order-sheets`，不是 `/getOrderSheet`）
- 小写 + 连字符（`/order-sheets`，不是 `/orderSheets` 或 `/order_sheets`）
- 层级最多 2 层：`/order-sheets/{id}/items` ✅；再往下的 `/items/{id}/sub-items/{id}/details` ❌
- Action sub-resource 例外：`/items/{id}/submit` 是动词但可接受，因为它是业务命令

### 3. 状态机转换

- 有副作用的状态转换（→ ERP、→ 发通知、→ 锁定记录）必须用 **POST + 命名 action 端点**
- `PATCH {status: "cancelled"}` 对简单、无副作用的状态可以接受；对复杂业务命令不行
- Action 端点使 API surface 自文档化：哪些转换合法，从 URL 就能看出来

```
✅  POST /items/{id}/submit
✅  POST /items/{id}/hold      {reason: "..."}
✅  POST /items/{id}/discard   {reason: "..."}
❌  PATCH /items/{id}          {status: "on_hold", hold_reason: "..."}
```

### 4. 路径参数稳定性

- 路径参数必须是**稳定标识符**（UUID / 业务 ID），不能是位置索引（`/items/0`、`/items/2`）
- 位置索引在删除/重排后失效，导致幂等性破坏和 cache 污染
- 检查：路径中有没有整数 index 被当作资源地址

### 5. HTTP 状态码正确性

| 场景 | 正确码 |
|------|-------|
| 创建成功 | 201 Created |
| 删除成功 | 204 No Content |
| 异步接受 | 202 Accepted |
| 校验失败 | 422 Unprocessable Entity |
| 认证缺失 | 401 Unauthorized |
| 权限不足 | 403 Forbidden |
| 资源不存在 | 404 Not Found |
| 冲突（如锁已被持有） | 409 Conflict |

**反模式**：`200 OK` + `{"success": false, "error": "..."}` —— HTTP 状态码存在的意义就是表达这个。

### 6. 响应结构一致性

**集合响应** — 永远不要返回裸数组，无法向后兼容地加 metadata：

```json
{
  "data": [...],
  "meta": { "total": 150, "page": 1, "per_page": 50, "has_more": true }
}
```

**单资源响应** — `{"data": {...}}` 与集合保持一致。

**错误响应** — 参考 RFC 9457（`application/problem+json`）：

```json
{
  "type": "https://api.example.com/errors/validation-failed",
  "title": "校验失败",
  "status": 422,
  "detail": "reason 字段不能为空",
  "instance": "/api/v1/order-sheets/abc/items/xyz/hold"
}
```

- `detail` 面向开发者，不要暴露 stack trace 或 DB 错误
- 多字段校验失败时，在 `errors` 数组里逐字段列出，不要合并成一条消息

### 7. API 版本策略

- 内部 API 最低要求：URI 前缀 `/api/v1/`，从第一天就加，否则日后无痛加版本的机会已过
- 不破坏现有 client 的变更（加字段、加端点）无需新版本
- 破坏性变更（删字段、改语义、改状态码）需要 `/v2/` 或协商的版本迁移计划

---

## 常见反模式速查

| 反模式 | 问题 | 修复 |
|--------|------|------|
| `GET /createOrder` | 动词在路径里 | `POST /orders` |
| `PATCH {status: "cancelled"}` 有副作用 | 隐藏的业务命令 | `POST /orders/{id}/cancel` |
| `/items/0`、`/items/2` 位置索引 | 不稳定，删行后失效 | 改用 `item_id` |
| 裸数组 `[{...}, {...}]` | 无法加 meta | `{"data": [...], "meta": {...}}` |
| `200 OK` + `{"error": "..."}` | HTTP 码传递的信息被浪费 | 用正确的 4xx/5xx |
| `/api/submit-erp` 暴露实现细节 | 与技术实现耦合 | `/items/{id}/submit` |
| 路径用 camelCase `/orderSheets` | 不符合 URL 规范 | `/order-sheets` |
| 无版本策略 | 第一次破坏性变更无退路 | 从第一天加 `/v1/` |
| 单条错误消息覆盖多字段校验失败 | 调试体验差 | `errors` 数组逐字段 |
| 过深嵌套 `/a/{id}/b/{id}/c/{id}/d` | 不可书签化，不稳定 | 超过 2 层用查询参数扁平化 |

---

## 幂等性检查

对每个 POST 端点问：这个操作被调用两次，会发生什么？

- 如果答案是「两次结果相同」→ 可以不加 Idempotency-Key（天然幂等）
- 如果答案是「第二次创建了重复记录/发了两封邮件/扣了两次款」→ 需要幂等键机制：
  - 客户端发 `Idempotency-Key: <uuid>` header
  - 服务端缓存响应（TTL 24h），相同 key 直接返回缓存
  - 同 key + 不同 body → 返回 409

本项目中 `/submit` 的幂等性由 ERP 自身的 `mxbh` 唯一约束保证；`/retry` 使用已存储的 finalValues，天然幂等。

---

## 与其他技能协作

| 场景 | 技能 |
|------|------|
| 发现端点需要新业务逻辑 | 直接在 `servers/routes/` 修改 |
| 发现前端调用了已废弃端点 | `/frontend-audit` 扫描调用方 |
| 发现跨系统集成 / Job 契约问题 | 参考仓库里对应的集成文档（如有） |
| 需要设计新端点 | 先对照本 skill 的 7 个维度再落码 |

---

## 报告输出要求

在 `## 概要` 中只额外给出一个简短 `风险摘要`，不要展开成过多字段。

推荐输出格式：

```markdown
# API 审计报告

## 概要
- 扫描范围：X 个路由文件，Y 个端点
- 发现问题：N 个（Critical: a，High: b，Medium: c，Low: d）

- 低风险：<列 1-3 个可直接改的项>
- 高风险：<列 1-3 个需确认的高 ROI 项>
- 安全执行：<如何在拿到用户确认后安全落地高风险项>

## 问题详情

### [问题类型] — [严重级别]

**端点**：`METHOD /path`
**问题**：<描述>
**建议**：<修复方案>
**理由**：<为什么>
```

## Fix Follow-through

如果后续用户让 AI 实施本审计中的建议，凡是会引入共享 adapter / helper / serializer、迁移调用方、统一 response shape、删除旧接口路径或收敛实现路径的改动，实施完成后必须追加 `/cleanup-followthrough`。

最低检查项：
- 旧 response shape / 旧字段拼装 / 旧兼容分支是否已删除
- 调用方是否还保留旧 API 路径或旧 payload 结构
- tests / fixtures / API 文档是否仍描述旧契约
- 是否出现“双轨制”接口：新契约已加，但旧契约仍被继续依赖
