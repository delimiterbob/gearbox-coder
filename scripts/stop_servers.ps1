<#
.SYNOPSIS
    Stop both Gearbox llama-server instances (ports 8001 and 8002).
#>
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

$LlamaCppDir = "I:\llama-cpp"
$PidFiles = @(
    Join-Path $LlamaCppDir "llama-server-8001.pid",
    Join-Path $LlamaCppDir "llama-server-8002.pid"
)

foreach ($pidFile in $PidFiles) {
    if (-not (Test-Path $pidFile)) {
        Write-Host "  [STOP] No PID file: $pidFile" -ForegroundColor DarkGray
        continue
    }

    $storedPid = (Get-Content $pidFile -Raw -ErrorAction SilentlyContinue).Trim()
    if (-not $storedPid) {
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
        continue
    }

    $proc = Get-Process -Id $storedPid -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Host "  [STOP] Stopping PID $storedPid ($($proc.ProcessName))..." -ForegroundColor Cyan
        Stop-Process -Id $storedPid -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        $check = Get-Process -Id $storedPid -ErrorAction SilentlyContinue
        if ($check) {
            Write-Host "  [WARN] Process $storedPid still running after 2s" -ForegroundColor Yellow
        } else {
            Write-Host "  [OK]   Process $storedPid stopped" -ForegroundColor Green
        }
    } else {
        Write-Host "  [SKIP] PID $storedPid not running (stale PID file)" -ForegroundColor DarkGray
    }

    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

Write-Host "  Servers stopped." -ForegroundColor Green
