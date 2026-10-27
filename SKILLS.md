# factory-os Skills 详细说明

factory-os 项目可用的 Claude Code skills。按优先级分类，每个 skill 包含用途、触发方式、典型场景。

## ⭐⭐⭐ 核心（必用）

### triage — 编码任务入口
**用途**：统一的编码任务分类、定范围、评估风险、TDD 计划、路由。

**触发**：`/triage` 或遇到新编码任务需要分析

**场景**：
- 新需求交过来，不知道从哪开始
- 有个模糊的想法，需要分解成可测试的步骤
- 大功能改动前，评估风险和依赖

**输出**：清晰的实现计划、风险评估、TDD 红绿步骤

---

### bug-fix — bug 修复流程
**用途**：先复现再修的 bug 修复，遵循 TDD 红绿流程。

**触发**：`/bug-fix` 或处理一个具体 bug

**场景**：
- 接到 bug 报告，需要复现、定位、验证修复
- bug 很诡异，需要系统地排查
- 修完了想确认没有引入新问题

**核心流程**：
1. 复现 bug（自动化测试）
2. 定位根因
3. 修复代码
4. 验证测试通过
5. 检查回归

**关键**：红测试 → 绿测试 → 重构（不是直接改代码）

---

### api-audit — REST API 设计审计
**用途**：审计后端 API 的设计质量（factory-os 有大量 API）。

**触发**：`/api-audit` 或新增/改动 API 端点

**场景**：
- 新写的 API 端点，想确保设计合理
- 改动一个已有的 API 前，想评估影响
- API 文档与实现不一致

**检查项**：
- HTTP 动词用法（GET/POST/PUT/DELETE）
- 路由设计（RESTful vs RPC）
- 请求/响应体结构
- 错误处理与状态码
- 认证与权限检查
- 版本管理

---

### security-audit — Web 安全审计
**用途**：审计 Web 应用安全（factory-os 有 WeChat 集成、权限系统）。

**触发**：`/security-audit` 或处理认证/授权/敏感数据

**场景**：
- 新增登录/权限逻辑
- 处理客户敏感数据（订单、客户资料）
- WeChat 回调、支付相关功能
- 数据库查询涉及行级隔离

**检查项**：
- SQL 注入防护
- XSS 防护
- CSRF 防护
- 认证状态管理
- 权限检查（见 `tests/test_principal.py`）
- 敏感信息日志泄露
- 行级隔离（RLS）
- WeChat 签名验证

---

### error-handling-audit — 错误处理审计
**用途**：审计错误处理（factory-os 是商业逻辑系统，不能吞异常）。

**触发**：`/error-handling-audit` 或修改异常处理逻辑

**场景**：
- 新增 try/except 块
- 与外部系统集成（飞书、支付、海天鑫 ERP）
- 数据库操作异常处理
- 异步任务错误处理

**检查项**：
- 异常被静默吞掉（without logging）
- 错误消息过于泛化
- 外来对象（库异常）直接拼进用户消息（见 `tests/test_wording.py`）
- 部分业务路径缺少异常处理
- 重试逻辑不当（可能导致重复操作）

---

## ⭐⭐ 常用

### frontend-audit — 前端审计
**用途**：审计前端代码（H5 端管理、数据台）。

**检查项**：
- React 组件设计（状态管理、副作用）
- 类型检查（TypeScript）
- 无障碍（a11y）
- 性能（不必要的重渲染）
- 样式一致性（设计系统）
- 测试覆盖

---

### playwright-cli — 浏览器自动化测试
**用途**：编写和运行 Playwright 自动化测试。

**触发**：`/playwright-cli` 或需要编写 e2e 测试

**场景**：
- 标签打印台的交互测试（见 `web/e2e-labels/`）
- H5 表单提交流程
- WeChat 扫码回调的 H5 着陆页

**典型用法**：
```bash
# 启动浏览器
npx playwright codegen http://localhost:3100

# 运行测试
npx playwright test web/e2e/landing.spec.ts
```

---

### cleanup-followthrough — 修复后的清理审计
**用途**：修复/重构后的收尾清理审计（死分支、重复 helper、残留 fallback）。

**触发**：修完 bug/功能后，想确保没有留下垃圾代码

**检查项**：
- 临时变量 / 调试代码
- 注释掉的代码块
- 重复的 helper 函数
- 已删除但仍导入的模块
- 过时的 fallback 逻辑

---

### post-change-audit — 大改动后的收口审计
**用途**：大改动（重构、迁移）后的收口审计。

**触发**：完成一个较大范围的改动后

**检查项**：
- 是否所有调用路径都更新了
- 是否有遗漏的 test case
- 文档/注释是否过期
- 性能回归
- 兼容性问题

---

### fix-and-unify — 修完一处后统一收敛
**用途**：修完一个 bug/问题后，搜索全仓相同模式，统一修复。

**场景**：
- 修了某个列表的排序 bug，发现另外 3 个地方有相同问题
- 修了一个 SQL 注入点，想找出全仓其他脆弱点
- 改了一个 API 错误码的含义，需要找出所有依赖方

**流程**：
1. 修完第一处
2. 搜索相同模式
3. 批量应用同样的修复
4. 统一测试

---

### code-placement — 代码放置规范
**用途**：判断新代码该放哪、谁是 owner。

**场景**：
- 新功能模块，不知道是后端 router 还是 service
- 一个功能涉及多个层，数据流该怎么设计
- 职责划分不清

