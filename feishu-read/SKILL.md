---
name: feishu-read
description: 一次性读取单篇飞书文档（docx）并输出为 markdown，供 Claude 直接读内容。USER TRIGGER: 读这篇飞书文档、帮我看看这个飞书文档、feishu read、读取飞书文档、用户贴出飞书文档 URL 并问内容/说了什么/帮我读一下。DO NOT TRIGGER: 批量同步整个文件夹（用 feishu-sync）、写飞书文档（用 feishu-meeting-note）、读取多维表格/审批等非 docx 文档。
---

# feishu-read：单篇飞书文档读取

给一个飞书文档 URL 或 token，直接把文档内容（docx → markdown）输出来，供 Claude 读取和引用。轻量、一次性、不落库。

## 前置条件

- **凭证**：`~/.config/feishu/secrets.env` 里配置了 `FEISHU_ALERT_APP_ID` 和 `FEISHU_ALERT_APP_SECRET`（告警机器人），或同名环境变量。
- **权限**：要读的文档已共享给「告警机器人」（可查看即可）。未共享会报权限错误。
- **支持类型**：飞书文档（docx）。表格、多维表格、幻灯片、审批单等暂不支持。

## 用法

```bash
# 输出到 stdout（默认）
python3 ~/.claude/skills/feishu-read/scripts/feishu_read.py <飞书文档URL>

# 写入文件
python3 ~/.claude/skills/feishu-read/scripts/feishu_read.py <URL> -o doc.md

# 不下载图片（只留占位符，更快）
python3 ~/.claude/skills/feishu-read/scripts/feishu_read.py <URL> --no-images

# 自定义图片下载目录
python3 ~/.claude/skills/feishu-read/scripts/feishu_read.py <URL> --assets-dir ./images
```

**输入格式**：支持完整的飞书文档 URL（`https://.../docx/XXXXX`）或纯 token。

## 输出格式

带 frontmatter 的 markdown：

```markdown
---
feishu_token: XXXXX
feishu_url: https://bytedance.larkoffice.com/docx/XXXXX
feishu_title: "文档标题"
feishu_modified: 1700000000
---

# 文档标题

正文内容...
```

图片默认下载到 `./_assets/<token>/` 目录，markdown 中用相对路径引用。

## 与 feishu-sync 的区别

| | feishu-read | feishu-sync |
|---|---|---|
| 场景 | 临时读一篇文档 | 客户资料批量镜像，长期同步 |
| 范围 | 单篇 docx | 整个文件夹，多种格式 |
| 输出 | stdout 或单文件 | 整个目录结构 + git 提交 |
| 前置 | 文档共享给机器人 | 文件夹共享 + 建私有 repo + Actions |
| 持续性 | 一次性 | 每 30 分钟自动同步 |

什么时候用哪个：
- 「帮我看看这篇文档说了什么」→ feishu-read
- 「这个客户的所有资料我要长期能搜到」→ feishu-sync
