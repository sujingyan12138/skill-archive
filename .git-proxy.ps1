<#
.SYNOPSIS
    开关 git 针对 GitHub 的代理。代理软件（如 v2ray/clash）关闭时用 off，开启时用 on。

.DESCRIPTION
    只改 GitHub / codeload / raw.githubusercontent 三个域名的作用域代理，
    不影响 gitee、公司内网 Git 等直连仓库。

.PARAMETER Action
    on   = 启用代理（默认 127.0.0.1:10808）
    off  = 关闭代理（回到直连）
    status = 只看当前状态

.PARAMETER Port
    代理端口，默认 10808。

.EXAMPLE
    .\git-proxy.ps1 on
    .\git-proxy.ps1 off
    .\git-proxy.ps1 status
    .\git-proxy.ps1 on -Port 7890
#>
[CmdletBinding()]
param(
    [ValidateSet('on', 'off', 'status')]
    [string]$Action = 'status',

    [int]$Port = 10808
)

$ErrorActionPreference = 'Stop'

$hosts = @(
    'github.com',
    'codeload.github.com',
    'raw.githubusercontent.com',
    'objects.githubusercontent.com'
)

function Get-ProxyValue($host_) {
    $v = git config --global --get "http.https://$host_/.proxy" 2>$null
    if ([string]::IsNullOrWhiteSpace($v)) { return $null }
    return $v
}

switch ($Action) {
    'status' {
        Write-Host '当前 GitHub 代理状态：' -ForegroundColor Cyan
        foreach ($h in $hosts) {
            $v = Get-ProxyValue $h
            if ($v) {
                Write-Host ("  [开] {0,-34} -> {1}" -f $h, $v) -ForegroundColor Green
            }
            else {
                Write-Host ("  [关] {0,-34} -> 直连" -f $h) -ForegroundColor DarkGray
            }
        }
        Write-Host ''
        Write-Host '探测代理端口 127.0.0.1:' -NoNewline
        $portOpen = $false
        try {
            $c = New-Object System.Net.Sockets.TcpClient
            $portOpen = $c.ConnectAsync('127.0.0.1', $Port).Wait(1500)
            $c.Close()
        }
        catch { $portOpen = $false }
        if ($portOpen) {
            Write-Host "$Port  ✅ 开放（代理软件在跑）" -ForegroundColor Green
        }
        else {
            Write-Host "$Port  ✗ 关闭（代理软件没开，此时 git 访问 GitHub 会失败）" -ForegroundColor Yellow
        }
    }

    'on' {
        foreach ($h in $hosts) {
            git config --global "http.https://$h/.proxy" "http://127.0.0.1:$Port"
            git config --global "https.https://$h/.proxy" "http://127.0.0.1:$Port"
        }
        Write-Host "已启用 GitHub 代理 -> http://127.0.0.1:$Port" -ForegroundColor Green
        Write-Host '（其他域名不受影响，仍为直连）'
    }

    'off' {
        foreach ($h in $hosts) {
            git config --global --unset-all "http.https://$h/.proxy" 2>$null
            git config --global --unset-all "https.https://$h/.proxy" 2>$null
        }
        Write-Host '已关闭 GitHub 代理（GitHub 恢复直连；若直连不通则访问会失败）' -ForegroundColor Yellow
    }
}
