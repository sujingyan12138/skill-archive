---
name: docx2pdf
description: Convert Word documents (.docx/.doc/.docm) to PDF on Windows using local MS Word via COM automation, with zero-loss formatting fidelity. Use this skill whenever the user asks to convert a Word document (or a folder of documents) to PDF, export a resume/report as PDF, or batch-convert docx files. Triggers include "转成pdf", "导出pdf", "convert to pdf", and any docx-to-PDF request.
agent_created: true
---

# docx2pdf

## Overview

Convert one or more Word documents to PDF on Windows by driving the locally installed MS Word through COM automation (`Word.Application` → `Documents.Open` → `SaveAs2(path, 17)`). Because the conversion engine is Word itself, fonts, pagination, images, and layout are identical to what the user sees in Word — no online service, no extra software, no font-substitution risk.

The conversion logic lives in a **tested script**: `scripts/convert.ps1`. Invoke that script; do not paste inline conversion code.

## When to Use

- User asks to convert a .docx/.doc/.docm file (or several) to PDF.
- User asks to batch-convert all Word documents in a folder.
- User asks for a PDF version of a resume, report, or any document originally in Word format.

**Do NOT use this skill for:**

- PDF → docx (or any conversion *into* Word format).
- Content editing of the docx (that belongs to `tencent-docs-routing` / local office edit skills). Pure docx→pdf format conversion does NOT need `tencent-docs-routing`.
- Machines without MS Word installed (see Troubleshooting).

## Primary Workflow (agent) — invoke the script

```powershell
& "C:\Users\Chen\.workbuddy\skills\docx2pdf\scripts\convert.ps1" "<source-path>"
```

That single line converts the file and writes the PDF **next to the source** (the behavior users usually want). Variants:

```powershell
# several files
& "...\convert.ps1" "D:\a\1.docx" "D:\b\2.docx"

# a whole folder (non-recursive) or a glob
& "...\convert.ps1" "D:\docs"
& "...\convert.ps1" "D:\docs\*.docx"

# custom output directory
& "...\convert.ps1" "D:\docs\*.docx" -OutputDir "D:\out"
```

Script behavior: `.docx` / `.docm` / `.doc`; PDFs next to source by default, into `-OutputDir` if given (created if missing); existing PDFs overwritten; Word lock files (`~$...`) and non-Word files skipped; nonexistent inputs reported and skipped. Status is printed as `OK:` / `FAIL:` lines plus `Done. OK=x FAIL=y`, and `$script:ConvertResult` is `'success'` or `'error'`.

### Verify (required — the PowerShell tool does not display stdout)

List the output location with the Bash tool and confirm each PDF exists with a fresh mtime and plausible size:

```bash
stat -c '%y %n' "<output-dir>"/*
```

Then present the PDF(s) with the file presentation tool. If a run produced no PDF, check for a zombie Word process (see below) and re-run.

## Critical Environment Constraints (all empirically tested 2026-09-13)

1. **The literal token for PowerShell's path-joining cmdlet (the one that combines a directory and a child name) must NEVER appear in a command or in code the agent executes.** The sandbox silently kills any command whose executed code contains it: exit code 1, no output, no error message, subsequent statements never run. In `convert.ps1` the token does not appear anywhere — not even in comments — and paths are built with string interpolation (`"$OutputDir\$base.pdf"`). Keep it that way. This single rule caused every mysterious failure during development.
2. **`cmd.exe` cannot be launched from the PowerShell tool** (hard policy, unaffected by the sandbox flag) — so the agent cannot run `convert.bat`; that file is for the user only.
3. **Bare `powershell` is not on PATH** — do not try to spawn a child `powershell.exe`.
4. Inline Word COM automation works fine; the script uses the same calls that were verified inline.

**Zombie processes:** if a conversion run is killed mid-flight, it can leave an invisible `WINWORD.EXE` behind (the script never reaches `$word.Quit()`). Check with `tasklist | grep -i winword` (Bash tool) and clean up only title-less instances:

```powershell
Get-Process WINWORD | Where-Object { -not $_.MainWindowTitle } | Stop-Process -Force
```

Never kill a WINWORD with a window title — that is the user's own editing session with unsaved work.

## Manual Use by the User (outside the agent)

- **Drag & drop**: drop Word files or a folder onto `scripts\convert.bat` — PDFs appear next to each source file. (Verified by inspection only: the agent's environment blocks cmd.exe, so this wrapper could not be executed during development. The `convert.ps1` it calls is fully tested.)
- **Console**: `powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Chen\.workbuddy\skills\docx2pdf\scripts\convert.ps1" "D:\docs\a.docx" [-OutputDir "D:\out"]`

## Troubleshooting

- **`New-Object -ComObject Word.Application` fails**: MS Word missing or COM blocked. Fallbacks: (a) check for LibreOffice (`soffice --headless --convert-to pdf --outdir <dir> <file>` via the Bash tool); (b) tell the user MS Word is needed for lossless conversion.
- **A document is open in Word on the user's desktop**: read-only open still works; if it fails, ask the user to close the document and retry.
- **Command dies silently / exit code 1 with no output**: a blocked token (constraint 1) or blocked program (constraint 2) is in the command. Remove it and retry; then check for and kill zombie WINWORD processes.
- **Script reports FAIL for a file**: the message after `--` carries Word's error (often a corrupted or password-protected file).
- **Editing `convert.ps1`**: keep it ASCII-only (PowerShell 5.1 misreads UTF-8-without-BOM .ps1 files and garbles non-ASCII text) and keep the forbidden token out of it, comments included.
