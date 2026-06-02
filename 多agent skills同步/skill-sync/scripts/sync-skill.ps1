param(
  [Parameter(Mandatory=$true)]
  [string]$SkillName,

  [string]$RepoRoot,

  [string]$SourcePath,

  [switch]$Package,

  [string]$PackagePath,

  [switch]$Global
)

$ErrorActionPreference = "Stop"

function Resolve-RepoRoot {
  param([string]$Start)
  $dir = (Resolve-Path -LiteralPath $Start).Path
  while ($dir) {
    if ((Test-Path -LiteralPath (Join-Path $dir ".codex")) -or
        (Test-Path -LiteralPath (Join-Path $dir ".claude")) -or
        (Test-Path -LiteralPath (Join-Path $dir ".agents"))) {
      return $dir
    }
    $parent = Split-Path -Parent $dir
    if ($parent -eq $dir) { break }
    $dir = $parent
  }
  return (Resolve-Path -LiteralPath $Start).Path
}

function Copy-SkillDirectory {
  param([string]$Source, [string]$Destination)
  $src = (Resolve-Path -LiteralPath $Source).Path
  if ((Test-Path -LiteralPath $Destination) -and ((Resolve-Path -LiteralPath $Destination).Path -eq $src)) {
    Write-Host "Source already at $Destination"
    return
  }
  $parent = Split-Path -Parent $Destination
  New-Item -ItemType Directory -Force -Path $parent | Out-Null
  if (Test-Path -LiteralPath $Destination) {
    Remove-Item -LiteralPath $Destination -Recurse -Force
  }
  New-Item -ItemType Directory -Force -Path $Destination | Out-Null
  Get-ChildItem -LiteralPath $src -Force | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $Destination -Recurse -Force
  }
  Write-Host "Synced $SkillName -> $Destination"
}

function Get-SkillFiles {
  param([string]$Directory)
  $result = @{}
  if (!(Test-Path -LiteralPath $Directory -PathType Container)) {
    return $result
  }
  $root = (Resolve-Path -LiteralPath $Directory).Path
  Get-ChildItem -LiteralPath $root -Recurse -Force -File | ForEach-Object {
    $rel = [System.IO.Path]::GetRelativePath($root, $_.FullName)
    $result[$rel] = $_.FullName
  }
  return $result
}

function Files-AreSame {
  param([string]$A, [string]$B)
  if (!(Test-Path -LiteralPath $A) -or !(Test-Path -LiteralPath $B)) { return $false }
  $aItem = Get-Item -LiteralPath $A
  $bItem = Get-Item -LiteralPath $B
  if ($aItem.Length -ne $bItem.Length) { return $false }
  $aHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $A).Hash
  $bHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $B).Hash
  return $aHash -eq $bHash
}

function Copy-OneFile {
  param([string]$SourceFile, [string]$DestinationFile)
  $parent = Split-Path -Parent $DestinationFile
  New-Item -ItemType Directory -Force -Path $parent | Out-Null
  Copy-Item -LiteralPath $SourceFile -Destination $DestinationFile -Force
}

function Sync-SkillPair {
  param([string]$Left, [string]$Right, [string]$LeftLabel, [string]$RightLabel)

  New-Item -ItemType Directory -Force -Path $Left | Out-Null
  New-Item -ItemType Directory -Force -Path $Right | Out-Null

  $leftFiles = Get-SkillFiles -Directory $Left
  $rightFiles = Get-SkillFiles -Directory $Right
  $keys = @($leftFiles.Keys + $rightFiles.Keys) | Select-Object -Unique | Sort-Object

  foreach ($rel in $keys) {
    $leftFile = $leftFiles[$rel]
    $rightFile = $rightFiles[$rel]

    if ($leftFile -and $rightFile) {
      if (Files-AreSame -A $leftFile -B $rightFile) { continue }
      $leftMtime = (Get-Item -LiteralPath $leftFile).LastWriteTimeUtc
      $rightMtime = (Get-Item -LiteralPath $rightFile).LastWriteTimeUtc
      if ($leftMtime -ge $rightMtime) {
        Copy-OneFile -SourceFile $leftFile -DestinationFile $rightFile
        Write-Host "$LeftLabel -> $RightLabel [$rel]"
      } else {
        Copy-OneFile -SourceFile $rightFile -DestinationFile $leftFile
        Write-Host "$RightLabel -> $LeftLabel [$rel]"
      }
    } elseif ($leftFile) {
      Copy-OneFile -SourceFile $leftFile -DestinationFile (Join-Path $Right $rel)
      Write-Host "$LeftLabel -> $RightLabel [$rel] (new)"
    } elseif ($rightFile) {
      Copy-OneFile -SourceFile $rightFile -DestinationFile (Join-Path $Left $rel)
      Write-Host "$RightLabel -> $LeftLabel [$rel] (new)"
    }
  }
}

