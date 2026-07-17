---
name: experience-summary-writer
description: Maintain and safely retrieve the cross-project AI collaboration ledger at D:\Homework\Obsidian\经验总结.md. Use this whenever the user asks to record, improve, review, or retrieve reusable pitfalls, debugging lessons, operational mistakes, thinking mistakes, collaboration takeaways, or a personal AI memory system; trigger on phrases such as "把这次踩坑写进经验总结", "总结这次协作经验", "记录到经验总结.md", and "以后遇到类似问题先查经验总结". Also use proactively when an AI is stuck or repeats failed attempts: search the ledger for scoped hypotheses, validate them against current evidence, and write back only after a reusable lesson is established.
---

# Experience Summary Writer

This skill keeps one durable cross-project troubleshooting and collaboration ledger:

```text
D:\Homework\Obsidian\经验总结.md
```

The file is not a diary. It is a reusable memory layer for AI agents working across different folders, projects, tools, and contexts.

## Memory Boundary

Keep each kind of information in its correct layer:

- Personalization instructions: stable user preferences and directions for where agents should look.
- `经验总结.md`: cross-project lessons that remain useful beyond the current task.
- Project `AGENTS.md` or `CLAUDE.md`: project-specific rules, commands, constraints, and acceptance criteria.
- Project docs or memory bank: current goal, active decisions, progress, next steps, and unresolved issues.
- Skills: repeatable procedures, tool choices, input/output contracts, and checklists.
- Official docs, web research, or connectors: live external facts that may change.

Do not promote temporary task state, one-project implementation details, unverified guesses, or fast-changing external facts into durable cross-project memory.

## When To Use

Use this skill in two modes.

### 1. Before solving a stuck problem

Search the ledger when a task is blocked, repeats failed attempts, resembles a known symptom, involves a high-risk operation, or the user explicitly asks. Do not read the entire ledger for every routine task.

1. Open `D:\Homework\Obsidian\经验总结.md`.
2. Search by symptom, tool name, platform, error message, folder, network condition, or operation type.
3. Read only the matching index, category, and nearby entries.
4. Check `状态`, `适用边界`, `最后验证`, and the current environment before using a result.
5. Apply the entry as a hypothesis, then verify it with current first-hand evidence.

Do not blindly copy old fixes. Treat the ledger as a set of hypotheses and reusable checks.

### 2. After a collaboration or debugging session

When the user asks to record this session, or when a meaningful pitfall was discovered:

1. Reconstruct what happened from tool output, files changed, commands, errors, and final fix.
2. Extract reusable lessons, not a full chat transcript.
3. Apply the write-back gate: keep the lesson only if it is useful across projects, prevents meaningful repeated cost, and has current evidence or is clearly marked as a hypothesis.
4. Route project-only state and rules to project documentation instead of this ledger.
5. Add or update entries in `经验总结.md` under the best category.
6. If the same issue already exists, update the old entry with a new note instead of creating a duplicate.
7. Keep the writing concise, concrete, and searchable.

Do not write merely because a task completed. One-off commands, chat summaries, transient paths, and facts already documented by an authoritative source usually do not belong here.

## Conflict Order

Resolve conflicts in this order:

1. The user's current explicit instruction.
2. Current project instructions and constraints.
3. First-hand evidence from current files, tools, tests, and official documentation.
4. This experience ledger.
5. External examples and community advice.

When current evidence disproves an old entry, update that entry's status, boundary, or conclusion. Do not create a second entry that silently contradicts it.

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

- 状态：有效 | 推测 | 待复核 | 已过时
- 触发场景：
- 适用边界：
- 表现：
- 根因：
- 解决：
- 复用规则：
- 验证：
- 最后验证：YYYY-MM-DD
- 关键词：
```

Field rules:

- `状态`: use `有效` for reproduced results, `推测` for unproven conclusions, `待复核` when the environment or premise changed, and `已过时` when the lesson should no longer be applied.
- `触发场景`: the situation where the problem appeared.
- `适用边界`: environments and assumptions where the lesson applies, plus important exclusions.
- `表现`: concrete symptoms, error text, wrong result, or failed behavior.
- `根因`: the best-supported cause. If uncertain, say `推测根因`.
- `解决`: the action that actually worked.
- `复用规则`: one sentence that future AI can apply.
- `验证`: how the fix was confirmed.
- `最后验证`: the most recent date on which the conclusion was checked against current evidence.
- `关键词`: searchable terms, tools, commands, filenames, or platform names.

## Writing Rules

- Write in Chinese unless source errors or commands are clearer in English.
- Prefer short, dense entries. One entry should usually be 8 to 14 lines.
- Do not paste long logs. Keep only the error line or command that matters.
- Do not record secrets, tokens, cookies, private credentials, or personal account details.
- Keep file links and paths exact when they are useful for future reuse.
- Separate facts from inference. Use `推测根因` when the cause was not fully proven.
- Prefer updating a matching entry over adding another. Preserve one current conclusion and explain why older advice became invalid.
- Preserve user wording if the user gives a key insight, then add a cleaned-up reusable rule.
- If an entry belongs to multiple categories, put it under the category future agents are most likely to search first, and include cross-keywords in `关键词`.
- Report the titles of entries added, corrected, or marked stale in the final response so durable memory is never changed silently.

## Maintenance Rules

When `经验总结.md` grows messy:

1. Merge duplicate entries that describe the same root cause.
2. Move entries out of `待归类`.
3. Split overloaded categories into clearer subheadings.
4. Keep old lessons, but mark obsolete fixes with `状态：已过时` instead of deleting them.
5. Maintain the `快速检索索引` near the top with high-value keywords and category links.
6. When an old entry is touched, gradually add missing `状态`, `适用边界`, and `最后验证` fields; do not create noisy bulk migrations solely for formatting.

## Minimal Workflow

When the user says:

> 请你把你这次你和我协作遇到的所有操作或者思维上的坑和经验总结下来然后写到 "D:\Homework\Obsidian\经验总结.md"

Do this:

1. Read the current ledger.
2. Identify up to 3 to 8 candidate lessons, then discard anything transient, project-only, duplicated, sensitive, or unsupported.
3. Group them into existing categories.
4. Add the new fields and edit `经验总结.md`.
5. Re-read the edited section and verify that headings, status, dates, links, and keywords are valid.
6. Report which categories were updated and list the added or changed entry titles.

If there were no meaningful pitfalls, say that clearly and add nothing.