**factory-os 架构**（见 `CLAUDE.md`）：
- **后端 flat**：`backend/*.py`（没有 `app/` 包），router 模块 + `xxx_repo.py` 仓储成对，在 `main.py` 里 `include_router`
- **前端 flat**：`web/src/*.tsx`（没有 `pages/`）
- **数据库**：`backend/schema/`，迁移用 `alembic`

---

### negative-code-audit — 删代码审计
**用途**：在保持行为的前提下缩减代码与分支。

**场景**：
- 功能做完了，想精简一下实现
- 某段代码太长，想删除不必要的部分
- 死代码、冗余条件

---

### implementation-path-audit — 实现路径审计
**用途**：检查是否有多条实现路径、错误的 owner、逻辑分散。

**场景**：
- 同一个功能在两个地方有不同实现
- 某个业务逻辑跨越多个模块，难以维护
- API 与 service 的职责不清

---

## ⭐ 补充

### feishu-read — 读飞书文档
**用途**：一次性读取单篇飞书文档（docx → markdown），轻量临时查阅。

**触发**：`/feishu-read [文档 URL]` 或贴飞书文档链接

**场景**：
- 客户在飞书上发了需求文档，需要快速读取
- 设计稿、规格说明书在飞书，需要参考
- 临时查阅，不需要完整的自动同步

**输出**：标准 markdown，可直接复制到 Claude 对话

**优势 vs feishu-sync**：
- 轻量：一条命令，不需要配置 repo
- 快速：只读一个文档
- 临时：适合一次性查阅

---

### concept-diagram — 架构图、流程图
**用途**：画概念图、流程图、架构图的标准与流程。

**触发**：需要画一个系统设计图

**输出**：
- Mermaid / SVG / HTML
- 导出 PNG / PDF
- 设计规范（色彩、连线、标注）

**factory-os 应用**：
- 多会话部署流程图
- 权限模型架构图
- 订单流转状态机
- 库存流向图

---

### daily-recap — 日报生成
**用途**：基于 Claude 会话 + git 提交的日报。

**触发**：`/daily-recap` 或工作日结束时

**用途**：
- 自动收集今天的代码改动
- 总结 AI 对话中的关键决策
- 生成可分享的工作日志
- 便于老板/团队跟踪进度

---

### feishu-sync — 飞书 → repo 镜像同步
**用途**：飞书云盘文件夹与 repo 的 markdown 单向镜像自动同步。

**触发**：设置一个新客户的资料库

**场景**：
- 新客户加入，飞书里有工艺规范、样品图片、客户档案
- 想让 Claude 能读到最新的客户资料，而不用每次都手动复制
- 自动同步，不用维护两份

**设置**（一次性）：
```bash
/feishu-sync --setup

# 指定飞书文件夹 URL 和 repo 目标目录
```

之后会自动每 30 分钟同步一次（Github Actions）。

---

### feishu-task-delivery — 飞书任务交付
**用途**：飞书任务行交付（多会话协作，factory-os 是多会话项目）。

**场景**：
- 完成一个子任务，标记为已完成
- 更新任务状态，同步给其他会话
- 任务之间有依赖关系

---

### feishu-todo-enrichment — 飞书待办补全
**用途**：飞书待办事项分类补全。

**场景**：
- 待办混乱，需要按优先级/类型分类
- 自动检查漏掉的字段
- 同步到任务管理

---

## 使用建议

### 开发流程

```mermaid
graph LR
    A["新需求"] -->|/triage| B["任务分解"]
    B -->|开始编码| C["实现功能"]
    C -->|遇到 bug| D["/bug-fix"]
    D --> E["修复并测试"]
    C -->|写 API| F["/api-audit"]
    C -->|权限/数据| G["/security-audit"]
    C -->|异常处理| H["/error-handling-audit"]
    E --> I["代码审查"]
    I -->|"/cleanup-followthrough| J["清理垃圾代码"]
    J -->|"/post-change-audit| K["大改动收口"]
    K -->|"/fix-and-unify| L["全仓相同模式修复"]
    L --> M["部署"]
```

### 多会话协作

factory-os 是多会话项目，用以下 skills 保持同步：

1. **任务分配**：`/triage` → `/feishu-task-delivery` 记录进度
2. **文档查阅**：`/feishu-read` 快速查看飞书需求
3. **日报同步**：`/daily-recap` 向队友汇报一天的改动

---

## 常见组合

### 新功能完整流程

```bash
/triage                      # 分解任务
# 编码...
/api-audit                   # 审计新 API
/security-audit              # 检查权限/敏感数据
/error-handling-audit        # 检查异常处理
# 测试...
/playwright-cli              # e2e 测试（需要）
/cleanup-followthrough       # 清理代码
/post-change-audit           # 大改动收口
/fix-and-unify               # 搜索相同模式
# 部署前
/feishu-task-delivery        # 标记任务完成
/daily-recap                 # 生成日报
```

### Bug 修复完整流程

```bash
/bug-fix                     # 复现、定位、修复
/fix-and-unify               # 找全仓相同问题
/error-handling-audit        # 检查异常处理
/cleanup-followthrough       # 清理测试代码
/feishu-task-delivery        # 标记 bug 修复
```

### 代码审查

```bash
/api-audit                   # API 设计
/security-audit              # 安全
/error-handling-audit        # 错误处理
/frontend-audit              # 前端（需要）
/implementation-path-audit   # 实现路径
/negative-code-audit         # 删代码审计
```

---

## 查看完整 Skill 说明

每个 skill 在 `~/team-skills/<name>/SKILL.md` 有详细说明。symlink 后也在本仓库对应目录下。

```bash
cat ~/factory-os-skills/bug-fix/SKILL.md
```

---

最后更新：2026-10-27
