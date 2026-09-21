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
   - Proxy and credentials are already configured globally, so a plain `git push` normally just works (see next section). Only if it fails, fall back to exporting `HTTP_PROXY`/`HTTPS_PROXY=http://127.0.0.1:10808` for a one-off retry.

Report the target archive path, commit hash, and push result. If the archive already has unrelated dirty files, mention that they were left untouched.

## 网络与认证（2026-09-21 实测结论，勿再重复踩坑）

**这台机器直连 github.com 不通，必须走本机代理 `127.0.0.1:10808`。** 这不是 git 或沙箱的限制，是网络层到 GitHub 的连通性被阻断（实测：直连 `github.com:443` 超时 21s；走代理 0.67s 返回 200）。无法通过改配置绕过——代理是必需品。

**代理已经配好了，`git push` 不需要加任何参数。** 配置写在用户级 `C:\Users\Chen\.gitconfig`，用 **URL 作用域**的写法，只有 GitHub 系域名走代理，gitee / 内网 Git 等一律直连：

```ini
[http "https://github.com/"]
    proxy = http://127.0.0.1:10808
[https "https://github.com/"]
    proxy = http://127.0.0.1:10808
```

四个域名已覆盖：`github.com`、`codeload.github.com`、`raw.githubusercontent.com`、`objects.githubusercontent.com`。

**代理开关**：用户代理软件不是常驻的（偶尔关）。代理关闭时上面的配置会让 GitHub 请求失败——那是预期行为。用归档仓库根目录的 `.git-proxy.ps1` 一键切换（**该脚本必须保持 UTF-8 BOM**，否则 PS 5.1 按 GBK 读会把中文注释变乱码）：

```powershell
. "D:\PyCharm\CODE\SKILL\.git-proxy.ps1" status   # 看当前状态 + 探测端口是否开放
. "D:\PyCharm\CODE\SKILL\.git-proxy.ps1" off      # 关代理（回到直连）
. "D:\PyCharm\CODE\SKILL\.git-proxy.ps1" on       # 开代理（默认 10808）
```

**认证：不需要用户手动登录，凭证已存在。** GitHub 凭证由 **Git Credential Manager（GCM）** 保管，路径 `C:\Program Files\Git\mingw64\bin\git-credential-manager.exe`。验证方式（不会弹窗）：

```bash
printf "protocol=https\nhost=github.com\n\n" | "C:/Program Files/Git/cmd/git.exe" credential fill
# 会返回 username=... 和 password=...（就是可用凭证）
```

### ⭐ 推送的正确姿势：用系统 git，不要用沙箱里的便携版 git

**这是 2026-09-21 最重要的结论。** WorkBuddy 沙箱里 `which git` 拿到的是便携版（`PortableGit/versions/1.2.0`），它的凭证助手是 `helper-selector`，在无 TTY 的沙箱里**必然失败**：

```
fatal: could not read Username for 'https://github.com': terminal prompts disabled
```

而系统的 `C:\Program Files\Git\cmd\git.exe` 用的是 `helper = manager`（GCM），**静默取到凭证、直接 push 成功**。所以归档推送一律这样写：

```bash
SYSGIT="/c/Program Files/Git/cmd/git.exe"
"$SYSGIT" -C "D:/PyCharm/CODE/SKILL" add <path>
"$SYSGIT" -C "D:/PyCharm/CODE/SKILL" commit -m "<中文说明>"
"$SYSGIT" -C "D:/PyCharm/CODE/SKILL" push
"$SYSGIT" -C "D:/PyCharm/CODE/SKILL" status -sb   # 无 [ahead N] 即推送成功
```

实测（2026-09-21）：`8a3f4df..9b28057  main -> main`，无需任何交互。

**别试图在用户级 `.gitconfig` 里修 `credential.helper`** —— 试过，两种写法都坏：
- 写无引号绝对路径 → 空格截断，报 `C:/Program: No such file or directory`
- 写带引号 → GCM 被调用但找不到凭证，**弹图形窗口把无交互环境卡死**（实测挂起 2 分钟后强杀）

保持用户级 `.gitconfig` 里**不出现 `credential.helper`**，让它自然回退到 system 级即可。

**验证 push 前必须用 `--dry-run` 或 `credential fill` 走认证路径**。⚠️ `git ls-remote` 对公开仓库**不需要认证**，用它判断"认证是否可用"会得到假阳性（2026-09-21 就因此误判过一次）。

**⚠️ 两个必须知道的坑：**

1. **`git credential fill` 会打印明文 token，别让它出现在对话输出里。** 排查时一律用 `sed 's/password=.*/password=<已隐藏>/'` 过滤。2026-09-21 曾不慎把 token 打到终端，该 token 应视为泄露、建议吊销重建。
2. **绝对不要**用 `GCM_INTERACTIVE=never git-credential-manager get` 之类的探针去"看有没有凭证"——GCM 找不到凭证时会弹图形窗口，在无交互环境里会**永久挂起**（实测卡死 2 分钟后被强杀）。判断凭证是否存在只走 `git credential fill`。

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

Do the same steps with the Bash tool. Never invoke PowerShell from Bash (blocked by policy); `cp` and git are fine.

**关键：git 命令一律用系统 git 的绝对路径**（沙箱便携版 git 无法认证，详见上文「推送的正确姿势」）：

```bash
SYSGIT="/c/Program Files/Git/cmd/git.exe"
```

1. Inspect the archive: `ls "D:/PyCharm/CODE/SKILL"` and search for an existing copy with the same skill name (`find "D:/PyCharm/CODE/SKILL" -maxdepth 2 -type d -name "<skill-name>"`).
2. Choose a category: reuse the one that already holds the copy; otherwise pick the nearest existing category folder, or place the skill as its own root-level folder when comparable utility skills live at the archive root (e.g. `Word图表快速插入`).
3. Copy the source skill folder into the archive, **excluding runtime files** (`.cache/`, `__pycache__/`, `*.pyc`, `.state.json`, `.skill-backups/`, `*.bak*`, `*.lock`):
   `cp -r "C:/Users/Chen/.workbuddy/skills/<name>" "D:/PyCharm/CODE/SKILL/<category-or-root>/<name>"`
4. `"$SYSGIT" -C "D:/PyCharm/CODE/SKILL" status --short` — stage only the skill path, never unrelated dirty files.
5. `"$SYSGIT" -C "D:/PyCharm/CODE/SKILL" add <path>` then commit with a descriptive Chinese message.
6. Push: `"$SYSGIT" -C "D:/PyCharm/CODE/SKILL" push`. 代理与凭证都已配好，无需任何参数。若报连不上，先用 `.git-proxy.ps1 status` 确认代理软件在跑；代理没开就开它，别去改 git 配置。若仍失败，保留本地提交并如实报告 push 未完成。
7. Confirm with `"$SYSGIT" -C "D:/PyCharm/CODE/SKILL" status -sb` (`[ahead N]` means the push did not land).

## Verification

After the script runs:

1. Check the displayed archive target paths.
2. Confirm `git status --short` only shows expected unrelated pre-existing files, or is clean.
3. If the script reports `NO_CHANGES`, do not create an empty commit.
4. If push failed after the proxy retry, report the exact failure and leave the local commit intact.
