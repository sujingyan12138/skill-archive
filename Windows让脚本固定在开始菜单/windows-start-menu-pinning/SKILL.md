---
name: windows-start-menu-pinning
description: Use this skill whenever the user wants to make a script, cmd/bat file, PowerShell script, portable app, shortcut, or arbitrary local file appear in Windows Start menu search or become pinnable to Windows 11 Start. It captures the safe wrapper-exe workflow, Start menu shortcut creation, verification steps, and the pitfalls from the HiBit Uninstaller automation incident, including why ConfigureStartPins policy can break the Start menu.
---

# Windows Start Menu Pinning

Use this skill when a user wants to put a nonstandard target, especially a `.cmd`, `.bat`, `.ps1`, portable tool, or custom automation entry, into the Windows Start menu or make it pinnable.

## Core Lesson

Windows 11 often refuses to expose "Pin to Start" for shortcuts that point directly to `.cmd`, `.bat`, or similar script files. A reliable approach is:

1. Create a tiny `.exe` launcher that starts the real target.
2. Create a Start Menu `.lnk` that points to the `.exe`, not to the script.
3. Restart `StartMenuExperienceHost` if AppsFolder still shows stale target metadata.
4. Let the user pin it from Start menu search or AppsFolder.

Do not use `ConfigureStartPins` policy as a casual pinning shortcut. It is a managed-layout policy, not a normal user pin API. Bad JSON or mismatched encodings can make the Start menu stop opening.

## Safe Workflow

1. Verify the target exists.
2. If the target is not already a normal installed app executable, create a wrapper `.exe`.
3. Put the wrapper and its small metadata file in a stable folder beside the target, for example `StartLaunchers\`.
4. Create a Start Menu shortcut under:
   - Current user: `[Environment]::GetFolderPath('Programs')`
   - Fallback: `C:\Users\<user>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs`
5. Point the shortcut to the wrapper `.exe`.
6. Set `WorkingDirectory` to the wrapper folder.
7. Set `IconLocation` to a relevant app `.exe` or `.ico`.
8. Restart `StartMenuExperienceHost` if the AppsFolder cache still shows an old target.
9. Verify with `shell:AppsFolder` that the item exposes a pin verb.

## Use the Bundled Script

Prefer the bundled script for repeatability:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\create-pinnable-start-shortcut.ps1 `
  -TargetPath "D:\Tools\My Script.cmd" `
  -DisplayName "My Script" `
  -ShortcutFolderName "My Tools" `
  -IconPath "D:\Tools\MyApp.exe"
```

The script creates:

- `StartLaunchers\<safe-name>.exe`
- `StartLaunchers\<safe-name>.target.txt`
- `%APPDATA%\Microsoft\Windows\Start Menu\Programs\<ShortcutFolderName>\<DisplayName>.lnk`

The `.exe` reads the adjacent `.target.txt` and starts the real file with `UseShellExecute=true`, so it can launch scripts, documents, and executables without quoting issues.

## Verification

Use Shell.Application to inspect the Start menu app item:

```powershell
$shell = New-Object -ComObject Shell.Application
$apps = $shell.Namespace('shell:AppsFolder')
foreach ($app in $apps.Items()) {
  if ($app.Name -like '*My Script*') {
    $app.Path
    $app.Verbs() | ForEach-Object { $_.Name -replace '&','' }
  }
}
```

If the item points to the wrapper `.exe`, the verbs often include:

- Open
- Open file location
- Run as administrator
- Pin to Start / Fixed to Start

If it still points to the old `.cmd`, restart the cache:

```powershell
Get-Process StartMenuExperienceHost -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 3
```

Then query again.

## What Not To Do

Avoid these unless the user explicitly asks for managed Start layout deployment:

- Do not write `HKCU\Software\Policies\Microsoft\Windows\Explorer\ConfigureStartPins`.
- Do not write `ConfigureStartPinsJSON`.
- Do not import or modify `start2.bin` by hand.
- Do not assume `Export-StartLayout` emits valid JSON for every locale; non-ASCII shortcut paths can be exported with malformed escape sequences.
- Do not assume programmatic `Pin to Start` works. Calling the Shell verb with `.DoIt()` can return `E_ACCESSDENIED` even when the verb is visible.

Policy-based pinning can override or break the user's Start layout. If policy values are already present and the user did not ask for policy management, report them and ask before touching them.

## Recovery From Bad Start Policy

If the Start menu stops opening after a pinning attempt:

1. Remove policy values:

```cmd
reg delete HKCU\Software\Policies\Microsoft\Windows\Explorer /v ConfigureStartPins /f
reg delete HKCU\Software\Policies\Microsoft\Windows\Explorer /v ConfigureStartPinsJSON /f
reg delete HKLM\Software\Policies\Microsoft\Windows\Explorer /v ConfigureStartPins /f
reg delete HKLM\Software\Policies\Microsoft\Windows\Explorer /v ConfigureStartPinsJSON /f
```

Ignore "value not found" for keys that were never present.

2. Restart shell components:

```powershell
gpupdate /target:user /force
Get-Process StartMenuExperienceHost,ShellExperienceHost -ErrorAction SilentlyContinue | Stop-Process -Force
Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Start-Process explorer.exe
```

3. If `start2.bin` was backed up before the attempt, restore it:

```powershell
$state = "$env:LOCALAPPDATA\Packages\Microsoft.Windows.StartMenuExperienceHost_cw5n1h2txyewy\LocalState"
Copy-Item "D:\Path\To\start2-backup.bin" (Join-Path $state "start2.bin") -Force
```

If `$env:LOCALAPPDATA` is empty in the automation environment, use the explicit user path.

## Environment Pitfalls

Automation shells can have missing environment variables. Before using Windows shell APIs or npm tools, set or avoid depending on:

```powershell
$env:SystemRoot = 'C:\WINDOWS'
$env:WINDIR = 'C:\WINDOWS'
$env:APPDATA = 'C:\Users\<user>\AppData\Roaming'
$env:LOCALAPPDATA = 'C:\Users\<user>\AppData\Local'
```

Prefer `[Environment]::GetFolderPath('Programs')` for the Start Menu Programs folder, with an explicit fallback if it returns empty.

## Quoting Rules For Elevated Cmd Entrypoints

For `.cmd` files that request elevation, avoid hand-building a `cmd.exe /k "path with spaces"` command. Use the current script path:

```cmd
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -ArgumentList '--elevated' -Verb RunAs"
```

Inside scripts, use:

```cmd
set "SCRIPT=%~dp0SomeScript.ps1"
```

This avoids paths like `D:\Edge\HiBit Uninstaller` being split into `D:\Edge\HiBit`.

## When The User Wants Fully Automatic Pinning

Be direct: Windows 11 does not expose a stable supported per-user API for arbitrary programmatic pinning. The safe deliverable is a Start menu searchable item that exposes the pin option. Ask the user to right-click and pin manually.

If they insist on policy-based pinning, first explain:

- It is a managed layout policy.
- It can override or damage the current Start layout.
- It needs backups and a recovery script.
- It should be tested on a disposable account first.

Then proceed only with explicit confirmation.
