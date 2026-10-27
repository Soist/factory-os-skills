---
name: daily-recap
description: "Create an end-of-day or point-in-time recap for this project using local Codex sessions, local Claude Code sessions, today's git commits, and the current worktree. USER TRIGGER: 'daily recap', 'what did I do today', 'handoff note', 'today summary', 'EOD summary'. AUTO TRIGGER: do not auto-trigger."
---

# Daily Recap

产出一份高信号、默认中文的日报 recap，概括用户今天在这个 repo 里实际完成了什么。

这个 skill 适用于个人复盘、团队异步交接、以及管理视角总结。它不是 transcript dump，也不是 commit log 改写。

## 语言要求

- 最终输出必须是 **全中文**。
- 不要出现中英混杂的判断句、建议句、标题或模板句。
- 技术名词只有在中文明显更别扭时才保留英文，例如 `Batch Chat`、`Playwright`、`pre-commit`。
- 即使底层证据来自英文 commits / sessions / Notion 原文，写 recap 时也必须翻译成自然中文，只保留必要的英文专有名词。
- 特别注意 `还需要提升的地方` 这一段，最容易退化成英文模板句，输出前必须人工检查一遍。

## 原则

- 先讲结果，再讲过程，不按时间线流水账展开。
- 明确区分“今天已经完成的事”和“还没收口的事”。
- 提炼主题、判断、取舍，不要粘贴原始聊天记录。
- 每个结论都要有证据支撑，但证据应被吸收进叙事，而不是单独变成噪音区块。
- 有不确定性就明确说，不要假装已经完成。

## 固定输出结构

最终输出只保留这 5 段：

```markdown
## 你今天完成了什么
## 仍然未完成的事
## 今天做得好的地方
## 还需要提升的地方
## 来源快照
```

不要再额外加：
- Executive summary
- Evidence trail
- Risks / follow-ups
- Suggested next moves
- Session evidence
- Notes lens

这些内容如果有价值，就吸收到上面 5 段里，而不是单独成节。

## 不要输出什么

- tool chatter、命令输出、中间 commentary
- 只是微调说法的重复 prompts
- 文件级流水账，除非它真能说明一个重要工作流
- “做了 X/Y/Z”但没有结果、影响、判断的低价值 bullet
- 长 transcript 摘录，除非用户明确要看 provenance

## Workflow

### 1. Generate the evidence-backed draft

Run:

```bash
python3 ~/.claude/skills/daily-recap/scripts/generate_daily_recap.py --date YYYY-MM-DD
```

默认输出：

```text
docs/daily-recaps/YYYY-MM-DD.md
```

脚本输入来源：
- `git log` for committed work
- `git status` for active WIP
- `~/.codex/sessions/YYYY/MM/DD/*.jsonl` filtered to the current repo
- `~/.claude/projects/<repo>.jsonl` filtered to the current repo and date
- optional distilled notes from an external source such as Notion via `--notes-file`

### 外部笔记，包括 Notion

如果用户把每日笔记记在 Notion 里，先用 Notion MCP 抓取当天内容，只提炼高信号 bullet，存到本地被 git ignore 的 recap 输入文件里，再传给生成器：

```bash
python3 ~/.claude/skills/daily-recap/scripts/generate_daily_recap.py --date YYYY-MM-DD --notes-file docs/daily-recaps/.inputs/YYYY-MM-DD-notes.txt
```

提炼规则：
- keep only outcomes, decisions, measurements, and explicit open questions
- do not dump the whole Notion page into the file
- prefer 5-10 short bullets max
- if Notion conflicts with git/session evidence, surface the conflict rather than hiding it

### 2. 复读并收紧生成结果

不要盲信脚本输出。生成后必须再读一遍并收紧：
- 合并重复 workstreams
- 把技术动作改写成“完成了什么”
- 删除弱 bullet
- 把 open items 写成真正的未决问题，而不是剩余文件列表
- 把“做得好”和“需要提升”写成有判断力的管理者视角

### 3. 输出标准

#### `你今天完成了什么`

- 这是主叙事。
- 顶层来源以 `Notion 笔记 + commits` 为准。
- 先从 Notion 里的结果/判断/测量值出发，再用 commits 补足落地细节。
- 如果 commits 里有 Notion 没写但明显重要的工作，也要补进来。
- coding sessions 只用于补强叙事，让人看得出这件事是否经历了：
  - 多轮澄清
  - 脏调试
  - 高风险验证
  - 关键取舍

写法要求：
- 不要写“改了哪些文件”
- 要写“你把什么能力、流程、质量门槛提升到了什么程度”

#### `今天做得好的地方`

- 这里不是夸奖，要写高质量判断。
- 只写真正体现能力的点，例如：
  - 把分析转成实现
  - 把风险控制前置
  - 提高了团队杠杆
  - 用了实证而不是主观判断

#### `还需要提升的地方`

这是最容易写空的一段，必须满足下面要求：

- 每条都要有 **具体证据**
- 每条都要有 **可执行改进动作**
- 优先给 **自动化改进建议**
- 自动化不合适时，再给流程/软技能建议

写法模板：

```markdown
- 问题判断。证据：……。改进动作：……。
```

优先级：
- 第一优先：pre-commit / pre-push guard、linter、script、checklist、Playwright/E2E、可复用模板
- 第二优先：流程约束
- 第三优先：软技能建议，例如更清晰地打包主题、及时做决策记录、明确 defer/close

禁止：
- “应该更认真一点”
- “下次注意”
- 没有证据的泛泛建议
- 英文整句直接残留在中文 recap 里

#### `来源快照`

- 保持简短，只保留最小必要 provenance：
  - themes
  - commit 数
  - dirty files 数
  - Codex / Claude session 数

## 解释规则

- Notion 笔记和 commits 是顶层叙事的一等来源。
- dirty 但未提交的文件一律视为 WIP，不算已完成。
- coding sessions 不是顶层来源，只用于补强叙事，让人看得出这件事是否经历了反复澄清、脏调试、或高风险验证。
- 如果 session 里有话题但没有对应代码/笔记支撑，默认视为 investigation，不要冒充已完成产出。
- Claude subagent transcript 默认忽略，噪音太高。
- 如果 Notion 和 commit 呈现出的重点不一致，不要二选一；先以 Notion 的 day narrative 为骨架，再把 commit 里确实重要但未写进笔记的内容补进去。

## 质量标准

一份好的 recap，要让同事在 2 分钟内回答清楚：
- 今天真正完成了什么？
- 还有什么没有收口？
- 做得好的地方是什么？
- 还需要提升什么？

如果做不到，就重写，不要输出流水账。

额外标准：
- `还需要提升的地方` 每一条都必须带证据和动作
- 动作优先自动化
- sessions 只能补强 narrative，不能喧宾夺主
- 输出语言必须统一为中文，不能出现“中文外壳 + 英文内容”
