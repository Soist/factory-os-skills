#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


IGNORED_PROMPT_PATTERNS = (
    "<environment_context>",
    "<local-command-caveat>",
    "<command-name>",
    "<image",
    "</image>",
)

THEME_RULES = {
    "deployment safety": ("deploy", "deployment", "migrate", "schema drift", "preflight", "promote guard"),
    "evaluation workflow": ("eval", "journal", "benchmark", "tracking"),
    "prompt quality": ("prompt", "prior", "rule", "factory", "customer yaml"),
    "ocr pipeline": ("ocr", "baidu", "accurate ocr", "extraction"),
    "frontend review flow": ("frontend", "review", "modal", "keyboard", "icon", "table", "usermanagement"),
    "pricing flow": ("pricing", "paper width", "quoted price", "erp"),
    "agent workflow": ("skill", "codex", "claude", "memory", "recap", "instruction"),
    "test reliability": ("test", "pytest", "migration test", "e2e", "smoke"),
}

ACHIEVEMENT_RULES = (
    {
        "id": "eval_framework",
        "keywords": ("eval", "journal", "batch chat", "auto-publish", "published eval", "batch api"),
        "title": "Turned eval into a publishable operating loop",
        "narrative": (
            "Upgraded the evaluation workflow from ad hoc run output into a real operating loop: "
            "runs can be tracked in a journal, published summaries are managed automatically, and "
            "the Qwen eval path was moved onto the cheaper Batch Chat endpoint instead of the older batch file flow."
        ),
    },
    {
        "id": "deploy_safety",
        "keywords": ("deploy", "schema drift", "preflight", "promote guard", "auto-migration", "ref-data sync"),
        "title": "Made deployment materially safer",
        "narrative": (
            "Raised the deployment safety bar by adding preflight auditing, promote guards, schema-drift checks, "
            "automatic migration handling, and reference-data sync, which reduces the chance of shipping broken state."
        ),
    },
    {
        "id": "test_reliability",
        "keywords": ("migration test", "isolated test db", "real assertions", "smoke test", "e2e", "focus"),
        "title": "Improved trust in the test suite",
        "narrative": (
            "Improved test credibility instead of just test count: migration tests now use an isolated database, "
            "tautological checks were replaced with real assertions, and review-flow regressions got stronger UI/E2E coverage."
        ),
    },
    {
        "id": "prompt_quality",
        "keywords": ("prompt", "priors", "prior labels", "accurate ocr", "customer yaml", "pricing_display"),
        "title": "Reduced prompt noise and tightened extraction inputs",
        "narrative": (
            "Reduced low-value information fed into extraction by stripping weak priors, improving prompt formatting, "
            "and tightening OCR/config behavior so model inputs are more intentional and less noisy."
        ),
    },
    {
        "id": "agent_ops",
        "keywords": ("agent memory", "project instructions", "memory", "instruction"),
        "title": "Strengthened the project operating system for AI agents",
        "narrative": (
            "Unified shared memory and project instructions so Codex and Claude operate from a cleaner common source of truth, "
            "which lowers onboarding friction and reduces agent drift."
        ),
    },
)


@dataclass
class SessionNote:
    source: str
    session_id: str
    started_at: str | None
    ended_at: str | None
    prompts: list[str]
    final_message: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a daily recap for this repo.")
    parser.add_argument("--date", default=str(date.today()), help="Target date in YYYY-MM-DD format.")
    parser.add_argument("--repo-root", default=os.getcwd(), help="Repository root. Defaults to cwd.")
    parser.add_argument(
        "--notes-file",
        help="Optional plain-text notes file with distilled daily notes from external sources such as Notion.",
    )
    parser.add_argument(
        "--output",
        help="Output markdown path. Defaults to docs/daily-recaps/<date>.md under repo root.",
    )
    return parser.parse_args()


