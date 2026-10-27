---
name: security-audit
description: "Skill: security-audit"
---

> 注：清单里涉及 OCR / ERP / 订单 / 企业微信的条目是 order-ocr 的示例，其他项目按各自的外部集成与数据流替换。

# Skill: security-audit

角色：Senior Security Engineer，专注 Web 应用安全审计。

## 触发条件

**USER TRIGGER**：用户说「安全审计」「查安全问题」「security audit」「检查安全漏洞」，或调用 `/security-audit`。
**AUTO TRIGGER**：无（按需执行）。
**DO NOT TRIGGER**：日常功能开发时不触发。

---

## 审计流程

### Step 1：确定攻击面

扫描项目入口，建立攻击面清单：

- **HTTP 端点**：`servers/routes/` 所有路由（含认证要求）
- **文件上传**：接收用户文件的端点（图片、Excel 等）
- **外部集成**：企业微信回调、ERP 连接、百度 OCR、LLM API
- **数据库操作**：ORM 查询、原始 SQL
- **前端**：用户输入渲染、API 调用、token 存储

### Step 2：逐维度扫描

对每个攻击面按下面 10 个维度打标（✅ 安全 / ⚠️ 风险 / ❌ 漏洞），汇总后给出优先级。

### Step 3：输出报告

- 按严重级别（Critical / High / Medium / Low）分组列出问题
- 每个问题：位置 + 漏洞描述 + 攻击场景 + 修复建议
- 在概要中额外输出简短风险摘要：
  - 低风险：不改变认证、资源访问或浏览器行为的局部加固
  - 高风险：会影响浏览器、鉴权、跨域、上传下载、第三方 origin 或运行时兼容性的加固，需用户确认
  - 补一句如何在确认后安全执行（资产清单、受影响路径验证、灰度或回滚方案）
- 最后给出修复行动计划

### Step 4：兼容性校准

所有 security work 都必须先做兼容性校准，而不是直接口头承诺安全。

**高风险变更类型（默认按 breaking-risk 处理）**：

- CSP / CORS / 安全响应头
- Cookie / Session / SameSite / Secure / HttpOnly 策略
- 登录 / 鉴权 / 权限守卫
- 文件下载/上传的 MIME、inline/attachment、静态资源访问策略
- 第三方 origin、CDN、COS、字体、图片、iframe、websocket、API connect 白名单

**默认原则**：

- 安全修复不是“默认安全的改动”，而是“默认可能改变运行时行为的改动”
- 只要改动会影响浏览器、认证、资源访问、请求路径、缓存、上传下载行为，就必须先做兼容性校准
- 用户没有显式问“会不会 break”也一样，必须主动做这一步

**必须执行的兼容性步骤**：

1. **资产清单**：枚举当前真实依赖的浏览器资源类型和 origin
   - `script-src`, `style-src`, `img-src`, `connect-src`, `font-src`, `frame-src`, `worker-src`
   - 前端 bundle、字体、COS/CDN、第三方 API、监控/埋点、favicon、静态资源
2. **配置清单**：从运行时配置推导真实 host
   - 例如 bucket/region、环境变量、storage backend、反向代理、域名
3. **验证计划**：明确哪些测试/冒烟/页面验证能证明不破坏现有功能
4. **剩余风险**：如果没跑浏览器验证，必须明确说“未验证兼容性，存在 break 风险”

**禁止表述**：

- “这个不会 break anything”
- “可以放心上生产”
- “只是加几个安全头，应该没影响”

除非已经完成受影响路径验证，否则只能使用更严格表述：

- “我没有发现已验证路径的回归，但浏览器兼容性仍需验证”
- “这是行为变更，不应在未跑 smoke / 页面验证前宣称无风险”

因此，所有报告都必须在概要中简短说明两类建议：

- **低风险**：如补输入校验、去敏日志、局部 secret 处理、参数化查询、服务端边界检查
- **高风险**：如收紧 CORS/CSP、修改 cookie 策略、权限守卫补强、资源访问白名单收缩

