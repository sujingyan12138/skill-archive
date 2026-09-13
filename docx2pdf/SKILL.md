---
name: docx2pdf
description: Convert Word documents (.docx/.doc) to PDF on Windows using local MS Word via COM automation, with zero-loss formatting fidelity. Use this skill whenever the user asks to convert a Word document (or a folder of documents) to PDF, export a resume/report as PDF, or batch-convert docx files. Triggers include "转成pdf", "导出pdf", "convert to pdf", and any docx-to-PDF request.
agent_created: true
---

# docx2pdf

## Overview

Convert one or more Word documents (.docx/.doc) to PDF on Windows by driving the locally installed MS Word through COM automation (`Word.Application` → `Documents.Open` → `SaveAs2(path, 17)`). Because the conversion engine is Word itself, fonts, pagination, images, and layout are identical to what the user sees in Word — no online service, no extra software, no font-substitution risk.

## When to Use

- User asks to convert a .docx/.doc file (or several) to PDF.
- User asks to batch-convert all Word documents in a folder.
- User asks for a PDF version of a resume, report, or any document originally in Word format.

**Do NOT use this skill for:**

- PDF → docx (or any conversion *into* Word format).
- Content editing of the docx (that belongs to `tencent-docs-routing` / local office edit skills). Pure docx→pdf format conversion does NOT need `tencent-docs-routing`.
- Machines without MS Word installed (see Troubleshooting).

## Critical Environment Constraints (all empirically tested 2026-09-13)

Inside the agent's PowerShell tool, the sandbox silently kills a command (exit code 1, no output, no error, subsequent statements never run) when it contains any of:

1. **`Join-Path`** — the single most surprising one. Build paths with string interpolation (`"$outDir\$($f.BaseName).pdf"`) or `[System.IO.Path]::ChangeExtension()` instead.
2. **Executing .ps1 script files** (`& C:\...\convert.ps1` or `-File ...`) — dies at the invocation point.
3. **Spawning powershell.exe child processes** (bare `powershell` is also not on PATH).

What DOES work inline (all verified): `New-Object -ComObject Word.Application` (full Word COM automation), `Get-ChildItem` / `Where-Object` / regex matching, try/catch/finally, foreach, Chinese paths, `New-Item -ItemType Directory -Force`, writing to any directory.

Side effect of a killed command: it may leave an invisible zombie `WINWORD.EXE` behind (the script never reaches `$word.Quit()`). Before/after failed runs, check with `Get-Process WINWORD` via the Bash tool (`tasklist | grep -i winword`) and kill ONLY title-less instances: `Get-Process WINWORD | Where-Object { -not $_.MainWindowTitle } | Stop-Process -Force` (never kill instances with a window title — those are the user's editing sessions).

Therefore: **always use the inline snippets below in the PowerShell tool**. The bundled `scripts/convert.ps1` is only for the user's manual use in a real console outside the sandbox.

## Primary Workflow (agent, inline snippet)

Single file — PDF next to the source (default behavior users usually want):

```powershell
$src = "C:\path\to\简历.docx"
$dst = [System.IO.Path]::ChangeExtension($src, ".pdf")
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($src, $false, $true)
    $doc.SaveAs2($dst, 17)   # 17 = wdFormatPDF
    $doc.Close($false)
} finally {
    $word.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
}
```

Multiple files or a whole directory (each PDF next to its source):

```powershell
$files = Get-ChildItem -Path "C:\some\dir" -File | Where-Object { $_.Name -notlike '~$*' -and $_.Extension -match '^\.(docx|doc)$' }
# or: $files = @("C:\a.docx", "C:\b.docx")
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$ok = 0; $fail = 0
try {
    foreach ($f in $files) {
        $dst = [System.IO.Path]::ChangeExtension($f.FullName, ".pdf")
        try {
            $doc = $word.Documents.Open($f.FullName, $false, $true)
            $doc.SaveAs2($dst, 17)
            $doc.Close($false)
            $ok++
        } catch { $fail++ }
    }
} finally {
    $word.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
}
"Done. OK=$ok FAIL=$fail"
```

Custom output directory — build `$dst` with string interpolation (NEVER `Join-Path`, see constraints above) and create the directory first:

```powershell
$outDir = "D:\some\out"
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
# inside the foreach:
$dst = "$outDir\$($f.BaseName).pdf"
```

Key constants: `SaveAs2` format `17` = PDF; `Documents.Open($src, $false, $true)` opens read-only without conversion prompts. Overwrite of an existing PDF is automatic.

## Workflow Steps

1. Confirm source path(s) exist; if the user named a folder, expand it (non-recursive, skip `~$` lock files).
2. Run the inline snippet above in the PowerShell tool with the actual paths. Non-ASCII (Chinese) paths are safe in inline commands.
3. **Verify** (the PowerShell tool's stdout is often NOT displayed — do not rely on it): list the output location with the Bash tool (`ls -la <dir>`) and confirm each PDF exists with a fresh timestamp and plausible size. If in doubt, check the file starts with `%PDF-` (e.g. `head -c 8 file.pdf`).
4. Present the resulting PDF(s) with the file presentation tool.

## Manual Console Script (for the user, outside the agent)

`scripts/convert.ps1` wraps the same logic for direct console use:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Chen\.workbuddy\skills\docx2pdf\scripts\convert.ps1" "D:\docs\a.docx" "D:\docs\*.docx" [-OutputDir "D:\out"]
```

Accepts files, directories (non-recursive), or globs; prints one `OK:`/`FAIL:` line per file; exit code 0 on full success. Never invoke it from the agent's PowerShell tool (sandbox blocks it — see constraints above).

## Troubleshooting

- **`New-Object -ComObject Word.Application` fails**: MS Word missing or COM blocked. Fallbacks: (a) check for LibreOffice (`soffice --headless --convert-to pdf --outdir <dir> <file>` via the Bash tool); (b) tell the user MS Word is needed for lossless conversion.
- **A document is open in Word on the user's desktop**: read-only open still works; if it fails, ask the user to close the document and retry.
- **Command dies silently / exit code 1 with no output**: the sandbox blocked a construct used — most often `Join-Path`, .ps1 file invocation, or child process spawning. Replace `Join-Path` with string interpolation and keep everything inline (see constraints above). A killed command may also leave a zombie WINWORD.EXE — clean it up (title-less instances only).
- **Future edits to convert.ps1**: keep it ASCII-only. PowerShell 5.1 misreads UTF-8-without-BOM .ps1 files and garbles non-ASCII text. Non-ASCII belongs in runtime arguments, not in the file.
