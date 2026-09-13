# docx2pdf: Convert Word documents to PDF using Word COM automation.
#
# Requires: Windows + installed MS Word (any recent version).
#
# IMPORTANT - invocation style:
#   This script is for MANUAL use in a real PowerShell console (outside the
#   WorkBuddy agent sandbox). In the agent's PowerShell tool, executing .ps1
#   files via `&` or spawning powershell.exe children is BLOCKED by the
#   sandbox - there, use the inline snippet documented in SKILL.md instead.
#
#   Manual console usage:
#     powershell -NoProfile -ExecutionPolicy Bypass -File convert.ps1 <path> [-OutputDir <dir>]
#
#   Each <path> can be:
#     - a .docx or .doc file
#     - a directory (converts all .docx/.doc directly inside it, non-recursive)
#     - a glob pattern (e.g. "D:\docs\*.docx")
#
# Output:
#   - By default, each PDF is written next to its source file (same name, .pdf extension).
#   - If -OutputDir is given, all PDFs go into that directory (created if missing).
#   - Existing PDFs are overwritten.
#
# Notes:
#   - This script NEVER calls `exit`/`throw` at top level on purpose: when invoked
#     in-process, `exit` would terminate the whole agent PowerShell session.
#     Status is reported via output lines ("OK:", "FAIL:", "Done. OK=x FAIL=y")
#     plus $script:ConvertResult ('success' | 'error'). Redirect output to a log
#     file and read it back if stdout is not visible.
#   - Keep this file ASCII-only: PowerShell 5.1 misreads UTF-8 .ps1 files without
#     BOM, which would garble non-ASCII comments. Paths with non-ASCII characters
#     (e.g. Chinese) are safe when passed as arguments at runtime.
#   - Word lock files (~$xxx.docx) are skipped automatically.

param(
    [Parameter(Mandatory = $true, Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$Paths,
    [string]$OutputDir = ""
)

$script:ConvertResult = 'error'

# ---- Collect source files ----
$files = New-Object System.Collections.Generic.List[string]
foreach ($p in $Paths) {
    if (Test-Path $p -PathType Container) {
        Get-ChildItem -Path $p -File |
            Where-Object { $_.Name -notlike '~$*' -and $_.Extension -match '^\.(docx|doc)$' } |
            ForEach-Object { $files.Add($_.FullName) }
    }
    elseif (Test-Path $p -PathType Leaf) {
        $files.Add((Resolve-Path -Path $p).Path)
    }
    elseif ($p -match '[*?]') {
        Get-ChildItem -Path $p -File -ErrorAction SilentlyContinue |
            ForEach-Object { $files.Add($_.FullName) }
    }
    else {
        Write-Output "SKIP (not found): $p"
    }
}

if ($files.Count -eq 0) {
    Write-Output "ERROR: no source files found."
    return
}

if ($OutputDir -and -not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

# ---- Convert via Word COM ----
$word = $null
$ok = 0
$fail = 0
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0   # wdAlertsNone

    foreach ($src in $files) {
        if ($OutputDir) {
            $dst = Join-Path $OutputDir ([System.IO.Path]::GetFileNameWithoutExtension($src) + '.pdf')
        }
        else {
            $dst = [System.IO.Path]::ChangeExtension($src, '.pdf')
        }
        try {
            $doc = $word.Documents.Open($src, $false, $true)  # confirmConversions=false, readOnly=true
            $doc.SaveAs2($dst, 17)                             # 17 = wdFormatPDF
            $doc.Close($false)
            $ok++
            Write-Output "OK: $dst"
        }
        catch {
            $fail++
            Write-Output "FAIL: $src -- $($_.Exception.Message)"
        }
    }
}
catch {
    Write-Output "FATAL: $($_.Exception.Message)"
}
finally {
    if ($word) {
        $word.Quit()
        [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
    }
}

Write-Output "Done. OK=$ok FAIL=$fail"
if ($fail -eq 0 -and $ok -gt 0) { $script:ConvertResult = 'success' }
