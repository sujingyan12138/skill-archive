param(
    [Parameter(Mandatory = $true)]
    [string]$TargetPath,

    [Parameter(Mandatory = $true)]
    [string]$DisplayName,

    [string]$ShortcutFolderName = "Custom Tools",
    [string]$IconPath,
    [string]$LauncherRoot
)

$ErrorActionPreference = "Stop"
$env:SystemRoot = if ($env:SystemRoot) { $env:SystemRoot } else { "C:\WINDOWS" }
$env:WINDIR = if ($env:WINDIR) { $env:WINDIR } else { "C:\WINDOWS" }

if (-not (Test-Path -LiteralPath $TargetPath)) {
    throw "Target does not exist: $TargetPath"
}

$targetFullPath = [IO.Path]::GetFullPath($TargetPath)
$targetDir = Split-Path -Parent $targetFullPath
if (-not $LauncherRoot) {
    $LauncherRoot = Join-Path $targetDir "StartLaunchers"
}
New-Item -ItemType Directory -Path $LauncherRoot -Force | Out-Null

$safeName = ($DisplayName -replace '[^\p{L}\p{Nd}\._-]+', '-').Trim('-')
if ([string]::IsNullOrWhiteSpace($safeName)) {
    $safeName = "PinnedLauncher"
}

$exePath = Join-Path $LauncherRoot ($safeName + ".exe")
$targetFile = Join-Path $LauncherRoot ($safeName + ".target.txt")
$sourcePath = Join-Path $LauncherRoot "PinnedLauncherSource.cs"

Set-Content -LiteralPath $targetFile -Value $targetFullPath -Encoding UTF8

$source = @'
using System;
using System.Diagnostics;
using System.IO;

public class PinnedLauncher
{
    [STAThread]
    public static int Main(string[] args)
    {
        string exePath = Process.GetCurrentProcess().MainModule.FileName;
        string targetPathFile = Path.Combine(
            AppDomain.CurrentDomain.BaseDirectory,
            Path.GetFileNameWithoutExtension(exePath) + ".target.txt"
        );
        if (!File.Exists(targetPathFile))
            return 2;

        string target = File.ReadAllText(targetPathFile).Trim();
        if (!File.Exists(target) && !Directory.Exists(target))
            return 3;

        ProcessStartInfo psi = new ProcessStartInfo();
        psi.FileName = target;
        psi.WorkingDirectory = Directory.Exists(target) ? target : Path.GetDirectoryName(target);
        psi.UseShellExecute = true;
        Process.Start(psi);
        return 0;
    }
}
'@

Set-Content -LiteralPath $sourcePath -Value $source -Encoding UTF8

$compiler = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (-not (Test-Path -LiteralPath $compiler)) {
    $compiler = Join-Path $env:WINDIR "Microsoft.NET\Framework\v4.0.30319\csc.exe"
}
if (-not (Test-Path -LiteralPath $compiler)) {
    throw "csc.exe was not found under $env:WINDIR\Microsoft.NET"
}

& $compiler /nologo /target:winexe /out:$exePath $sourcePath
if ($LASTEXITCODE -ne 0) {
    throw "Failed to compile launcher."
}

$programs = [Environment]::GetFolderPath("Programs")
if ([string]::IsNullOrWhiteSpace($programs)) {
    $programs = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
}
if ([string]::IsNullOrWhiteSpace($programs)) {
    throw "Cannot resolve Start Menu Programs folder. Set APPDATA or pass a normal user environment."
}

$shortcutDir = Join-Path $programs $ShortcutFolderName
New-Item -ItemType Directory -Path $shortcutDir -Force | Out-Null

$shortcutPath = Join-Path $shortcutDir ($DisplayName + ".lnk")
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $exePath
$shortcut.WorkingDirectory = $LauncherRoot
if ($IconPath -and (Test-Path -LiteralPath $IconPath)) {
    $shortcut.IconLocation = "$IconPath,0"
} else {
    $shortcut.IconLocation = "$exePath,0"
}
$shortcut.Description = $DisplayName
$shortcut.Save()

Get-Process StartMenuExperienceHost -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

[pscustomobject]@{
    Launcher = $exePath
    TargetFile = $targetFile
    Shortcut = $shortcutPath
}
