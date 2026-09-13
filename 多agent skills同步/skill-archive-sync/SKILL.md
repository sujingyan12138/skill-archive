---
name: skill-archive-sync
description: Archive newly created or modified skills into D:\PyCharm\CODE\SKILL and push that archive repository. Use this whenever the user creates, edits, improves, syncs, packages, or finalizes a skill and mentions skill archive, D:\PyCharm\CODE\SKILL, "同步到SKILL仓库", "推送远端", "归档skill", or wants good skills preserved in the remote archive. Also use after project/global skill work when the user expects changed skills to be backed up.
---

# Skill Archive Sync

Use this skill after creating or modifying a skill when the user wants that skill preserved in the archive repository:

```text
D:\PyCharm\CODE\SKILL
```

The archive is a Git repository that stores useful skills by category. Preserve the source skill folder structure exactly, including `SKILL.md`, `scripts/`, `references/`, `assets/`, eval files, and other bundled resources.

## Trigger Context

Use this skill when the user asks to:

- sync a new or changed skill to `D:\PyCharm\CODE\SKILL`
- find an older archived copy of a skill and update it
- push skill changes to the archive remote
- preserve a newly created global/project skill
- keep `.codex/skills`, `.claude/skills`, `.agents/skills`, `.cc-switch/skills`, and the archive repository aligned

If the current task just edits a project skill but the user has previously established that skill edits should be archived, use this skill before finishing.

## Archive Rules

1. Identify the source skill directory.
   - Prefer an explicit source path from the user.
   - Otherwise use the skill directory just created or modified.
   - Valid source roots include project `.codex/skills/<name>`, `.claude/skills/<name>`, `.agents/skills/<name>`, global `%USERPROFILE%\.cc-switch\skills\<name>`, `%USERPROFILE%\.codex\skills\<name>`, and `%USERPROFILE%\.claude\skills\<name>`.

2. Search the archive for existing copies.
   - Find directories named exactly like the source skill and containing `SKILL.md`.
   - If multiple existing copies are found, update all of them unless the user names a category.
   - If no existing copy is found, create one under the best matching archive category.

3. Choose a category conservatively.
   - Prefer the category the user explicitly names.
   - If the skill is about agent/skill synchronization, use `多agent skills同步`.
   - If the skill is about creating skills, use `Skill创建`.
   - If the skill is about daily summaries, use `日常学习总结`.
   - If the skill is project-specific, use `项目/<project-or-system-name>`.
   - If uncertain, inspect the archive root folders and choose the nearest existing category; ask only when a wrong category would create lasting confusion.

4. Preserve archive history.
   - Do not delete archive files unless the user explicitly asks.
   - Do not stage unrelated dirty files.
   - Inspect `git status --short` before committing.
   - Commit only the copied skill path(s).

5. Push after committing.
   - Push to `origin`.
   - If push fails because of network/proxy issues, retry in PowerShell with:

```powershell
$env:HTTP_PROXY='http://127.0.0.1:10808'
$env:HTTPS_PROXY='http://127.0.0.1:10808'
git push
```

Report the target archive path, commit hash, and push result. If the archive already has unrelated dirty files, mention that they were left untouched.

## Script Workflow

**Environment caveat (verified 2026-09-13):** the bundled `sync-skill-archive.ps1` contains the path-joining cmdlet token that the WorkBuddy agent's PowerShell sandbox silently kills, and it also may need `cmd.exe`/child processes, which that tool forbids. **In the agent environment, do NOT try to run the script — use the Manual Workflow below** (Bash tool + `cp` + `git`). The script remains valid for a real PowerShell console outside the agent.

Use the bundled script (real console only) for deterministic sync:

```powershell
$env:SystemRoot='C:\Windows'; $env:WINDIR='C:\Windows'
& "$env:USERPROFILE\.cc-switch\skills\skill-archive-sync\scripts\sync-skill-archive.ps1" `
  -SourcePath "C:\path\to\skill-name" `
  -Category "多agent skills同步" `
  -Push
```

Useful options:

- `-SkillName <name>`: pass when the source folder name is not enough or when searching only.
- `-ArchiveRoot <path>`: defaults to `D:\PyCharm\CODE\SKILL`.
- `-Category <name>`: create/update under that archive category when no old copy exists, or restrict updates to that category.
- `-AllMatches`: update every archived copy with the same skill name. This is the default behavior when no category is given.
- `-DryRun`: show what would change without copying, committing, or pushing.
- `-CommitMessage <message>`: override the generated commit message.
- `-Push`: commit and push after syncing.

## Manual Workflow (agent environment — preferred)

Do the same steps with the Bash tool. Never invoke PowerShell from Bash (blocked by policy); `cp` and `git` are fine.

1. Inspect the archive: `ls "D:/PyCharm/CODE/SKILL"` and search for an existing copy with the same skill name (`find "D:/PyCharm/CODE/SKILL" -maxdepth 2 -type d -name "<skill-name>"`).
2. Choose a category: reuse the one that already holds the copy; otherwise pick the nearest existing category folder, or place the skill as its own root-level folder when comparable utility skills live at the archive root (e.g. `Word图表快速插入`).
3. Copy the source skill folder into the archive:
   `cp -r "C:/Users/Chen/.workbuddy/skills/<name>" "D:/PyCharm/CODE/SKILL/<category-or-root>/<name>"`
4. `git -C "D:/PyCharm/CODE/SKILL" status --short` — stage only the skill path, never unrelated dirty files.
5. `git -C "D:/PyCharm/CODE/SKILL" add <path>` then commit with a descriptive Chinese message.
6. Push: `git -C "D:/PyCharm/CODE/SKILL" push`. On proxy failure, retry with `HTTP_PROXY`/`HTTPS_PROXY=http://127.0.0.1:10808` exported in the Bash environment. If it still fails, leave the local commit and report that the push is pending.
7. Confirm with `git status -sb` (`[ahead N]` means the push did not land).

## Verification

After the script runs:

1. Check the displayed archive target paths.
2. Confirm `git status --short` only shows expected unrelated pre-existing files, or is clean.
3. If the script reports `NO_CHANGES`, do not create an empty commit.
4. If push failed after the proxy retry, report the exact failure and leave the local commit intact.
