# Windows Folder Guide

## Purpose

Use this reference when you need more detailed guidance than the main skill body: folder triage, risk classification, migration checklists, and reusable command templates.

## Folder Triage Matrix

### Usually good migration candidates

These are often worth moving if they are large and the app tolerates the original path being a junction:

- `C:\Users\<user>\AppData\Local\Google`
- `C:\Users\<user>\AppData\Local\Microsoft\Edge`
- `C:\Users\<user>\AppData\Roaming\Tencent\...`
- `C:\Users\<user>\AppData\Roaming\PotPlayerMini64`
- User-profile model folders
- Cache-heavy app data under `AppData\Local`
- Playlists, browser profiles, plugin caches, non-system media caches

Typical reason they are good candidates:

- They are large
- They are user data, not system binaries
- Apps usually keep working if the original path becomes a junction

### Caution candidates

Inspect carefully and explain tradeoffs:

- `ProgramData\...`
- Shared app data used by services
- Launchers, anti-cheat caches, updater directories
- GPU/AI runtimes with background services
- Some database or local-server data folders

These are not automatic "no", but they need stronger process checks and clearer rollback plans.

### High-risk candidates

Avoid migrating unless the user explicitly understands the risk and the path has been carefully verified:

- `C:\Windows\...`
- `C:\Program Files\...`
- `C:\Program Files (x86)\...`
- Driver-owned folders
- Service-owned folders that remain locked after user-space processes are stopped
- Folders needed before user logon or very early in boot

## Link Choice

### Default: `mklink /J`

Prefer:

```cmd
mklink /J "C:\original\path" "E:\target\path"
```

Why:

- Better app compatibility on Windows
- Better compatibility with older tools
- Often safer for browsers, chat apps, and desktop software

### Use `mklink /D` only when justified

Only switch to:

```cmd
mklink /D "C:\original\path" "E:\target\path"
```

when the exact symbolic-link semantics are required and the compatibility risk is acceptable.

## Standard Migration Checklist

### Before migration

1. Confirm source path exists.
2. Confirm target drive/path exists or can be created.
3. Measure folder size if useful.
4. Check whether the app is running.
5. Check whether the path is already a `Junction` or symlink.
6. Check whether a `.old` backup already exists.

### During migration

1. Stop the app if needed.
2. Copy with `robocopy`.
3. Rename the source to `.old`.
4. Create the junction at the original path.
5. Verify the new path points where expected.

### After migration

1. Launch the app or ask the user to validate.
2. Confirm core data is still visible.
3. Keep `.old` until validation is complete.
4. Delete `.old` only after confirmation.

## Command Templates

### Inspect a folder

```powershell
Get-Item -LiteralPath 'C:\path\to\folder' | Format-List FullName,Attributes,LinkType
Get-ChildItem -Force -LiteralPath 'C:\path\to\folder' | Select-Object Name,LastWriteTime | Format-Table -AutoSize
(Get-ChildItem -Force -LiteralPath 'C:\path\to\folder' -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
```

### Find likely owning processes

```powershell
Get-Process | Where-Object { $_.ProcessName -match 'chrome|msedge|WeChat|PotPlayer|NVIDIA' } | Select-Object ProcessName,Id,Path | Format-Table -AutoSize
```

Adjust the process pattern to the folder owner.

### Copy to destination

```powershell
robocopy 'C:\source' 'E:\target' /E /COPY:DAT /DCOPY:DAT /R:1 /W:1 /XJ
```

### Rename original to backup

```powershell
Rename-Item -LiteralPath 'C:\source' -NewName 'source.old'
```

### Create junction

```cmd
mklink /J "C:\source" "E:\target"
```

### Verify junction

```powershell
Get-Item -LiteralPath 'C:\source' | Format-List FullName,Attributes,LinkType,Target
```

### Remove backup after validation

```powershell
Remove-Item -LiteralPath 'C:\source.old' -Recurse -Force
```

## Handling Occupied Folders

### If the app is still running

- Stop normal user processes first.
- Retry the rename.
- If rename now works, continue.

### If files are still locked by services or system containers

- Explain that the path is not fully free yet.
- Check whether the session is elevated.
- If needed, recommend admin terminal or Safe Mode.

### If only cache files remain locked

Make the distinction explicit:

- If the locked files are disposable cache, the user may choose to leave that folder for later cleanup.
- If the locked files are active state, do not claim the migration is complete.

## Reusable Judgments from Prior Successes

These patterns worked well:

- Browsers: move the whole user-data parent folder and use `Junction`
- Chat apps: move the app data directory, keep `.old` until the user checks history/login
- Media tools: move config/model/playlist folders together rather than selectively

These patterns were problematic:

- Driver/runtime folders with active service ownership
- Directories still in use by privileged background processes

## Recommended Summary Format After Each Migration

When finishing a migration, summarize:

1. Which path was moved
2. Which target path now holds the real data
3. Which link type was used
4. Whether the app was verified
5. Whether `.old` still exists or was removed