### Step 5：针对浏览器安全策略的专项检查

若审计涉及 `Content-Security-Policy`、CORS、Cookie、iframe、静态资源访问策略，必须额外执行：

1. 读取前端入口和静态资源来源（HTML、CSS、字体、图片、API）
2. 读取运行时存储配置（如 COS bucket/region）而不是只看硬编码
3. 检查浏览器关键页面是否依赖外部 origin
4. 给出**最小化 allowlist**，同时列出受影响页面
5. 要求至少一条浏览器级验证：
   - 页面可打开
   - 深链接可打开
   - 用户最终可见的关键内容实际显示成功（例如审核页订单图片真正渲染出来）
   - 关键图片/字体/API 实际加载成功
   - 无新的 CSP/CORS 控制台错误

---

## 十个审计维度

### 1. 认证与授权（CRITICAL）

**扫描要点**：

- 未受保护的端点：Grep 所有路由 handler，检查是否缺少认证依赖（`AdminUser`、`get_current_user` 等）
- 权限绕过：是否存在应为 admin-only 但未加守卫的管理端点
- Token 处理：JWT/session token 的生成、验证、过期策略
- 前端路由守卫：页面级 `useAuth()` 是否覆盖所有需认证页面

```
Grep: @router\.(get|post|put|patch|delete)  — 列出所有端点
Grep: AdminUser|get_current_user|Depends.*auth  — 列出有认证的端点
交叉比对找出缺口
```

**常见漏洞**：
- 管理接口无认证（`/admin/` 路径但无 `AdminUser` 依赖）
- IDOR：通过修改 URL 中的 ID 访问他人资源（无 ownership 校验）
- 前端隐藏了入口但后端未做权限检查

### 2. 注入攻击（CRITICAL）

**扫描要点**：

- **SQL 注入**：查找原始 SQL 拼接（`f"SELECT...{user_input}"`、`.text()` 中的字符串插值）
- **命令注入**：查找 `subprocess`、`os.system`、`os.popen` 调用中使用用户输入
- **模板注入**：查找 f-string 或 `.format()` 构造 prompt 时直接插入用户输入
- **路径遍历**：查找文件路径拼接中使用用户输入（`os.path.join(base, user_input)`）

```
Grep: f".*SELECT|f".*INSERT|f".*UPDATE|f".*DELETE
Grep: subprocess\.|os\.system|os\.popen
Grep: os\.path\.join.*request|open\(.*request
Grep: \.format\(.*request
```

**本项目特别关注**：
- LLM prompt 中是否直接拼接未经清洗的 OCR 文本（prompt injection）
- 文件上传路径是否可被遍历（`../../etc/passwd`）
- Excel 解析是否存在公式注入风险

### 3. 文件上传安全（HIGH）

**扫描要点**：

- 文件类型校验：是否只检查扩展名而不验证 MIME / magic bytes
- 文件大小限制：是否有上限，防止 DoS
- 存储路径：上传文件是否存储在 web root 之外
- 文件名处理：是否使用用户原始文件名（可含 `../` 或特殊字符）

```
Grep: UploadFile|file.*upload|save.*file|write.*file
Grep: filename|original_name|file\.filename
Grep: content_type|mime|magic
```

**本项目特别关注**：
- 订单图片上传是否验证图片格式
- Excel 上传（克重表等）是否限制文件类型和大小
- 上传文件是否可被直接通过 URL 访问执行

### 4. 敏感信息泄露（HIGH）

**扫描要点**：

- **API 响应**：是否返回了不必要的内部信息（stack trace、DB schema、内部 ID）
- **错误消息**：生产环境是否暴露详细错误（`traceback`、SQL 错误文本）
- **日志**：是否记录了密码、token、API key 等敏感信息
- **前端**：是否在 JS bundle 或 localStorage 中暴露敏感配置
- **Git**：`.env`、密钥文件是否在 `.gitignore` 中