def localize_text(text: str) -> str:
    replacements = [
        ("Turned eval into a publishable operating loop", "把 eval 升级成可发布、可运营的闭环"),
        ("Made deployment materially safer", "显著提高了部署安全性"),
        ("Improved trust in the test suite", "提高了测试体系的可信度"),
        ("Reduced prompt noise and tightened extraction inputs", "减少了 prompt 噪音并收紧了提取输入"),
        ("Strengthened the project operating system for AI agents", "强化了 AI agent 的项目操作系统"),
        (
            "Upgraded the evaluation workflow from ad hoc run output into a real operating loop: runs can be tracked in a journal, published summaries are managed automatically, and the Qwen eval path was moved onto the cheaper Batch Chat endpoint instead of the older batch file flow.",
            "把评测流程从一次性跑完就结束的 ad hoc 输出，升级成了真正可运营的闭环：运行结果可以自动记录到 journal，发布摘要可以自动管理，而且 Qwen eval 路径也从旧的 batch file flow 切到了更便宜的 Batch Chat endpoint。",
        ),
        (
            "Raised the deployment safety bar by adding preflight auditing, promote guards, schema-drift checks, automatic migration handling, and reference-data sync, which reduces the chance of shipping broken state.",
            "通过增加 preflight 审计、promote guard、schema drift 检查、自动 migration 处理和参考数据同步，把部署安全门槛明显抬高了，降低了把错误状态发出去的概率。",
        ),
        (
            "Improved test credibility instead of just test count: migration tests now use an isolated database, tautological checks were replaced with real assertions, and review-flow regressions got stronger UI/E2E coverage.",
            "不是简单增加测试数量，而是提高了测试本身的可信度：migration tests 改成使用隔离数据库，无效的 tautological checks 被替换成真正有约束力的断言，review flow 的回归也补强了 UI/E2E 覆盖。",
        ),
        (
            "Reduced low-value information fed into extraction by stripping weak priors, improving prompt formatting, and tightening OCR/config behavior so model inputs are more intentional and less noisy.",
            "通过去掉低价值 priors、改进 prompt formatting、收紧 OCR 与配置行为，减少了输入到提取流程里的噪音，让模型拿到的信息更有意图、更少干扰。",
        ),
        (
            "Unified shared memory and project instructions so Codex and Claude operate from a cleaner common source of truth, which lowers onboarding friction and reduces agent drift.",
            "统一了 shared memory 和 project instructions，让 Codex 与 Claude 基于更干净的一套共同事实工作，从而降低 onboarding 摩擦，也减少 agent drift。",
        ),
        (
            "The coding sessions show this was not a straight implementation: it involved cost validation and repeated eval-framework clarification before the cheaper path was trusted.",
            "相关 coding sessions 说明这不是一次直线型实现：中间经历了成本验证和多轮 eval framework 澄清，最后才真正信任并切到更便宜的路径。",
        ),
        (
            "The external notes also confirm the pricing outcome in practice: roughly 100 VLM calls came out to about 3.6 yuan, validating that the cheaper batch path is really being used.",
            "你的 notes 也从实践上确认了价格结果：大约 100 次 VLM 调用成本约 3.6 元，说明更便宜的 batch 路径确实已经生效。",
        ),
        (
            "The supporting session trail shows this was a genuine analysis thread, not a quick cleanup, with back-and-forth over whether priors were helping or hurting extraction.",
            "sessions 里的上下文也说明这不是随手清理，而是一条真实的数据分析线程：中间反复讨论过 priors 到底是在帮忙还是在伤害提取效果。",
        ),
        (
            "The strongest supporting data point in the notes is a 302/308 field-accuracy run after prior/rule formatting changes, which suggests the cleanup was not merely cosmetic.",
            "notes 里最强的支撑数据点是 prior/rule formatting 调整后出现了一次 302/308 的字段准确率，说明这次清理不是表面文章。",
        ),
        (
            "This also showed up in the day notes as better onboarding for new team members, not just internal cleanup.",
            "这件事在你的日记里也体现为新同事 onboarding 体验的提升，而不只是内部清理。",
        ),
        (
            "In other words, today's work improved both release confidence and operator clarity.",
            "换句话说，今天这部分工作同时提升了发布信心和操作清晰度。",
        ),
        (
            "The related sessions also suggest the UI/test work took real verification effort rather than a one-pass fix.",
            "相关 sessions 也能看出，这部分 UI/test 工作并不是一把过，而是经历了真实验证与反复收敛。",
        ),
        (
            "The biggest unresolved product decision is still OCR strategy: the notes show that removing high-accuracy OCR is not yet a clear win, so the flag stays while more benchmarking is done.",
            "当前最大的未决产品判断仍然是 OCR 策略：notes 已经说明，去掉高精度 OCR 还不是一个明确的胜利，所以现在保留开关，继续 benchmark。",
        ),
        (
            "Prompt and model-provider tuning is still open. Factory configs and the Qwen provider are being adjusted, which means extraction behavior may still move tomorrow.",
            "prompt 和 model-provider 调整仍然没有完全收口。工厂配置和 Qwen provider 还在变化，这意味着提取行为明天仍可能继续变化。",
        ),
        (
            "There is also process/tooling work still open around docs and agent-profile assets, so some of today’s operational improvements are not fully closed out yet.",
            "另外 docs 和 agent-profile 这条流程/工具链工作也还没完全收尾，所以今天的一部分操作性改进仍未彻底闭环。",
        ),
        (
            "There is also an unresolved correctness question around missing `crease_lines` in cloud behavior versus local runs, which should be treated as a real investigation thread rather than background noise.",
            "还有一个未解决的正确性问题：cloud 行为里会出现 `crease_lines` 缺失，但本地复现不到，这应该被当成一条真实调查线，而不是背景噪音。",
        ),
        (
            "Several unresolved UX and extraction questions already consumed meaningful investigation time, so they should either be closed decisively or deferred explicitly instead of staying half-open.",
            "有几条 UX 与 extraction 的未决问题已经消耗了不少调查时间，接下来要么明确收口，要么明确延期，而不是继续半开半关。",
        ),
        (
            "Frontend workbench hardening remains open in the worktree, so UI reliability work is still in transition rather than fully closed.",
            "frontend workbench 的加固工作还留在 worktree 里，说明 UI 可靠性这条线仍在过渡中，还没有彻底收口。",
        ),
        (
            "You improved safety on both sides of the delivery loop: release controls got stronger while test credibility also improved.",
            "你同时提高了交付链路两端的安全性：一边是发布控制更强，另一边是测试可信度更高。",
        ),
        (
            "You connected cost awareness to implementation instead of leaving it as analysis; the eval path now reflects the pricing insight.",
            "你把成本意识真正转成了实现决策，而不是停留在分析层面；现在 eval 路径已经体现了这份价格洞察。",
        ),
        (
            "You invested in team leverage, not just feature output, by improving the shared agent operating model.",
            "你投入的是团队杠杆，而不只是功能产出；共享 agent operating model 的改进会持续放大后续效率。",
        ),
        (
            "You focused on system-level improvements with durable payoff rather than only local feature work.",
            "你今天做的不是局部功能修补，而是更有长期回报的系统级改进。",
        ),
        (
            "You did not stop at theory; you checked whether the batch-cost hypothesis held in real runs and used that evidence to drive implementation.",
            "你没有停留在理论判断上，而是用真实运行结果去验证 batch 成本假设，并让实现跟着证据走。",
        ),
        (
            "The day spanned many threads. The next level up is sharper packaging: fewer commits per theme and cleaner separation between infra, eval, prompt, and UI work.",
            "今天跨的线程还是偏多。下一步要拉高的是打包能力：每个主题更少的 commits，以及 infra、eval、prompt、UI 之间更清晰的边界。",
        ),
        (
            "Too much remains open at day end. Push harder toward a clean worktree or at least one clearly isolated unfinished branch of work.",
            "收工时仍然留了太多未关闭内容。下一步要更强地逼近 clean worktree，至少也要把未完成工作隔离成一条明确的支线。",
        ),
        (
            "Frontend hardening is still half-shipped. Close the loop with a deliberate test-and-commit boundary before starting another thread.",
            "frontend 加固仍然处于半出货状态。下一步应该先用明确的 test-and-commit 边界把这一条线收口，再开启新的线程。",
        ),
        (
            "Presentation quality is still trailing backend rigor. If formatting is visibly poor, it should compete for priority with model and infra work because it shapes user trust directly.",
            "呈现质量仍然落后于后端 rigor。如果格式肉眼可见地差，它就应该和 model、infra 工作竞争优先级，因为它会直接影响用户信任。",
        ),
        ("What You Achieved", "你今天完成了什么"),
        ("What Is Still Open", "仍然未完成的事"),
        ("What You Did Well", "今天做得好的地方"),
        ("Need Improvement", "还需要提升的地方"),
        ("Source Snapshot", "来源快照"),
        ("Repo", "仓库"),
        ("Themes consolidated from commits, sessions, and notes", "从 commits、sessions、notes 汇总出的主题"),
        ("Commits", "提交数"),
        ("Dirty files", "未提交文件数"),
        ("Codex sessions", "Codex 会话数"),
        ("Claude sessions", "Claude 会话数"),
        ("Evidence", "证据"),
    ]
    for src, dst in replacements:
        text = text.replace(src, dst)
    return text


