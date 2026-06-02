---
name: windows-space-slimming
description: Use this skill when the user wants to free space on a Windows system drive, especially by assessing large folders under AppData, Local, Roaming, or similar user-data paths; deciding whether a directory is safe to migrate; moving it to another drive; and preserving app compatibility with directory junctions, backups, and validation.
---

# Windows Space Slimming

## Overview

Use this skill to do low-risk Windows space slimming, especially when the user wants to move large user-data folders off `C:` without breaking apps. The default pattern is: inspect first, prefer `Junction` for compatibility, keep a `.old` backup until the app is verified, then remove the backup.

## When to Use

Use this skill when the task involves one or more of these:

- Freeing space on `C:`
- Assessing whether a folder under `AppData`, `Local`, `Roaming`, or another user-data path is safe to move
- Moving browser data, chat data, model folders, media caches, or app configuration folders to another drive
- Replacing the original path with `mklink /J`
- Handling "file in use", "access denied", or "file exists" during migration

Read [references/windows-folder-guide.md](./references/windows-folder-guide.md) when you need:

- A folder risk matrix
- Suggested categories for safe vs risky moves
- Command templates
- A reusable migration checklist

## Core Rule

Do not treat Windows space slimming as "delete large things fast". Treat it as controlled relocation of user data with rollback.

Default preference order:

1. Check whether the folder is user data rather than a core system path.
2. Check whether the owning app is running.
3. Copy to the target drive.
4. Rename the original folder to `.old`.
5. Create a directory junction with `mklink /J`.
6. Verify the app still works.
7. Remove `.old` only after verification.

## Decision Rules

### Prefer `Junction` over `/D`

For folders moved within the same Windows machine, prefer:

```cmd
mklink /J "C:\original\path" "E:\target\path"
```

Use `Junction` by default for:

- Browser user data
- Chat app data
- Media player config/model folders
- Large user caches and model directories

Reason:

- Better compatibility with many Windows apps and cleanup tools
- Fewer surprises than symbolic links for common desktop software

Only prefer `mklink /D` when the task explicitly requires symbolic link behavior and the software is known to tolerate it.

### Safe-by-default candidates

Usually good migration candidates:

- `AppData\Local\Google`
- `AppData\Local\Microsoft\Edge`
- `AppData\Roaming\Tencent\...`
- `AppData\Roaming\PotPlayerMini64`
- Model, cache, playlist, plugin, and browser-profile directories under the user profile

### High-risk candidates

Be much more cautious with:

- `Windows\...`
- `Program Files\...`
- `ProgramData\...`
- Driver-related paths
- Folders locked by system services or containers

Do not force migration just because a folder is large. If it is tied to drivers, services, or privileged processes, stop and explain the risk.

## Workflow

### 1. Inspect before moving

For each candidate folder:

- Check existence
- Check total size
- Check whether target directory already exists
- Check active processes that may own the folder
- Check whether the folder already is a reparse point

### 2. Decide if the folder should be moved

Ask:

- Is this primarily user data, cache, configuration, models, or app state?
- Is it outside core system paths?
- Is the software likely to tolerate a junction at the original path?

If yes, continue. If unclear, inspect more and bias toward caution.

### 3. Stop the owning app if needed

If the folder belongs to a running app:

- Stop user-space processes first
- Re-check whether the directory is still in use
- If system-level processes still hold the path, explain that admin elevation or Safe Mode may be required

Do not claim success if the rename step cannot be completed.

### 4. Migrate with rollback

Preferred sequence:

1. Copy to the destination with `robocopy`
2. Rename source to `.old`
3. Create the junction at the original path
4. Verify the junction target
5. Launch the app or ask the user to verify

Do not delete the original data before the app is verified.

### 5. Verify before cleanup

Good verification signals:

- The app launches normally
- Existing settings, chat history, bookmarks, playlists, or models still appear
- The original path shows as `Junction`
- The target directory on the other drive receives updates

Only after that should `.old` be removed.

## Handling Common Failures

### `mklink` says the file already exists

This usually means the original source path still exists. `mklink` cannot replace an existing directory.

### Access denied or rename fails

Likely causes:

- The app is still running
- A background service owns the folder
- The terminal is not elevated

Next actions:

- Stop the owning processes
- Retry
- If still blocked and the folder is system-tied, recommend admin terminal or Safe Mode

### Copy is partially blocked by locked files

Do not pretend the migration is complete. Explain which files are still in use and whether the remaining data is only cache or is still important state.

## Response Pattern

When using this skill, structure the work like this:

1. State that you will inspect the folder, target path, and active processes first.
2. Classify the folder as safe, caution, or high risk.
3. Say whether `Junction` or symbolic link is preferred, and why.
4. Execute the migration if the risk is acceptable.
5. Keep backups until verification.
6. Summarize what was moved, what remains, and whether cleanup is still pending.

## Boundaries

Do not:

- Use destructive commands like `git reset --hard` equivalents for filesystem cleanup
- Delete the original folder before a verified replacement exists
- Move core Windows folders just because they are large
- Hide uncertainty when a driver/service-owned path is involved

If the user asks to move a risky system-owned path, support them by explaining the tradeoff and using a safer fallback when possible.
