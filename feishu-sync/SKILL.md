---
name: feishu-sync
description: 把飞书云盘文件夹单向镜像成 repo 里的 markdown（docx→md、pptx/xlsx/pdf→md、图片落 _assets），飞书删了 repo 同步删，可定时自动跑。USER TRIGGER: 新客户接入、'同步飞书资料到 repo'、'feishu sync'、'把客户飞书文件夹拉下来'、配置/排查定时同步。DO NOT TRIGGER: 往飞书写文档（那是 feishu-meeting-note）、只读单个飞书文档一次性查看。
---

# feishu-sync：飞书文件夹 → repo 的 markdown 镜像

目的：客户资料在飞书里协作（会议纪要、方案、PPT），coding agent 在 repo 里工作。**单向镜像，不提炼**——agent 直接读原文，没有需要人审核的 AI 产物。

脚本纯 stdlib（Python ≥3.11，用 `tomllib`），凭证同 `feishu-meeting-note`：`~/.config/feishu/secrets.env`。**目标文件夹必须先共享给告警机器人。**

## 新客户接入（一条命令）

前置（飞书里手动，每个客户一次）：把客户的飞书文件夹共享给「告警机器人」（可查看即可）。

```bash
python3 ~/.claude/skills/feishu-sync/scripts/onboard.py <飞书文件夹URL> --name <客户slug>
```

（Codex 对应 `~/.codex/skills/feishu-sync/…`；slug 用小写字母数字连字符，如 `mingpeng`，同时是 repo 名。）它会：校验机器人能读该文件夹 → 确保 team-skills 的只读 deploy key → 建私有 repo `<owner>/<slug>` 并 clone 到 `~/Documents/customers/<slug>` → 写 `feishu-sync.toml`、GitHub Actions workflow、CLAUDE.md → 本地首次同步并 push（走 SSH）→ 写 3 个 Actions secret → 触发一次 workflow 并等结果。

之后每 30 分钟 GitHub Actions 自动同步（飞书改动到 repo 平均延迟约 15 分钟、最长 30 分钟加排队；要立刻同步用 `gh workflow run feishu-sync.yml -R <owner>/<slug>`）。同事只 `git pull`。

- 每个客户的配置都在其 repo 里（`feishu-sync.toml` + `.github/workflows/feishu-sync.yml`），不在 GitHub 设置页；改同步频率改 workflow 里的 cron（最小 5 分钟）。
- 同步失败（部分文档转换失败）时 workflow 标红，GitHub 会给仓库所有者发邮件；成功的部分照常提交。
- Actions 的私有仓库分钟数有免费额度，客户多了注意用量。

## 格式统一规则

| 飞书里 | repo 里 |
|---|---|
| docx | `.md`（标题/列表/待办/表格/引用/高亮块/链接）；图片下载到 `_assets/<token>/` |
| .md .txt .csv .json .html 图片 | 原样 |
| .pptx | `.md`，每页一节：文字 + 备注 + 页内 ≥30KB 的图 |
| .xlsx | `.md`，每个 sheet 一张表 |
| .pdf | `.md`（`pdftotext -layout`，版式复杂的会乱）；机器没装 pdftotext 则保留 pdf |
| 飞书原生 slides | `.md`，每页一节，页面图片下载到 `_assets/`（整页是图的幻灯片没有可检索文字，agent 需看图） |
| 飞书原生 sheet / bitable | `.md`，每个工作表/数据表一张表（**未用真实文件验证**，失败会在日志里报错，不会静默） |
| mindnote 等其余类型 | 只告警跳过 |

每个 md 带 frontmatter：`feishu_token / feishu_url / feishu_modified`，可回溯来源。

## 行为与安全

- **镜像删除**：飞书里没了，本地也删（git 历史可找回）。飞书列表为空但本地有文件时**拒绝清空**（多半是权限/共享丢了），确认无误才加 `--allow-empty`。
- 列表接口任何一页失败都整体中止，不会拿残缺列表去删。
- 单个文档转换失败：保留旧版本，继续其它，退出码非 0。
- 幂等：靠 `modified_time` 跳过未变的；状态在 `<out>/.feishu-sync.json`。
- 客户数据进 repo：**repo 必须私有**，访问范围与飞书权限保持一致。图片和 pptx 配图会让 repo 变大。

## 已知限制

- docx 里的画板/思维导图/内嵌表格（sheet 块）输出为占位注释，不转换。
- pptx 里的图表、SmartArt 只取文字；设计稿型 PPT 文字很碎，价值有限。
- 无说话人分离等问题属于上游纪要质量，与本工具无关。
