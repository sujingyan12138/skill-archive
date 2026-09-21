param(
  [Parameter(Mandatory=$true)]
  [string]$SkillName,

  [string]$RepoRoot,

  [string]$SourcePath,

  [switch]$ProjectOnly,

  [switch]$Bidirectional,

  [switch]$DryRun,

  [switch]$NoBackup,

  [string]$BackupRoot,

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
  if (Test-Path -LiteralPath $Destination) {
    $dst = (Resolve-Path -LiteralPath $Destination).Path
    if ($dst -eq $src) {
      Write-Host "Source already at $Destination"
      return
    }
  }
  if ($DryRun) {
    Write-Host "  $Destination : 目录不存在，将整目录复制 (dry-run)"
    return
  }
  $parent = Split-Path -Parent $Destination
  New-Item -ItemType Directory -Force -Path $parent | Out-Null
  if (Test-Path -LiteralPath $Destination) {
    $item = Get-Item -LiteralPath $Destination -Force
    if ($item.PSIsContainer) {
      # 目标已是目录（含指向别处的软链）。绝不递归删除 —— PowerShell 5.1 的
      # Remove-Item -Recurse 会穿透软链删掉它指向的真实内容。这里只建不删。
      Write-Host "Destination exists as a directory, skipped rebuild: $Destination"
      return
    }
    Remove-Item -LiteralPath $Destination -Force
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
  # Windows PowerShell 5.1 has no [System.IO.Path]::GetRelativePath, so build the
  # relative path manually. Do not reintroduce the .NET Core-only call.
  $prefix = $root.TrimEnd('\', '/') + '\'
  $skipDirs = @('.cache', '__pycache__', '.skill-backups', '.git', 'node_modules',
                '.venv', 'venv', '.idea', '.vscode', '.pytest_cache', '.mypy_cache')
  $skipFiles = @('.state.json', '.DS_Store', 'Thumbs.db', 'desktop.ini',
                 '.in_use', '.last_inuse_sweep')
  Get-ChildItem -LiteralPath $root -Recurse -Force -File | ForEach-Object {
    $full = $_.FullName
    if ($full.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
      $rel = $full.Substring($prefix.Length)
    } else {
      $rel = $_.Name
    }
    # 运行态文件（下载缓存、同步状态、字节码）不属于技能内容，不该跨目录同步，
    # 否则副本里会凭空多出 .cache / .state.json / __pycache__。
    $parts = $rel -split '[\\/]'
    $leaf = $parts[$parts.Count - 1]
    $skip = $false
    for ($i = 0; $i -lt $parts.Count - 1; $i++) {
      if ($skipDirs -contains $parts[$i]) { $skip = $true; break }
    }
    if (!$skip) {
      if ($skipFiles -contains $leaf) { $skip = $true }
    }
    if (!$skip -and $leaf.EndsWith('.pyc')) { $skip = $true }
    if (!$skip -and ($leaf -like '*.bak*' -or $leaf -like '*.orig' -or $leaf.EndsWith('~'))) { $skip = $true }
    if (!$skip) { $result[$rel] = $full }
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

function Backup-SkillDir {
  param([string]$Directory, [string]$Label)
  if ($NoBackup -or $DryRun) { return $null }
  if (!(Test-Path -LiteralPath $Directory -PathType Container)) { return $null }
  $stamp = (Get-Date).ToString("yyyyMMdd-HHmmss")
  $root = $BackupRoot
  if (-not $root) {
    $root = Join-Path $env:USERPROFILE ".cc-switch\.skill-backups\sync"
  }
  $safe = $Label -replace '[\\/:*?"<>|]', '_'
  $dest = Join-Path (Join-Path $root $SkillName) ("$safe`__$stamp\files")
  New-Item -ItemType Directory -Force -Path $dest | Out-Null
  Get-ChildItem -LiteralPath $Directory -Force | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $dest -Recurse -Force
  }
  return (Split-Path -Parent $dest)
}

function Sync-OneWay {
  param([string]$Source, [string]$Target, [string]$SourceLabel, [string]$TargetLabel)

  $srcFiles = Get-SkillFiles -Directory $Source
  $tgtFiles = Get-SkillFiles -Directory $Target
  $changed = @()
  foreach ($rel in ($srcFiles.Keys | Sort-Object)) {
    $sf = $srcFiles[$rel]
    if ($tgtFiles.ContainsKey($rel)) {
      if (Files-AreSame -A $sf -B $tgtFiles[$rel]) { continue }
    }
    $changed += $rel
  }

  $onlyTarget = @()
  foreach ($rel in ($tgtFiles.Keys | Sort-Object)) {
    if (!$srcFiles.ContainsKey($rel)) { $onlyTarget += $rel }
  }

  if ($changed.Count -eq 0) {
    if ($onlyTarget.Count -gt 0) {
      Write-Host "  $TargetLabel : 已一致（目标另有 $($onlyTarget.Count) 个源里没有的文件，保留）"
    } else {
      Write-Host "  $TargetLabel : 已一致"
    }
    return 0
  }

  if ($DryRun) {
    Write-Host "  $TargetLabel : 将写入 $($changed.Count) 个文件 (dry-run)"
    return $changed.Count
  }

  $bk = Backup-SkillDir -Directory $Target -Label $TargetLabel
  if ($bk) { Write-Host "  $TargetLabel : 旧版已备份 -> $bk" }

  New-Item -ItemType Directory -Force -Path $Target | Out-Null
  foreach ($rel in $changed) {
    Copy-OneFile -SourceFile $srcFiles[$rel] -DestinationFile (Join-Path $Target $rel)
  }
  Write-Host "  $TargetLabel : 已同步 $($changed.Count) 个文件（$SourceLabel -> $TargetLabel）"
  return $changed.Count
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
      if ($DryRun) {
        Write-Host "  [dry-run] $rel"
        continue
      }
      if ($leftMtime -ge $rightMtime) {
        Copy-OneFile -SourceFile $leftFile -DestinationFile $rightFile
        Write-Host "$LeftLabel -> $RightLabel [$rel]"
      } else {
        Copy-OneFile -SourceFile $rightFile -DestinationFile $leftFile
        Write-Host "$RightLabel -> $LeftLabel [$rel]"
      }
    } elseif ($leftFile) {
      if ($DryRun) { Write-Host "  [dry-run] $rel (new)"; continue }
      Copy-OneFile -SourceFile $leftFile -DestinationFile (Join-Path $Right $rel)
      Write-Host "$LeftLabel -> $RightLabel [$rel] (new)"
    } elseif ($rightFile) {
      if ($DryRun) { Write-Host "  [dry-run] $rel (new)"; continue }
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

$userHome = $env:USERPROFILE
$masterRoot = Join-Path $userHome ".cc-switch\skills"

$globalSkillRoots = @(
  (Join-Path $userHome ".codex\skills"),
  (Join-Path $userHome ".claude\skills"),
  (Join-Path $userHome ".workbuddy\skills")
)

$candidateSources = @()
if ($SourcePath) { $candidateSources += $SourcePath }
$candidateSources += @(
  (Join-Path $masterRoot "$SkillName"),
  (Join-Path $RepoRoot ".agents\skills\$SkillName"),
  (Join-Path $RepoRoot ".codex\skills\$SkillName"),
  (Join-Path $RepoRoot ".claude\skills\$SkillName")
)
foreach ($r in $globalSkillRoots) {
  $candidateSources += (Join-Path $r $SkillName)
}

$source = $candidateSources | Where-Object { Test-Path -LiteralPath $_ -PathType Container } | Select-Object -First 1
if (-not $source) {
  throw "Skill '$SkillName' not found. Create it under '$RepoRoot\.codex\skills\$SkillName', put it in '$masterRoot', or pass -SourcePath."
}
$source = (Resolve-Path -LiteralPath $source).Path
Write-Host "Source: $source"
Write-Host "RepoRoot: $RepoRoot"
if ($ProjectOnly) {
  Write-Host "Mode: project-only"
} elseif ($Bidirectional) {
  Write-Host "Mode: all agents, bidirectional (mtime decides)"
} else {
  Write-Host "Mode: all agents, one-way (source wins)"
}

$destinations = @()
$projectDestinations = @()
if (Test-Path -LiteralPath (Join-Path $RepoRoot ".codex\skills")) {
  $projectDestinations += (Join-Path $RepoRoot ".codex\skills\$SkillName")
} elseif (Test-Path -LiteralPath (Join-Path $RepoRoot ".agents\skills")) {
  $projectDestinations += (Join-Path $RepoRoot ".agents\skills\$SkillName")
} else {
  $projectDestinations += (Join-Path $RepoRoot ".codex\skills\$SkillName")
}
$projectDestinations += (Join-Path $RepoRoot ".claude\skills\$SkillName")

if ($ProjectOnly) {
  $destinations = $projectDestinations
} else {
  $destinations += $globalSkillRoots | ForEach-Object { Join-Path $_ $SkillName }
  foreach ($pd in $projectDestinations) {
    if (Test-Path -LiteralPath $pd -PathType Container) { $destinations += $pd }
  }
}

$destinations = @($destinations | Where-Object { $_ -ne $source } | Select-Object -Unique)

foreach ($dest in $destinations) {
  if (!(Test-Path -LiteralPath $dest -PathType Container)) {
    Copy-SkillDirectory -Source $source -Destination $dest
  }
}

$syncRoots = @($source) + @($destinations) | Select-Object -Unique

if ($Bidirectional -and $syncRoots.Count -gt 1) {
  for ($i = 0; $i -lt $syncRoots.Count; $i++) {
    for ($j = $i + 1; $j -lt $syncRoots.Count; $j++) {
      Sync-SkillPair -Left $syncRoots[$i] -Right $syncRoots[$j] -LeftLabel $syncRoots[$i] -RightLabel $syncRoots[$j]
    }
  }
} else {
  $sourceFiles = Get-SkillFiles -Directory $source
  Write-Host "文件数: $($sourceFiles.Count)"
  foreach ($dest in $destinations) {
    $label = $dest
    Sync-OneWay -Source $source -Target $dest -SourceLabel $source -TargetLabel $label | Out-Null
  }
}

$hashTargets = @()
foreach ($dest in $destinations) {
  $hashTargets += (Join-Path $dest "SKILL.md")
}
$hashTargets = @($hashTargets | Where-Object { Test-Path -LiteralPath $_ })

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
