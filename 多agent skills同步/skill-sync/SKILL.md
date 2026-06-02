---
name: skill-sync
description: Keep project Codex/agent and Claude skills synchronized, while packaging this sync tool for global installation. Use this whenever the user asks to create, update, improve, perfect, finalize, synchronize, or package a skill, especially if they mention .codex/skills, .claude/skills, .agents/skills, project skills, global install, or a zip package.
allowed-tools: Bash(powershell:*) Bash(pwsh:*)
---

# Skill Sync

Use this skill whenever you create or modify any skill.

The goal is simple: install this `skill-sync` tool globally, then use it inside any project to keep that project's Codex/agent skill copy and Claude skill copy aligned.

Sync behavior is conservative:

- Files that exist only on one side are copied to the other side.
- Files that exist on both sides and are identical are skipped.
- Files that differ are resolved by modification time; newer overwrites older.
- The script does not delete extra files.

## Skill Locations

Project-level destinations:

```text
<project>\.codex\skills\<skill-name>
<project>\.claude\skills\<skill-name>
```

Optional project source/destination used by some agent workspaces:

```text
<project>\.agents\skills\<skill-name>
```

Global installation locations for this `skill-sync` tool:

```text
%USERPROFILE%\.codex\skills\skill-sync
%USERPROFILE%\.claude\skills\skill-sync
```

Do not copy ordinary project skills to global locations by default. Project skills should stay project-local unless the user explicitly asks to install that specific skill globally.

Do not assume every project has `.agents\skills`. Some projects use `.codex\skills` only.

Project sync rule:

- If `<project>\.codex\skills` exists, sync the project Codex copy there.
- If `<project>\.codex\skills` does not exist but `<project>\.agents\skills` exists, sync the project Codex/agent copy there.
- Always sync `<project>\.claude\skills` for Claude.

## Source Selection

When syncing an existing project skill, choose the source in this order unless the user explicitly says otherwise:

1. Explicit `-SourcePath`, if provided.
2. `<project>\.agents\skills\<skill-name>`, if it exists.
3. `<project>\.codex\skills\<skill-name>`, if it exists.
4. `<project>\.claude\skills\<skill-name>`, if it exists.

Only consider global source copies when the command is run with `-Global` or the user explicitly asks to install/sync a global skill.

When creating a new skill in a project that has no existing copy, create the first working copy under:

```text
<project>\.codex\skills\<skill-name>
```

Then run the sync script so the project `.claude\skills` copy is created too.

If the project already uses `.agents\skills` and has no `.codex\skills`, create it under:

```text
<project>\.agents\skills\<skill-name>
```

Then run the sync script so the project Claude copy is created too.

## Sync Command

Run from the current project root when possible:

```powershell
$env:SystemRoot='C:\Windows'; $env:WINDIR='C:\Windows'
& "<path-to-skill-sync>\scripts\sync-skill.ps1" -SkillName "<skill-name>"
```

If the source is not in the current project, pass it explicitly:

```powershell
$env:SystemRoot='C:\Windows'; $env:WINDIR='C:\Windows'
& "<path-to-skill-sync>\scripts\sync-skill.ps1" -SkillName "<skill-name>" -SourcePath "C:\path\to\<skill-name>"
```

In this Codex environment, prefer invoking the script in the current PowerShell with `&`. Starting a nested `powershell -File` can fail if the current process has not inherited `SystemRoot`/`WINDIR`.

## Package Command

To produce a zip that the user can install globally for `skill-sync` itself or for a skill the user explicitly wants globally installed:

```powershell
$env:SystemRoot='C:\Windows'; $env:WINDIR='C:\Windows'
& "<path-to-skill-sync>\scripts\sync-skill.ps1" -SkillName "<skill-name>" -Package
```

Default package output:

```text
<project>\dist\<skill-name>.zip
```

The zip contains the skill folder itself, so it can be extracted into:

```text
%USERPROFILE%\.codex\skills
%USERPROFILE%\.claude\skills
```

To also sync a skill to global Codex/Claude skill folders, use `-Global` explicitly:

```powershell
$env:SystemRoot='C:\Windows'; $env:WINDIR='C:\Windows'
& "<path-to-skill-sync>\scripts\sync-skill.ps1" -SkillName "<skill-name>" -Global
```

Use `-Global` for `skill-sync` itself or for a skill the user explicitly wants installed globally. Do not use it for ordinary project-only skills.

## Required Workflow

Whenever the user says to create or improve a skill:

1. Edit one source copy only.
2. Run `sync-skill.ps1` for that skill.
3. Verify hashes for `SKILL.md` across project Codex/agent copy (`.codex` if present, otherwise `.agents`) and project `.claude`.
4. If the user asks for an installable artifact, run with `-Package` and return the zip path.

If syncing exposes a new pitfall, update this skill first, then sync `skill-sync` itself.

## Design Note

This skill intentionally combines two patterns:

- Obsidian's `sync_agent_skills.py` style: bidirectional, file-level, mtime-based, no deletes.
- The project skill workflow here: `.codex` first, `.agents` fallback, `.claude` project copy, optional `-Global`, and installable zip output.
