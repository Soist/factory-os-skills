---
name: error-handling-audit
description: "Skill: error-handling-audit"
---

# Skill: error-handling-audit

角色：Senior Engineer，专注错误处理质量审计。

## 触发条件

**USER TRIGGER**：用户说「审计错误处理」「查 catch 问题」「检查异常处理」「error handling audit」，或调用 `/error-handling-audit`。
**AUTO TRIGGER**：无（按需执行）。
**DO NOT TRIGGER**：构建新功能时不触发（只做专项审计时使用）。

---

## 审计目标

找出所有**静默吞掉异常**或**错误处理不规范**的位置。项目原则：所有 catch 必须至少记录错误，绝不静默。

除严重级别外，概要里还要补一个简短风险摘要：
- **低风险**：补日志、补 `exc_info`、统一 `logger` / `console.error`、补 trace metadata
- **高风险**：会改变错误传播、接口返回、前端错误态、重试或降级语义，需用户确认

---

## 审计流程

### Phase 1：后端扫描（Python）

**1.1 空 except / 吞异常**

```
Grep: except.*:\s*$  (后面跟 pass 或只有 print)
Grep: except Exception.*pass
Grep: except:$
```

- 找 `except: pass`、`except Exception: pass`、`except ...: continue`（无日志）
- 找只 `print(e)` 而不用 `logger.error/exception` 的 catch

**1.2 禁用 print() 作为错误输出**

```
Grep: print(.*[Ee]rror|print(.*[Ee]xcep|print(.*[Ff]ail
```

- 运行时信息必须用 `logger`（`from src.utils.logger import get_logger`），禁止 `print()`

**1.3 ExtractionError 未携带 trace metadata**

```
Grep: raise ExtractionError
```

- 每处 `raise ExtractionError(...)` 应有 `metadata=trace.to_metadata_dict()`
- 失败前应调用 `trace.set_error(exc)` + `trace.finalize(success=False)`

**1.4 analytics log_error 调用不完整**

```
Grep: log_error(
```

- 必须同时传 `error_type`（`TYPE_*` 常量）和 `error_code`（具体码常量）
- 不得省略其中一个，不得硬编码字符串

**1.5 裸 logger.error 未附上 exc_info**

```
Grep: logger\.error(.*except
```

- 在 except 块内用 `logger.error()` 时，异常应通过 `logger.exception()` 或 `logger.error(..., exc_info=True)` 记录 stack trace，不要只记文字

---

### Phase 2：前端扫描（TypeScript/React）

**2.1 空 catch 块**

```
Grep: catch\s*\([^)]*\)\s*\{\s*\}
Grep: catch\s*\(\s*\)\s*\{
Grep: \/\*\s*ignore\s*\*/
```

- 任何空 catch 或 `/* ignore */` 都是违规

**2.2 catch 中无 console.error**

扫描所有 catch 块，找出：
- catch 块中没有 `console.error` / `console.warn`
- catch 块中只有 `setLoading(false)` 等 state 清理，没有错误记录

**2.3 catch 中生成假数据冒充成功**

```
Grep: catch.*\{[^}]*return.*\[\]
Grep: catch.*\{[^}]*setState.*\[\]
```

- API 失败不得用空数组、mock 数据或 fallback 值悄悄替换，必须展示错误状态

**2.4 Promise 未处理**

```
Grep: \.then([^)]*)\s*(?!\.catch)
Grep: async.*\{(?!.*try)
```

- `fetch().then()` 没有 `.catch()` 链
- async 函数没有 try/catch 包裹（调用层也没有 `.catch()`）

---

### Phase 3：输出报告

```markdown
# 错误处理审计报告

## 概要
- 扫描范围：后端 X 个文件，前端 Y 个文件
- 违规数：N 个（Critical: a，High: b，Medium: c）
- 低风险：<列 1-3 个可直接改的项>
- 高风险：<列 1-3 个需确认的高 ROI 项>
- 安全执行：<如何在拿到用户确认后安全落地高风险项>

## 违规详情

### [违规类型] — [严重级别]

**位置**：`file:line`
**问题**：<描述>
**现状**：
```code```
**修复建议**：<具体修法>

## 修复优先级

| 优先级 | 数量 | 典型位置 |
|--------|------|---------|
| Critical | N | ... |
| High | N | ... |
| Medium | N | ... |

## 行动计划
1. 先处理低风险项
2. 高风险项在用户确认后按安全执行方案处理
```

---

## 严重级别定义

| 级别 | 含义 |
|------|------|
| Critical | 完全静默：`except: pass`、空 catch、假数据 fallback |
| High | 有记录但信息不足：只 `print()`、缺 `exc_info`、缺 `error_type` |
| Medium | 风格不一致：用 `console.log` 而不是 `console.error`、Promise 链缺 `.catch()` |

---

## 注意

- 不主动修改代码，仅输出审计报告
- 对照项目规范（`agent-profile/src/shared/instructions/PROJECT.md`、`frontend-coding-practices.md`）判断违规
- 关注实际遗漏的错误可观测性，不报告格式层面的 lint 风格问题
- 优先扫描高频路径：本仓库的路由层、服务层、外部调用封装、前端源码目录（按实际结构）

## Fix Follow-through

如果后续用户让 AI 实施本审计中的建议，凡是会统一 catch 逻辑、抽取错误处理 helper、收口错误态、删除 fallback 或改变错误传播路径的改动，实施完成后必须追加 `/cleanup-followthrough`。

最低检查项：
- 旧 silent catch / fallback 分支 / mock-success 路径是否真的删掉
- 旧 logger / console 模式是否还在附近文件继续被使用
- tests / fixtures / 错误文案是否仍暗示旧错误行为
- 是否出现“双轨制”错误处理：新规范已引入，但旧处理方式仍并存
