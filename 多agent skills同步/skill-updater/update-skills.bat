@echo off
rem ---------------------------------------------------------------
rem  skill-updater launcher
rem  Usage:
rem    update-skills.bat                      -> check skills AND claude plugins (read only)
rem    update-skills.bat update --dry-run     -> preview what would change
rem    update-skills.bat update --yes         -> apply updates (auto backup)
rem    update-skills.bat plugin-update --yes  -> only claude plugins
rem    update-skills.bat mirrors              -> are the agent skill folders in sync?
rem    update-skills.bat doctor               -> lint SKILL.md frontmatter
rem    update-skills.bat list                 -> show source manifest
rem ---------------------------------------------------------------
chcp 65001 >nul
cd /d "%~dp0"

if not exist "scripts\skill_update.py" (
  echo [ERROR] scripts\skill_update.py not found next to this file.
  pause
  exit /b 1
)

set "PYEXE=C:\Users\Chen\.workbuddy\binaries\python\versions\3.13.12\python.exe"
if not exist "%PYEXE%" set "PYEXE=python"

if "%~1"=="" (
  "%PYEXE%" scripts\skill_update.py check
  echo.
  echo ---------------------------------------------------------------
  echo  To apply updates, run:
  echo    update-skills.bat update --dry-run
  echo    update-skills.bat update --yes
  echo ---------------------------------------------------------------
) else (
  "%PYEXE%" scripts\skill_update.py %*
)

echo.
pause
