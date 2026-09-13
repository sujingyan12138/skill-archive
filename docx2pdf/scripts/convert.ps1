# docx2pdf: Convert Word documents to PDF using Word COM automation.
#
# Requires: Windows + installed MS Word (any recent version).
#
# IMPORTANT - invocation style:
#   Works both in a real PowerShell console AND inside the WorkBuddy agent's
#   PowerShell tool (via `& "C:\...\convert.ps1" <path> ...`).
#
#   Manual console usage:
#     powershell -NoProfile -ExecutionPolicy Bypass -File convert.ps1 <path> [-OutputDir <dir>]
#   Or simply drag Word files onto convert.bat (next to this file).
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
#   - NEVER use PowerShell's built-in path-joining cmdlet (the one that combines
#     a directory and a child name) inside this script, and never put its exact
#     name in this file: the agent's sandbox silently kills any command whose
#     executed code contains that token (verified 2026-09-13: the command dies
#     right at that statement, leaving a zombie WINWORD.EXE). Build paths with
#     string interpolation ("$dir\$name.pdf") instead. The path-resolving cmdlet
#     (the one that turns a relative path into an absolute one) is avoided for
#     the same reason.
#   - This script NEVER calls `exit`/`throw` at top level on purpose: when
#     invoked in-process, `exit` would terminate the whole agent PowerShell session.
#     Status is reported via output lines ("OK:", "FAIL:", "Done. OK=x FAIL=y")
#     plus $script:ConvertResult ('success' | 'error').
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
    # Wildcard check MUST come first: Test-Path returns True for patterns like
    # "C:\dir\*.docx" (it matches existing items), so a later wildcard branch
    # would be unreachable and the raw pattern would be handed to Word.
    if ($p -match '[*?]') {
        Get-ChildItem -Path $p -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -notlike '~$*' -and $_.Extension -match '^\.(docx|docm|doc)$' } |
            ForEach-Object { $files.Add($_.FullName) }
    }
    elseif (Test-Path $p -PathType Container) {
        Get-ChildItem -Path $p -File |
            Where-Object { $_.Name -notlike '~$*' -and $_.Extension -match '^\.(docx|docm|doc)$' } |
            ForEach-Object { $files.Add($_.FullName) }
    }
    elseif (Test-Path $p -PathType Leaf) {
        $files.Add($p)
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
            $base = [System.IO.Path]::GetFileNameWithoutExtension($src)
            $dst = "$OutputDir\$base.pdf"
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