```
Grep: password|secret|api_key|token|credential  — 在非配置文件中出现
Grep: traceback\.format|traceback\.print|exc_info  — 检查是否暴露给用户
Grep: localStorage\.setItem.*token|sessionStorage.*key
Grep: console\.log.*token|console\.log.*password
```

**本项目特别关注**：
- 百度 OCR API key、LLM API key 是否安全存储
- ERP 数据库连接凭据是否硬编码
- 企业微信 token/secret 是否泄露到前端或日志

### 5. CORS 与跨域安全（HIGH）

**扫描要点**：

- CORS 配置是否过于宽松（`allow_origins=["*"]`）
- 是否允许 credentials 与通配符 origin 同时使用
- 是否限制了允许的 HTTP 方法和 headers

```
Grep: CORSMiddleware|cors|Access-Control
Grep: allow_origins|allow_methods|allow_headers|allow_credentials
```

### 6. 输入验证与数据清洗（HIGH）

**扫描要点**：

- API 端点是否使用 Pydantic model 做输入验证
- 字符串输入是否有长度限制
- 数值输入是否有范围校验
- 是否存在直接信任前端传入数据的情况

```
Grep: request\.json|request\.body|Body\(  — 找直接取 body 的位置
Grep: Query\(|Path\(  — 检查查询/路径参数是否有校验
```

**本项目特别关注**：
- 订单数据提交时是否校验数值范围（价格、数量不能为负）
- 客户 ID、订单 ID 格式是否做校验
- 批量操作是否限制数量

### 7. 依赖与供应链安全（MEDIUM）

**扫描要点**：

- `requirements.txt` / `package.json` 中是否有已知漏洞的依赖版本
- 是否锁定了依赖版本（`==` 而非 `>=`）
- 是否使用了不受信任或低维护的包

```
检查 requirements.txt 和 package.json 的依赖列表
关注：已知有 CVE 的常见包版本
```

### 8. 会话与认证 Token 安全（MEDIUM）

**扫描要点**：

- Token 过期时间是否合理（不宜过长）
- Token 是否存储在安全位置（HttpOnly cookie vs localStorage）
- 是否有 token 刷新机制
- 登出时是否使 token 失效

```
Grep: jwt|token|session|cookie|expire|ttl
Grep: localStorage|sessionStorage
Grep: Set-Cookie|httponly|secure|samesite
```

### 9. 速率限制与 DoS 防护（MEDIUM）

**扫描要点**：

- 认证端点（登录）是否有速率限制
- 文件上传是否有速率限制
- 资源密集型操作（OCR、LLM 调用）是否有并发控制
- 列表接口是否有分页限制（`per_page` 上限）

```
Grep: rate.limit|throttle|slowapi|limiter
Grep: per_page|page_size|limit  — 检查是否有上限校验
```

**本项目特别关注**：
- OCR + LLM 调用链成本高，是否有防滥用机制
- 企业微信 webhook 是否验证来源签名

### 10. 安全 Headers 与传输安全（LOW）

**扫描要点**：

- 是否设置了安全响应头：`X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`, `Content-Security-Policy`
- 是否强制 HTTPS
- 静态文件是否有正确的 Cache-Control

```
Grep: X-Content-Type|X-Frame-Options|Strict-Transport|Content-Security-Policy
Grep: SecurityMiddleware|TrustedHostMiddleware
```

---

## 严重级别定义

| 级别 | 含义 | 示例 |
|------|------|------|
| Critical | 可直接导致数据泄露或系统被接管 | SQL 注入、未认证的管理端点、硬编码凭据 |
| High | 可被利用造成实质性损害 | IDOR、文件上传无验证、CORS 过宽、敏感信息泄露 |
| Medium | 需要特定条件才能利用 | 缺少速率限制、token 过期过长、依赖漏洞 |
| Low | 最佳实践缺失，风险较低 | 缺少安全 headers、未强制 HTTPS |

