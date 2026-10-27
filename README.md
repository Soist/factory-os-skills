# factory-os Skills

factory-os 专用 skills 集合（Claude Code & Codex）。包含代码审计、飞书集成、前端测试、文档交付等开发工具。

## 安装

```bash
cd ~/factory-os-skills
./install.sh
```

脚本会 symlink 所有 skills 到 `~/.claude/skills/` 和 `~/.codex/skills/`，并为 factory-os 项目配置专属 skills。

安装后新开会话。

## Skills 按优先级分类

### ⭐⭐⭐ 核心（必用）

| Skill | 说明 |
|---|---|
| `triage` | 编码任务入口：分类、定范围、评估风险、TDD 计划、路由 |
| `bug-fix` | 先复现再修的 bug 修复流程 |
| `api-audit` | 后端 REST API 审计 |
| `security-audit` | Web 安全审计（WeChat、权限系统） |
| `error-handling-audit` | 错误处理审计 |

### ⭐⭐ 常用

| Skill | 说明 |
|---|---|
| `frontend-audit` | 前端审计（H5 端管理、数据台） |
| `playwright-cli` | 浏览器自动化测试 |
| `cleanup-followthrough` | 修复后的清理审计 |
| `post-change-audit` | 大改动后的收口审计 |
| `fix-and-unify` | 修完一处后统一收敛同类问题 |
| `code-placement` | 代码放置规范 |
| `negative-code-audit` | 删代码审计 |
| `implementation-path-audit` | 实现路径审计 |

### ⭐ 补充

| Skill | 说明 |
|---|---|
| `concept-diagram` | 架构图、流程图 |
| `daily-recap` | 日报生成 |
| `feishu-read` | 读飞书文档 |
| `feishu-sync` | 飞书 → repo 镜像同步 |
| `feishu-task-delivery` | 飞书任务交付 |
| `feishu-todo-enrichment` | 飞书待办补全 |

## 配置

factory-os 仓库的 `.claude/settings.json` 已配置自动加载这些 skills（Claude Code CLI & Desktop）：

```json
{
  "skillsDir": ["~/.claude/skills/", "~/factory-os-skills/"]
}
```

对于 Codex（VS Code 等 IDE），symlink 会自动同步到 `~/.codex/skills/`。

（新装的话 install.sh 会自动设置）

## 使用示例

```bash
# 新 bug 修复，流程化处理
/bug-fix

# API 设计审计
/api-audit

# 安全审查
/security-audit

# 读飞书文档（轻量查阅）
/feishu-read [文档 URL]

# 编码任务入口
/triage
```

## 常见问题

### 某个 skill 需要飞书凭证

如果使用 `feishu-*` skills，需要配置飞书凭证：

```bash
mkdir -p ~/.config/feishu && chmod 700 ~/.config/feishu
cat > ~/.config/feishu/secrets.env << EOF
FEISHU_ALERT_APP_ID=...
FEISHU_ALERT_APP_SECRET=...
EOF
chmod 600 ~/.config/feishu/secrets.env
```

### 如何更新

```bash
cd ~/factory-os-skills
git pull origin main
./install.sh
```

---

Created for factory-os project. 2026-10-27