def run(cmd: list[str], cwd: Path) -> str:
    completed = subprocess.run(cmd, cwd=cwd, check=True, text=True, capture_output=True)
    return completed.stdout


def parse_day(day_text: str) -> date:
    return datetime.strptime(day_text, "%Y-%m-%d").date()


def same_repo(path_text: str | None, repo_root: Path) -> bool:
    if not path_text:
        return False
    try:
        return Path(path_text).resolve() == repo_root.resolve()
    except FileNotFoundError:
        return Path(path_text) == repo_root


def extract_text(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        texts: list[str] = []
        for item in value:
            if isinstance(item, dict):
                if item.get("type") in {"input_text", "text"} and isinstance(item.get("text"), str):
                    texts.append(item["text"])
                elif item.get("type") == "tool_result" and isinstance(item.get("content"), str):
                    continue
            elif isinstance(item, str):
                texts.append(item)
        return texts
    return []


def clean_prompt(text: str) -> str | None:
    text = text.strip()
    if not text:
        return None
    if any(pattern in text for pattern in IGNORED_PROMPT_PATTERNS):
        return None
    text = re.sub(r"\[Image #\d+\]\s*", "", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = text.strip()
    if not text:
        return None
    if text.startswith("/"):
        return None
    if len(text) > 220:
        text = text[:217].rstrip() + "..."
    return text


def shorten(text: str | None, limit: int = 180) -> str | None:
    if not text:
        return None
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def top_level_area(path_text: str) -> str:
    path = Path(path_text)
    parts = path.parts
    if not parts:
        return "repo"
    if len(parts) == 1:
        return parts[0]
    return parts[0]


def summarize_paths(paths: list[str], limit: int = 4) -> str:
    if not paths:
        return "no files"
    sorted_paths = sorted(paths)
    if len(sorted_paths) <= limit:
        return ", ".join(f"`{path}`" for path in sorted_paths)
    shown = ", ".join(f"`{path}`" for path in sorted_paths[:limit])
    return f"{shown}, +{len(sorted_paths) - limit} more"


def bulletize(text: str) -> str:
    return text[0].upper() + text[1:] if text else text


def read_optional_text(path_text: str | None) -> str:
    if not path_text:
        return ""
    path = Path(path_text)
    if not path.is_file():
        raise FileNotFoundError(f"Notes file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def note_bullets(notes_text: str) -> list[str]:
    bullets: list[str] = []
    for raw_line in notes_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"^[\-\*\d\.\)\s]+", "", line).strip()
        if not line:
            continue
        bullets.append(line)
    return dedupe_keep_order(bullets)


def collect_git_commits(repo_root: Path, target_day: date) -> list[dict[str, Any]]:
    start = f"{target_day.isoformat()} 00:00:00"
    end = f"{target_day.isoformat()} 23:59:59"
    raw = run(
        [
            "git",
            "log",
            "--since",
            start,
            "--until",
            end,
            "--no-merges",
            "--numstat",
            "--date=iso",
            "--pretty=format:__COMMIT__%n%H%x1f%s%x1f%ad",
        ],
        repo_root,
    )
    commits: list[dict[str, Any]] = []
    for block in raw.split("__COMMIT__"):
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        head = lines[0].split("\x1f")
        if len(head) < 3:
            continue
        files: list[str] = []
        insertions = 0
        deletions = 0
        for line in lines[1:]:
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            added, removed, path = parts
            files.append(path)
            if added.isdigit():
                insertions += int(added)
            if removed.isdigit():
                deletions += int(removed)
        commits.append(
            {
                "sha": head[0],
                "subject": head[1],
                "date": head[2],
                "files": files,
                "insertions": insertions,
                "deletions": deletions,
            }
        )
    return commits


def collect_worktree(repo_root: Path) -> list[dict[str, str]]:
    raw = run(["git", "status", "--short"], repo_root)
    changes: list[dict[str, str]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        status = line[:2]
        path_text = line[3:]
        if " -> " in path_text:
            path_text = path_text.split(" -> ", 1)[1]
        changes.append({"status": status, "path": path_text})
    return changes


def collect_codex_sessions(repo_root: Path, target_day: date) -> list[SessionNote]:
    session_dir = Path.home() / ".codex" / "sessions" / target_day.strftime("%Y/%m/%d")
    sessions: list[SessionNote] = []
    if not session_dir.exists():
        return sessions
    for path in sorted(session_dir.glob("*.jsonl")):
        prompts: list[str] = []
        final_message: str | None = None
        started_at: str | None = None
        ended_at: str | None = None
        session_id = path.stem
        repo_match = False
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                obj = json.loads(line)
                timestamp = obj.get("timestamp")
                if timestamp:
                    if not started_at:
                        started_at = timestamp
                    ended_at = timestamp
                if obj.get("type") == "session_meta":
                    payload = obj.get("payload", {})
                    repo_match = same_repo(payload.get("cwd"), repo_root)
                    session_id = payload.get("id", session_id)
                if not repo_match:
                    continue
                if obj.get("type") == "response_item":
                    payload = obj.get("payload", {})
                    if payload.get("type") == "message" and payload.get("role") == "user":
                        for raw_text in extract_text(payload.get("content")):
                            text = clean_prompt(raw_text)
                            if text:
                                prompts.append(text)
                elif obj.get("type") == "event_msg":
                    payload = obj.get("payload", {})
                    if payload.get("type") == "task_complete":
                        final_message = shorten(payload.get("last_agent_message"))
        deduped = dedupe_keep_order(prompts)
        if repo_match and (deduped or final_message):
            sessions.append(
                SessionNote(
                    source="codex",
                    session_id=session_id,
                    started_at=started_at,
                    ended_at=ended_at,
                    prompts=deduped,
                    final_message=final_message,
                )
            )
    return sessions


def claude_project_dir(repo_root: Path) -> Path:
    encoded = str(repo_root.resolve()).replace("/", "-")
    return Path.home() / ".claude" / "projects" / encoded


def collect_claude_sessions(repo_root: Path, target_day: date) -> list[SessionNote]:
    project_dir = claude_project_dir(repo_root)
    sessions: list[SessionNote] = []
    if not project_dir.exists():
        return sessions
    for path in sorted(project_dir.glob("*.jsonl")):
        prompts: list[str] = []
        session_id = path.stem
        started_at: str | None = None
        ended_at: str | None = None
        seen_target_day = False
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                obj = json.loads(line)
                timestamp = obj.get("timestamp")
                if timestamp and timestamp.startswith(target_day.isoformat()):
                    seen_target_day = True
                if obj.get("type") != "user":
                    continue
                if obj.get("isMeta") or obj.get("isSidechain"):
                    continue
                if not same_repo(obj.get("cwd"), repo_root):
                    continue
                if not timestamp or not timestamp.startswith(target_day.isoformat()):
                    continue
                if not started_at:
                    started_at = timestamp
                ended_at = timestamp
                message = obj.get("message", {})
                for raw_text in extract_text(message.get("content")):
                    text = clean_prompt(raw_text)
                    if text:
                        prompts.append(text)
        deduped = dedupe_keep_order(prompts)
        if seen_target_day and deduped:
            sessions.append(
                SessionNote(
                    source="claude",
                    session_id=session_id,
                    started_at=started_at,
                    ended_at=ended_at,
                    prompts=deduped,
                )
            )
    return sessions


def dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def group_paths(paths: list[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for path_text in paths:
        grouped[top_level_area(path_text)].append(path_text)
    return dict(sorted(grouped.items()))


def infer_themes(
    commits: list[dict[str, Any]],
    worktree: list[dict[str, str]],
    sessions: list[SessionNote],
    notes_text: str,
) -> list[str]:
    corpus: list[str] = []
    corpus.extend(commit["subject"].lower() for commit in commits)
    corpus.extend(change["path"].lower() for change in worktree)
    for session in sessions:
        corpus.extend(prompt.lower() for prompt in session.prompts)
    if notes_text:
        corpus.append(notes_text.lower())
    joined = " \n".join(corpus)
    scores: list[tuple[int, str]] = []
    for theme, keywords in THEME_RULES.items():
        score = sum(joined.count(keyword) for keyword in keywords)
        if score:
            scores.append((score, theme))
    scores.sort(reverse=True)
    return [theme for _, theme in scores[:5]]


def build_achievement_blocks(commits: list[dict[str, Any]], notes_text: str) -> list[dict[str, str]]:
    subjects = " \n".join(commit["subject"].lower() for commit in commits)
    combined = subjects + ("\n" + notes_text.lower() if notes_text else "")
    achievements: list[dict[str, str]] = []
    for rule in ACHIEVEMENT_RULES:
        if any(keyword in combined for keyword in rule["keywords"]):
            matched = [commit for commit in commits if any(keyword in commit["subject"].lower() for keyword in rule["keywords"])]
            achievements.append(
                {
                    "title": rule["title"],
                    "narrative": rule["narrative"],
                    "evidence": ", ".join(f"`{commit['sha'][:8]}`" for commit in matched[:4]) if matched else "external notes",
                }
            )
    return achievements[:5]


def collect_related_session_details(
    sessions: list[SessionNote],
    keywords: tuple[str, ...],
    limit: int = 2,
) -> list[str]:
    matched: list[str] = []
    for session in sessions:
        for prompt in session.prompts:
            prompt_lc = prompt.lower()
            if any(keyword in prompt_lc for keyword in keywords):
                matched.append(prompt)
    return dedupe_keep_order(matched)[:limit]


def build_wip_narratives(worktree: list[dict[str, str]]) -> list[str]:
    narratives: list[str] = []
    frontend_paths = [item["path"] for item in worktree if item["path"].startswith("frontend/")]
    if frontend_paths:
        narratives.append(
            "The main open thread is still the frontend review workbench: multiple review, modal, keyboard, and shared-component files are in flight, "
            "so the UI hardening work is not yet at a stable shipped boundary."
        )
    prompt_paths = [item["path"] for item in worktree if item["path"].startswith("prompts/") or item["path"].startswith("src/llm/")]
    if prompt_paths:
        narratives.append(
            "Prompt and model-provider tuning is still open. Factory configs and the Qwen provider are being adjusted, which means extraction behavior may still move tomorrow."
        )
    docs_paths = [item["path"] for item in worktree if item["path"].startswith("docs/") or item["path"].startswith("agent-profile/")]
    if docs_paths:
        narratives.append(
            "There is also process/tooling work still open around docs and agent-profile assets, so some of today’s operational improvements are not fully closed out yet."
        )
    return narratives[:3]


def build_strengths(commits: list[dict[str, Any]], worktree: list[dict[str, str]], achievements: list[dict[str, str]]) -> list[str]:
    strengths: list[str] = []
    titles = " ".join(item["title"].lower() for item in achievements)
    if "deploy" in titles and "test" in titles:
        strengths.append("You improved safety on both sides of the delivery loop: release controls got stronger while test credibility also improved.")
    if any("eval" in commit["subject"].lower() for commit in commits) and any("batch" in commit["subject"].lower() for commit in commits):
        strengths.append("You connected cost awareness to implementation instead of leaving it as analysis; the eval path now reflects the pricing insight.")
    if any("memory" in commit["subject"].lower() or "instruction" in commit["subject"].lower() for commit in commits):
        strengths.append("You invested in team leverage, not just feature output, by improving the shared agent operating model.")
    if not strengths and achievements:
        strengths.append("You focused on system-level improvements with durable payoff rather than only local feature work.")
    return strengths[:3]


def build_improvements(worktree: list[dict[str, str]], commits: list[dict[str, Any]], achievements: list[dict[str, str]]) -> list[str]:
    improvements: list[str] = []
    if len(commits) >= 8:
        top_areas = sorted(group_paths([path for commit in commits for path in commit["files"]]).keys())
        improvements.append(
            "The day spanned too many threads. Evidence: today's shipped work crossed "
            f"{len(commits)} commits and multiple areas ({', '.join(top_areas[:6])}). "
            "Action: add a lightweight pre-commit or pre-push guard that warns when staged files span too many top-level areas, "
            "so infra, eval, prompt, and UI work are forced into cleaner commit boundaries."
        )
    if len(worktree) >= 15:
        improvements.append(
            "Too much remained open at day end. Evidence: the worktree still held many unfinished files across multiple areas. "
            "Action: add an end-of-day helper command that summarizes dirty files by workstream and refuses a 'done for today' recap until each open thread is tagged as either ship, stash, or defer."
        )
    if any(item["path"].startswith("frontend/") for item in worktree) and any("frontend" in item["title"].lower() or "test" in item["title"].lower() for item in achievements):
        improvements.append(
            "Frontend hardening is still half-shipped. Evidence: review-workbench and shared-component files are still open while the day already included UI reliability work. "
            "Action: add a small visual/E2E regression pack for the known fragile review states, then use that pack as the gate before opening a new frontend thread."
        )
    return improvements[:3]


def build_summary(
    commits: list[dict[str, Any]],
    worktree: list[dict[str, str]],
    sessions: list[SessionNote],
    themes: list[str],
    achievements: list[dict[str, str]],
) -> list[str]:
    bullets: list[str] = []
    if not commits:
        bullets.append("No commits landed today; the day was mainly investigation and in-progress work.")
        return bullets
    if achievements:
        bullets.append(achievements[0]["narrative"])
        if len(achievements) > 1:
            bullets.append(achievements[1]["narrative"])
    if sessions:
        bullets.append(f"You used local Codex/Claude sessions heavily for investigation and design, but the value came from converting that exploration into shipped infra, eval, and quality improvements.")
    if worktree:
        bullets.append("The main gap is finish discipline: several frontend and prompt-related threads are still open, so the shipped story is stronger than the end-of-day cleanliness.")
    return bullets[:5]


def merge_context_into_achievements(
    achievements: list[dict[str, str]],
    notes_text: str,
    themes: list[str],
    sessions: list[SessionNote],
) -> list[dict[str, str]]:
    notes = note_bullets(notes_text)
    enriched: list[dict[str, str]] = []
    for item in achievements:
        narrative = item["narrative"]
        title_lower = item["title"].lower()
        if "eval" in title_lower:
            session_details = collect_related_session_details(
                sessions,
                ("cost", "batch", "eval framework", "accuracy ocr", "handwritten ocr"),
            )
            if session_details:
                narrative += f" The coding sessions show this was not a straight implementation: it involved cost validation and repeated eval-framework clarification before the cheaper path was trusted."
        if "eval" in title_lower:
            if any("3.6 yuan" in note.lower() or "batch chat" in note.lower() or "batch pricing" in note.lower() for note in notes):
                narrative += " The external notes also confirm the pricing outcome in practice: roughly 100 VLM calls came out to about 3.6 yuan, validating that the cheaper batch path is really being used."
        if "prompt" in title_lower:
            session_details = collect_related_session_details(
                sessions,
                ("crease lines", "customer prior", "field rules", "vlm", "prior"),
            )
            if session_details:
                narrative += " The supporting session trail shows this was a genuine analysis thread, not a quick cleanup, with back-and-forth over whether priors were helping or hurting extraction."
            if any("302/308" in note for note in notes):
                narrative += " The strongest supporting data point in the notes is a 302/308 field-accuracy run after prior/rule formatting changes, which suggests the cleanup was not merely cosmetic."
        if "agent" in title_lower:
            if any("onboarding" in note.lower() for note in notes):
                narrative += " This also showed up in the day notes as better onboarding for new team members, not just internal cleanup."
        if "deployment" in title_lower and "deployment safety" in themes:
            narrative += " In other words, today's work improved both release confidence and operator clarity."
        if "test suite" in title_lower:
            session_details = collect_related_session_details(
                sessions,
                ("frontend audit", "test-guard", "e2e", "keyboard", "modal", "review workbench"),
            )
            if session_details:
                narrative += " The related sessions also suggest the UI/test work took real verification effort rather than a one-pass fix."
        enriched.append({**item, "narrative": narrative})
    return enriched


def merge_context_into_open_items(
    wip_narratives: list[str],
    notes_text: str,
    worktree: list[dict[str, str]],
    sessions: list[SessionNote],
) -> list[str]:
    notes = note_bullets(notes_text)
    enriched = list(wip_narratives)
    if any("accuracy ocr" in note.lower() and ("keep" in note.lower() or "benchmark" in note.lower()) for note in notes):
        enriched.insert(
            0,
            "The biggest unresolved product decision is still OCR strategy: the notes show that removing high-accuracy OCR is not yet a clear win, so the flag stays while more benchmarking is done."
        )
    if any("crease_lines" in note.lower() and "open question" in note.lower() for note in notes):
        enriched.append(
            "There is also an unresolved correctness question around missing `crease_lines` in cloud behavior versus local runs, which should be treated as a real investigation thread rather than background noise."
        )
    if collect_related_session_details(sessions, ("formatting is bad", "customer_rules", "factory_rules", "remove accuracy ocr"), limit=1):
        enriched.append(
            "Several unresolved UX and extraction questions already consumed meaningful investigation time, so they should either be closed decisively or deferred explicitly instead of staying half-open."
        )
    if any(item["path"].startswith("frontend/") for item in worktree):
        enriched.append(
            "Frontend workbench hardening remains open in the worktree, so UI reliability work is still in transition rather than fully closed."
        )
    return dedupe_keep_order(enriched)[:4]


def merge_context_into_strengths(strengths: list[str], notes_text: str) -> list[str]:
    notes = note_bullets(notes_text)
    enriched = list(strengths)
    if any("confirmed! batch works now" in note.lower() or "batch works now" in note.lower() for note in notes):
        enriched.append("You did not stop at theory; you checked whether the batch-cost hypothesis held in real runs and used that evidence to drive implementation.")
    return dedupe_keep_order(enriched)[:4]


def merge_context_into_improvements(improvements: list[str], notes_text: str) -> list[str]:
    notes = note_bullets(notes_text)
    enriched = list(improvements)
    if any("formatting quality is still bad" in note.lower() or "formatting is bad" in note.lower() for note in notes):
        enriched.append(
            "Presentation quality is still trailing backend rigor. Evidence: your own daily notes explicitly call out formatting as bad. "
            "Action: do not rely on memory here; create a targeted UI audit checklist or Playwright visual check for the exact formatting failures so presentation regressions are caught automatically, not discussed repeatedly."
        )
    if any("open question" in note.lower() for note in notes):
        enriched.append(
            "Some decisions are staying open across too many loops. Evidence: the notes still carry unresolved questions around OCR strategy and `crease_lines` behavior after substantial investigation. "
            "Action: create a short decision record template with hypothesis, current evidence, stop/continue rule, and next owner so ambiguous topics stop drifting between 'active' and 'background'."
        )
    return dedupe_keep_order(enriched)[:4]


def build_risks(worktree: list[dict[str, str]], commits: list[dict[str, Any]]) -> list[str]:
    risks: list[str] = []
    if not worktree:
        risks.append("No dirty worktree was detected at recap time.")
        return risks
    untracked = [item["path"] for item in worktree if item["status"] == "??"]
    if untracked:
        risks.append(f"Untracked files need review before they disappear from memory: {summarize_paths(untracked, limit=5)}.")
    frontend_dirty = [item["path"] for item in worktree if item["path"].startswith("frontend/")]
    if frontend_dirty:
        risks.append("Frontend work is still mid-flight; avoid describing those changes as shipped until tests and commit boundaries are clear.")
    prompt_dirty = [item["path"] for item in worktree if item["path"].startswith("prompts/")]
    if prompt_dirty:
        risks.append("Prompt/config edits are open in the worktree; these usually need explicit validation against factory behavior before closing the day.")
    if commits and any("deploy" in commit["subject"].lower() for commit in commits) and worktree:
        risks.append("Today mixed shipped deployment/process work with new local WIP; tomorrow should keep release-safe changes and active feature work clearly separated.")
    return risks[:4]


def build_next_steps(worktree: list[dict[str, str]], commits: list[dict[str, Any]], themes: list[str]) -> list[str]:
    steps: list[str] = []
    if worktree:
        grouped = group_paths([item["path"] for item in worktree])
        biggest_area = max(grouped.items(), key=lambda pair: len(pair[1]))[0]
        steps.append(f"Finish or split the open `{biggest_area}` workstream into a deliberate commit boundary.")
    if any(item["path"].startswith("frontend/") for item in worktree):
        steps.append("Run targeted frontend tests or E2E coverage before shipping the current UI changes.")
    if any(item["path"].startswith("prompts/") for item in worktree):
        steps.append("Validate the prompt/factory edits with a concrete sample order before calling them done.")
    if any(theme == "agent workflow" for theme in themes):
        steps.append("Keep the recap habit: end the next session by regenerating the recap before context fades.")
    if not steps and commits:
        steps.append("Close the day by checking whether any follow-up from today's shipped commits still needs documentation or verification.")
    return steps[:4]


def render_markdown(
    target_day: date,
    repo_root: Path,
    commits: list[dict[str, Any]],
    worktree: list[dict[str, str]],
    codex_sessions: list[SessionNote],
    claude_sessions: list[SessionNote],
    notes_text: str,
) -> str:
    sessions = codex_sessions + claude_sessions
    themes = infer_themes(commits, worktree, sessions, notes_text)
    achievements = build_achievement_blocks(commits, notes_text)
    achievements = merge_context_into_achievements(achievements, notes_text, themes, sessions)
    summary = build_summary(commits, worktree, sessions, themes, achievements)
    wip_narratives = merge_context_into_open_items(build_wip_narratives(worktree), notes_text, worktree, sessions)
    strengths = merge_context_into_strengths(build_strengths(commits, worktree, achievements), notes_text)
    improvements = merge_context_into_improvements(build_improvements(worktree, commits, achievements), notes_text)

    achievement_lines = []
    for item in achievements:
        line = f"- **{item['title']}**: {item['narrative']} Evidence: {item['evidence']}."
        achievement_lines.append(localize_text(line))
    if not achievement_lines:
        achievement_lines.append(localize_text("- No strong achievement narrative could be inferred from today's shipped work."))

    wip_lines = [localize_text(f"- {item}") for item in wip_narratives]
    if not wip_lines and worktree:
        grouped_worktree = group_paths([item["path"] for item in worktree])
        for area, paths in grouped_worktree.items():
            wip_lines.append(localize_text(f"- `{area}` remains open across {len(paths)} file(s): {summarize_paths(paths)}"))
    if not wip_lines:
        wip_lines.append(localize_text("- Worktree was clean at recap time."))

    strength_lines = [localize_text(f"- {item}") for item in strengths]
    improvement_lines = [localize_text(f"- {item}") for item in improvements]
    source_lines = [
        localize_text(
            f"- Themes consolidated from commits, sessions, and notes: {', '.join(themes)}."
            if themes
            else "- Themes consolidated from commits, sessions, and notes.",
        ),
        localize_text(f"- Commits: {len(commits)}"),
        localize_text(f"- Dirty files: {len(worktree)}"),
        localize_text(f"- Codex sessions: {len(codex_sessions)}"),
        localize_text(f"- Claude sessions: {len(claude_sessions)}"),
    ]

    sections = [
        f"# Daily Recap - {target_day.isoformat()}",
        "",
        localize_text(f"_Repo: `{repo_root}`_"),
        "",
        localize_text("## What You Achieved"),
        *achievement_lines,
        "",
        localize_text("## What Is Still Open"),
        *wip_lines,
    ]
    if strength_lines:
        sections.extend(["", localize_text("## What You Did Well"), *strength_lines])
    if improvement_lines:
        sections.extend(["", localize_text("## Need Improvement"), *improvement_lines])
    sections.extend(
        [
            "",
            localize_text("## Source Snapshot"),
            *source_lines,
        ]
    )
    return "\n".join(sections).rstrip() + "\n"


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    target_day = parse_day(args.date)
    output = Path(args.output) if args.output else repo_root / "docs" / "daily-recaps" / f"{target_day.isoformat()}.md"
    notes_text = read_optional_text(args.notes_file)

    commits = collect_git_commits(repo_root, target_day)
    worktree = collect_worktree(repo_root)
    codex_sessions = collect_codex_sessions(repo_root, target_day)
    claude_sessions = collect_claude_sessions(repo_root, target_day)
    markdown = render_markdown(target_day, repo_root, commits, worktree, codex_sessions, claude_sessions, notes_text)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
