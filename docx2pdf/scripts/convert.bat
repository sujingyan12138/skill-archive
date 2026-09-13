@echo off
setlocal
if "%~1"=="" (
    echo docx2pdf - convert Word documents .docx/.doc to PDF
    echo.
    echo Usage:
    echo   1. Drag and drop Word files onto this file, or
    echo   2. convert.bat "C:\docs\a.docx" ["C:\docs\*.docx" ...] [-OutputDir "C:\out"]
    echo      or drop a folder onto this file to convert every .docx inside it.
    echo.
    echo PDFs are written next to each source file unless -OutputDir is given.
    echo.
    pause
    exit /b 1
)
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0convert.ps1" %*
echo.
pause
