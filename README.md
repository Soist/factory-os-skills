# factory-os Skills

factory-os 专用 skills 集合（Claude Code & Codex）。19 个完整 skills，包含代码审计、飞书集成、前端测试、文档交付等开发工具。

## 安装

```bash
cd ~/factory-os-skills
./install.sh
```

脚本会为 factory-os 项目配置专属 skills 目录，并在 `~/.claude/settings.json` 中添加 `skillsDir` 指向。

新开 Claude Code 会话即可使用。

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

factory-os 仓库的 `.claude/settings.json` 配置自动加载这些 skills（Claude Code CLI & Desktop）：

```json
{
  "skillsDir": ["~/.claude/skills/", "~/factory-os-skills/"]
}
```

（运行 install.sh 会自动设置）

## 使用示例

### Claude Code（CLI / Desktop）

在对话中输入 `/` 然后选择 skill：

```bash
/bug-fix              # 新 bug 修复，流程化处理
/api-audit            # API 设计审计
/security-audit       # 安全审查
/feishu-read [URL]    # 读飞书文档（轻量查阅）
/triage               # 编码任务入口
```

### Codex（VS Code / IDE）

在 Claude 对话侧边栏中调用 skills（同样支持 `/` 命令）。

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
