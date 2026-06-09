---
name: experience-summary-writer
description: Maintain the cross-project AI collaboration experience ledger at D:\Homework\Obsidian\经验总结.md. Use this whenever the user asks to summarize pitfalls, lessons, debugging experience, operational mistakes, thinking mistakes, project collaboration takeaways, or says phrases like "把这次踩坑写进经验总结", "总结这次协作经验", "记录到经验总结.md", "以后遇到类似问题先查经验总结". Also use proactively when an AI gets stuck or repeats failed attempts: first search the ledger for similar cases, then append a concise reusable lesson after the issue is resolved.
---

# Experience Summary Writer

This skill keeps one durable cross-project troubleshooting and collaboration ledger:

```text
D:\Homework\Obsidian\经验总结.md
```

The file is not a diary. It is a reusable memory layer for AI agents working across different folders, projects, tools, and contexts.

## When To Use

Use this skill in two modes.

### 1. Before solving a stuck problem

When a task is blocked, repeating failed attempts, or smells similar to past issues:

1. Open `D:\Homework\Obsidian\经验总结.md`.
2. Search by symptom, tool name, platform, error message, folder, network condition, or operation type.
3. Read the matching category and entries before trying more fixes.
4. Apply only the parts that match the current evidence.

Do not blindly copy old fixes. Treat the ledger as a set of hypotheses and reusable checks.

### 2. After a collaboration or debugging session

When the user asks to record this session, or when a meaningful pitfall was discovered:

1. Reconstruct what happened from tool output, files changed, commands, errors, and final fix.
2. Extract reusable lessons, not a full chat transcript.
3. Add or update entries in `经验总结.md` under the best category.
4. If the same issue already exists, update the old entry with a new note instead of creating a duplicate.
5. Keep the writing concise, concrete, and searchable.

## Ledger Categories

Use existing headings when possible. Add a new top-level category only when no existing category can reasonably hold the lesson.

Default categories:

- `网络环境与代理`: proxy, DNS, TLS, GitHub push, package download, API timeout, mainland network issues.
- `文件系统与路径`: Windows paths, quoting, Chinese paths, spaces, sandbox/workspace confusion, temp files.
- `Git 与远端仓库`: dirty worktrees, staging scope, push failures, branch/remote issues, commit hygiene.
- `工具链与依赖`: Python, Node, PowerShell, ffmpeg, yt-dlp, OCR, whisper, package versions.
- `浏览器自动化与视频处理`: Playwright, Douyin/Bilibili/YouTube capture, cookies, anti-crawl, video OCR/transcription.
- `AI 协作与提示词`: task framing, role design, prompt mistakes, over-automation, human review checkpoints.
- `项目结构与文档`: repo conventions, AGENTS/CLAUDE/SOUL rules, skill sync, index maintenance, Obsidian file layout.
- `Windows 环境`: environment variables, PowerShell behavior, permissions, encoding, process/session issues.
- `待归类`: temporary holding area. Clean this up when the file grows.

## Entry Format

Each entry should use this exact shape:

```markdown
### YYYY-MM-DD | 项目/场景 | 简短标题

- 触发场景：
- 表现：
- 根因：
- 解决：
- 复用规则：
- 验证：
- 关键词：
```

Field rules:

- `触发场景`: the situation where the problem appeared.
- `表现`: concrete symptoms, error text, wrong result, or failed behavior.
- `根因`: the best-supported cause. If uncertain, say `推测根因`.
- `解决`: the action that actually worked.
- `复用规则`: one sentence that future AI can apply.
- `验证`: how the fix was confirmed.
- `关键词`: searchable terms, tools, commands, filenames, or platform names.

## Writing Rules

- Write in Chinese unless source errors or commands are clearer in English.
- Prefer short, dense entries. One entry should usually be 8 to 14 lines.
- Do not paste long logs. Keep only the error line or command that matters.
- Do not record secrets, tokens, cookies, private credentials, or personal account details.
- Keep file links and paths exact when they are useful for future reuse.
- Separate facts from inference. Use `推测根因` when the cause was not fully proven.
- Preserve user wording if the user gives a key insight, then add a cleaned-up reusable rule.
- If an entry belongs to multiple categories, put it under the category future agents are most likely to search first, and include cross-keywords in `关键词`.

## Maintenance Rules

When `经验总结.md` grows messy:

1. Merge duplicate entries that describe the same root cause.
2. Move entries out of `待归类`.
3. Split overloaded categories into clearer subheadings.
4. Keep old lessons, but mark obsolete fixes with `状态：已过时` instead of deleting them.
5. Maintain the `快速检索索引` near the top with high-value keywords and category links.

## Minimal Workflow

When the user says:

> 请你把你这次你和我协作遇到的所有操作或者思维上的坑和经验总结下来然后写到 "D:\Homework\Obsidian\经验总结.md"

Do this:

1. Read the current ledger.
2. Identify 3 to 8 reusable lessons from the current session.
3. Group them into existing categories.
4. Edit `经验总结.md`.
5. Report which categories were updated and list the new entry titles.

If there were no meaningful pitfalls, say that clearly and add nothing.