if (-not $RepoRoot) {
  $RepoRoot = Resolve-RepoRoot -Start (Get-Location).Path
} else {
  $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$candidateSources = @()
if ($SourcePath) { $candidateSources += $SourcePath }
$candidateSources += @(
  (Join-Path $RepoRoot ".agents\skills\$SkillName"),
  (Join-Path $RepoRoot ".codex\skills\$SkillName"),
  (Join-Path $RepoRoot ".claude\skills\$SkillName")
)

if ($Global) {
  $candidateSources += @(
    (Join-Path $env:USERPROFILE ".codex\skills\$SkillName"),
    (Join-Path $env:USERPROFILE ".claude\skills\$SkillName")
  )
}

$source = $candidateSources | Where-Object { Test-Path -LiteralPath $_ -PathType Container } | Select-Object -First 1
if (-not $source) {
  throw "Skill '$SkillName' not found. Create it under '$RepoRoot\.codex\skills\$SkillName' or pass -SourcePath."
}
$source = (Resolve-Path -LiteralPath $source).Path
Write-Host "Source: $source"
Write-Host "RepoRoot: $RepoRoot"

$destinations = @()
if (Test-Path -LiteralPath (Join-Path $RepoRoot ".codex\skills")) {
  $destinations += (Join-Path $RepoRoot ".codex\skills\$SkillName")
} elseif (Test-Path -LiteralPath (Join-Path $RepoRoot ".agents\skills")) {
  $destinations += (Join-Path $RepoRoot ".agents\skills\$SkillName")
} else {
  $destinations += (Join-Path $RepoRoot ".codex\skills\$SkillName")
}

$destinations += @(
  (Join-Path $RepoRoot ".claude\skills\$SkillName")
)

$globalDestinations = @()
if ($Global) {
  $globalDestinations += @(
    (Join-Path $env:USERPROFILE ".codex\skills\$SkillName"),
    (Join-Path $env:USERPROFILE ".claude\skills\$SkillName")
  )
  $destinations += $globalDestinations
}

$destinations = @($destinations | Select-Object -Unique)

foreach ($dest in $destinations) {
  if (!(Test-Path -LiteralPath $dest -PathType Container)) {
    Copy-SkillDirectory -Source $source -Destination $dest
  }
}

$syncRoots = @($source) + @($destinations) | Select-Object -Unique
for ($i = 0; $i -lt $syncRoots.Count; $i++) {
  for ($j = $i + 1; $j -lt $syncRoots.Count; $j++) {
    Sync-SkillPair -Left $syncRoots[$i] -Right $syncRoots[$j] -LeftLabel $syncRoots[$i] -RightLabel $syncRoots[$j]
  }
}

$hashTargets = @(
  (Join-Path $RepoRoot ".codex\skills\$SkillName\SKILL.md"),
  (Join-Path $RepoRoot ".agents\skills\$SkillName\SKILL.md"),
  (Join-Path $RepoRoot ".claude\skills\$SkillName\SKILL.md")
) | Where-Object { Test-Path -LiteralPath $_ }

if ($Global) {
  $hashTargets += @(
    (Join-Path $env:USERPROFILE ".codex\skills\$SkillName\SKILL.md"),
    (Join-Path $env:USERPROFILE ".claude\skills\$SkillName\SKILL.md")
  ) | Where-Object { Test-Path -LiteralPath $_ }
}

$hashTargets | ForEach-Object {
  $hash = Get-FileHash -Algorithm SHA256 -LiteralPath $_
  Write-Host ("HASH {0} {1}" -f $hash.Hash.Substring(0,16), $_)
}

if ($Package) {
  if (-not $PackagePath) {
    $dist = Join-Path $RepoRoot "dist"
    New-Item -ItemType Directory -Force -Path $dist | Out-Null
    $PackagePath = Join-Path $dist "$SkillName.zip"
  }
  $PackagePath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($PackagePath)
  if (Test-Path -LiteralPath $PackagePath) {
    Remove-Item -LiteralPath $PackagePath -Force
  }
  $staging = Join-Path ([System.IO.Path]::GetTempPath()) ("skill-sync-package-" + [System.Guid]::NewGuid().ToString("N"))
  New-Item -ItemType Directory -Force -Path $staging | Out-Null
  $stageSkill = Join-Path $staging $SkillName
  Copy-SkillDirectory -Source $source -Destination $stageSkill
  Compress-Archive -LiteralPath $stageSkill -DestinationPath $PackagePath -Force
  Remove-Item -LiteralPath $staging -Recurse -Force
  Write-Host "PACKAGE $PackagePath"
}
