param(
  [string]$SourcePath,
  [string]$SkillName,
  [string]$Category,
  [string]$ArchiveRoot = "D:\PyCharm\CODE\SKILL",
  [switch]$AllMatches,
  [switch]$Push,
  [switch]$DryRun,
  [string]$CommitMessage
)

$ErrorActionPreference = "Stop"

function Resolve-FullPath {
  param([string]$Path)
  return $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path)
}

function Assert-SkillSource {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
    throw "SourcePath does not exist: $Path"
  }
  $skillFile = Join-Path $Path "SKILL.md"
  if (-not (Test-Path -LiteralPath $skillFile -PathType Leaf)) {
    throw "SourcePath is not a skill directory because SKILL.md is missing: $Path"
  }
}

function Get-RelativeGitPath {
  param([string]$Root, [string]$Path)
  $rootFull = (Resolve-Path -LiteralPath $Root).Path
  $pathFull = (Resolve-Path -LiteralPath $Path).Path
  return ([System.IO.Path]::GetRelativePath($rootFull, $pathFull)).Replace("\", "/")
}

function Test-Excluded {
  param([System.IO.FileSystemInfo]$Item)
  $parts = $Item.FullName -split '[\\/]'
  $excludedDirs = @(".git", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv")
  foreach ($part in $parts) {
    if ($excludedDirs -contains $part) { return $true }
  }
  $name = $Item.Name
  if ($name -eq ".DS_Store") { return $true }
  if ($name -like "*.pyc") { return $true }
  if ($name -like "*.pyo") { return $true }
  return $false
}

function Copy-SkillArchive {
  param([string]$Source, [string]$Destination)

  $sourceFull = (Resolve-Path -LiteralPath $Source).Path
  if (-not (Test-Path -LiteralPath $Destination -PathType Container)) {
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
  }

  Get-ChildItem -LiteralPath $sourceFull -Recurse -Force | Where-Object { -not (Test-Excluded -Item $_) } | ForEach-Object {
    $relative = [System.IO.Path]::GetRelativePath($sourceFull, $_.FullName)
    $target = Join-Path $Destination $relative
    if ($_.PSIsContainer) {
      New-Item -ItemType Directory -Force -Path $target | Out-Null
    } else {
      $parent = Split-Path -Parent $target
      New-Item -ItemType Directory -Force -Path $parent | Out-Null
      Copy-Item -LiteralPath $_.FullName -Destination $target -Force
    }
  }
}

function Find-ArchivedSkillTargets {
  param([string]$Root, [string]$Name, [string]$CategoryName)

  $searchRoot = $Root
  if ($CategoryName) {
    $candidate = Join-Path $Root $CategoryName
    if (Test-Path -LiteralPath $candidate -PathType Container) {
      $searchRoot = $candidate
    }
  }

  if (-not (Test-Path -LiteralPath $searchRoot -PathType Container)) {
    return @()
  }

  $matches = Get-ChildItem -LiteralPath $searchRoot -Recurse -Filter "SKILL.md" -File |
    Where-Object { $_.Directory.Name -eq $Name } |
    ForEach-Object { $_.Directory.FullName }

  return @($matches | Sort-Object -Unique)
}

function Invoke-Git {
  param([string[]]$GitArgs)
  & git -C $ArchiveRoot @GitArgs
  if ($LASTEXITCODE -ne 0) {
    throw "git $($GitArgs -join ' ') failed with exit code $LASTEXITCODE"
  }
}

$ArchiveRoot = Resolve-FullPath -Path $ArchiveRoot
if (-not (Test-Path -LiteralPath $ArchiveRoot -PathType Container)) {
  throw "ArchiveRoot does not exist: $ArchiveRoot"
}

if ($SourcePath) {
  $SourcePath = Resolve-FullPath -Path $SourcePath
  Assert-SkillSource -Path $SourcePath
  if (-not $SkillName) {
    $SkillName = Split-Path -Leaf $SourcePath
  }
}

if (-not $SkillName) {
  throw "Pass -SourcePath or -SkillName."
}

Write-Host "ARCHIVE_ROOT $ArchiveRoot"
Write-Host "SKILL_NAME $SkillName"
if ($SourcePath) { Write-Host "SOURCE $SourcePath" }

$statusBefore = & git -C $ArchiveRoot status --short
Write-Host "STATUS_BEFORE"
if ($statusBefore) { $statusBefore | ForEach-Object { Write-Host $_ } } else { Write-Host "(clean)" }

$targets = Find-ArchivedSkillTargets -Root $ArchiveRoot -Name $SkillName -CategoryName $Category

if ($targets.Count -eq 0) {
  if (-not $Category) {
    $Category = "未分类"
  }
  $targets = @((Join-Path (Join-Path $ArchiveRoot $Category) $SkillName))
  Write-Host "TARGET_MODE create"
} else {
  Write-Host "TARGET_MODE update"
}

if ($Category -and $targets.Count -gt 1) {
  $categoryRoot = Join-Path $ArchiveRoot $Category
  $categoryRootFull = Resolve-FullPath -Path $categoryRoot
  $targets = @($targets | Where-Object { $_.StartsWith($categoryRootFull, [System.StringComparison]::OrdinalIgnoreCase) })
}

if ($targets.Count -gt 1 -and -not $AllMatches -and -not $Category) {
  Write-Host "MULTIPLE_TARGETS defaulting to all matches"
}

$targets = @($targets | Sort-Object -Unique)
Write-Host "TARGETS"
$targets | ForEach-Object { Write-Host $_ }

if ($DryRun) {
  Write-Host "DRY_RUN no files copied"
  exit 0
}

if (-not $SourcePath) {
  throw "SourcePath is required unless running -DryRun."
}

foreach ($target in $targets) {
  Copy-SkillArchive -Source $SourcePath -Destination $target
  Write-Host "SYNCED $target"
}

$relativeTargets = @()
foreach ($target in $targets) {
  $relativeTargets += Get-RelativeGitPath -Root $ArchiveRoot -Path $target
}

$statusAfterCopy = & git -C $ArchiveRoot status --short -- @relativeTargets
Write-Host "STATUS_TARGETS"
if ($statusAfterCopy) { $statusAfterCopy | ForEach-Object { Write-Host $_ } } else { Write-Host "(no changes)" }

if (-not $Push) {
  Write-Host "DONE copied without commit/push because -Push was not set"
  exit 0
}

if (-not $statusAfterCopy) {
  Write-Host "NO_CHANGES"
  exit 0
}

Invoke-Git -GitArgs (@("add", "--") + $relativeTargets)

if (-not $CommitMessage) {
  $CommitMessage = "archive skill: $SkillName"
}

Invoke-Git -GitArgs @("commit", "-m", $CommitMessage)
$commitHash = (& git -C $ArchiveRoot rev-parse --short HEAD).Trim()
Write-Host "COMMIT $commitHash"

& git -C $ArchiveRoot push
if ($LASTEXITCODE -ne 0) {
  Write-Host "PUSH_FAILED retrying with proxy"
  $env:HTTP_PROXY = "http://127.0.0.1:10808"
  $env:HTTPS_PROXY = "http://127.0.0.1:10808"
  & git -C $ArchiveRoot push
  if ($LASTEXITCODE -ne 0) {
    throw "git push failed after proxy retry with exit code $LASTEXITCODE"
  }
}

Write-Host "PUSH_OK $commitHash"