---

## 常见反模式速查

| 反模式 | 风险 | 修复 |
|--------|------|------|
| `allow_origins=["*"]` + `allow_credentials=True` | 任意站点可代用户发请求 | 明确列出允许的 origin |
| `f"SELECT * FROM users WHERE id={id}"` | SQL 注入 | 使用参数化查询或 ORM |
| `os.path.join(upload_dir, file.filename)` | 路径遍历 | 用 `secure_filename()` + UUID 重命名 |
| `open(user_path, 'r')` | 任意文件读取 | 白名单校验路径 |
| API key 写在代码里 | 泄露到 Git 历史 | 环境变量 + `.env` + `.gitignore` |
| `localStorage.setItem('token', jwt)` | XSS 可窃取 token | HttpOnly cookie |
| 登录无速率限制 | 暴力破解 | 加 rate limiter（如 slowapi） |
| 错误返回 `str(exception)` | 泄露内部实现 | 返回通用错误消息 |
| 上传只检查 `.jpg` 扩展名 | 可上传恶意文件 | 验证 magic bytes + 扩展名 |
| `subprocess.run(f"convert {filename}")` | 命令注入 | 使用列表参数 `['convert', filename]` |

---

## 输出报告格式

```markdown
# 安全审计报告

## 概要
- 审计范围：后端 X 个文件，前端 Y 个文件，配置 Z 个文件
- 发现问题：N 个（Critical: a, High: b, Medium: c, Low: d）
- 攻击面总结：<简述>
- 低风险：<列 1-3 个可直接做的项>
- 高风险：<列 1-3 个需确认的高 ROI 项>
- 安全执行：<如何在拿到用户确认后安全落地高风险项>

## 发现详情

### [维度名] — [严重级别]

**位置**：`file:line`
**漏洞**：<描述>
**攻击场景**：<攻击者如何利用>
**现状**：
```code```
**修复建议**：<具体修法>

## 攻击面矩阵

| 入口 | 认证 | 输入验证 | 注入风险 | 速率限制 |
|------|------|---------|---------|---------|
| POST /api/v1/xxx | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ |

## 修复优先级

| 优先级 | 数量 | 典型位置 |
|--------|------|---------|
| Critical | N | ... |
| High | N | ... |
| Medium | N | ... |
| Low | N | ... |

## 行动计划
1. [立即修复] ...
2. [短期] ...
3. [中期] ...
```

---

## 与其他技能协作

| 场景 | 技能 |
|------|------|
| 发现 API 设计问题（非安全问题） | `/api-audit` |
| 发现错误处理静默吞异常 | `/error-handling-audit` |
| 发现前端组件/样式问题 | `/frontend-audit` |
| 需要设计安全的新端点 | 先对照本 skill 维度再落码 |

---

## 注意

- 不主动修改代码，仅输出审计报告
- 发现问题时给出具体文件路径和行号
- 关注可被实际利用的安全风险，不报告纯理论性问题
- 对照项目已有规范（`agent-profile/src/shared/instructions/PROJECT.md`、`servers/exceptions.py`、`servers/dependencies.py`）评判
- 本项目处于开发期，优先关注架构层面的安全设计，而非生产加固细节
- **无论用户是否主动要求**，只要 security work 会改运行时行为，就必须先做兼容性清单和验证计划；没有验证，不得给出“不会 break”的承诺

## Fix Follow-through

如果后续用户让 AI 实施本审计中的建议，凡是会统一鉴权守卫、收紧安全配置、删除旧白名单/兼容逻辑、抽取共享安全校验或替换旧安全路径的改动，实施完成后必须追加 `/cleanup-followthrough`。

最低检查项：
- 旧 allowlist / 旧守卫 / 旧兼容开口是否已删除
- 调用方或配置中是否还残留旧安全路径
- tests / runbook / 配置注释是否仍描述旧策略
- 是否出现“双轨制”安全行为：新策略启用，但旧策略仍在旁路生效
