<#
.SYNOPSIS
    Start two llama-server instances: controller (port 8001) and coder (port 8002).
    Auto-tunes GPU layer offload for RTX 5060 (8 GB VRAM) — same logic as MTS.
.PARAMETER ControllerOnly
    Start only the controller server.
.PARAMETER CoderOnly
    Start only the coder server.
.EXAMPLE
    .\start_servers.ps1
    .\start_servers.ps1 -ControllerOnly
#>
[CmdletBinding()]
param(
    [switch]$ControllerOnly,
    [switch]$CoderOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$LlamaCppDir  = "I:\llama-cpp"
$GgufDir      = "I:\gguf-models"
$ServerExe    = Join-Path $LlamaCppDir "llama-server.exe"
$USABLE_VRAM_GB = 7.5

$Servers = @(
    @{
        Role       = "controller"
        FileName   = "Qwen3-4B-Q4_K_M.gguf"
        Port       = 8001
        ContextSize = 8192
        PidFile    = Join-Path $LlamaCppDir "llama-server-8001.pid"
        LogFile    = Join-Path $LlamaCppDir "llama-server-8001.log"
        Skip       = $CoderOnly
    },
    @{
        Role       = "coder"
        FileName   = "phi-4-Q4_K_M.gguf"
        Port       = 8002
        ContextSize = 8192
        PidFile    = Join-Path $LlamaCppDir "llama-server-8002.pid"
        LogFile    = Join-Path $LlamaCppDir "llama-server-8002.log"
        Skip       = $ControllerOnly
    }
)

if (-not (Test-Path $ServerExe)) {
    throw "llama-server.exe not found at $ServerExe"
}

function Start-LlamaInstance {
    param($Server)

    $ModelPath = Join-Path $GgufDir $Server.FileName
    if (-not (Test-Path $ModelPath)) {
        throw "Model not found: $ModelPath. Run .\scripts\download_models.ps1 first."
    }

    # Kill any existing instance on this port
    if (Test-Path $Server.PidFile) {
        $oldPid = (Get-Content $Server.PidFile -Raw).Trim()
        $proc = Get-Process -Id $oldPid -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "  [$($Server.Role)] Stopping previous instance (PID $oldPid)..." -ForegroundColor Yellow
            Stop-Process -Id $oldPid -Force
            Start-Sleep -Seconds 2
        }
        Remove-Item $Server.PidFile -Force
    }

    # GPU layer calculation (mirrors MTS start-llama-server.ps1)
    $fileSizeGB = (Get-Item $ModelPath).Length / 1GB
    if ($fileSizeGB -le $USABLE_VRAM_GB) {
        $ngl = 99
        $strategy = "Full GPU"
    } else {
        $estimatedLayers = 40
        $ngl = [math]::Floor($estimatedLayers * $USABLE_VRAM_GB / $fileSizeGB)
        if ($ngl -lt 1) { $ngl = 1 }
        $strategy = "Partial GPU ($ngl layers)"
    }

    $contextSize = $Server.ContextSize
    if ($fileSizeGB -gt 20 -and $contextSize -gt 8192) {
        $contextSize = 8192
    }

    Write-Host ""
    Write-Host "  [$($Server.Role)] Model:    $($Server.FileName)" -ForegroundColor Cyan
    Write-Host "  [$($Server.Role)] Size:     $([math]::Round($fileSizeGB, 1)) GB" -ForegroundColor Cyan
    Write-Host "  [$($Server.Role)] GPU:      $strategy (ngl=$ngl)" -ForegroundColor Cyan
    Write-Host "  [$($Server.Role)] Port:     $($Server.Port)" -ForegroundColor Cyan

    $argList = @(
        "--model",       $ModelPath,
        "--port",        $Server.Port,
        "--ctx-size",    $contextSize,
        "--n-gpu-layers",$ngl,
        "--threads",     12,
        "--parallel",    1,
        "--flash-attn",  "auto",
        "--jinja"
    )

    $proc = Start-Process -FilePath $ServerExe -ArgumentList $argList `
        -PassThru -WindowStyle Hidden -RedirectStandardError $Server.LogFile

    $proc.Id | Out-File -FilePath $Server.PidFile -Encoding utf8 -NoNewline
    Write-Host "  [$($Server.Role)] PID: $($proc.Id)" -ForegroundColor Green

    # Wait for health
    $healthUrl = "http://127.0.0.1:$($Server.Port)/health"
    $timeout = 300
    $elapsed = 0
    Write-Host "  [$($Server.Role)] Waiting for $healthUrl ..." -ForegroundColor Gray

    while ($elapsed -lt $timeout) {
        Start-Sleep -Seconds 2
        $elapsed += 2
        try {
            $resp = Invoke-WebRequest -Uri $healthUrl -TimeoutSec 3 -UseBasicParsing -ErrorAction SilentlyContinue
            if ($resp.StatusCode -eq 200) {
                Write-Host "  [$($Server.Role)] Ready after ${elapsed}s" -ForegroundColor Green
                return
            }
        } catch {}
        if ($proc.HasExited) {
            throw "[$($Server.Role)] llama-server exited unexpectedly. Check $($Server.LogFile)"
        }
        if ($elapsed % 30 -eq 0) {
            Write-Host "  [$($Server.Role)] Still loading... (${elapsed}s)" -ForegroundColor Gray
        }
    }
    throw "[$($Server.Role)] Server did not become healthy within ${timeout}s"
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor White
Write-Host "  GEARBOX: Starting llama-server instances" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor White

foreach ($server in $Servers) {
    if ($server.Skip) {
        Write-Host "  [$($server.Role)] Skipped" -ForegroundColor DarkGray
        continue
    }
    Start-LlamaInstance -Server $server
}

Write-Host ""
Write-Host "  Both servers ready." -ForegroundColor Green
Write-Host "  Controller: http://127.0.0.1:8001/v1" -ForegroundColor White
Write-Host "  Coder:      http://127.0.0.1:8002/v1" -ForegroundColor White
Write-Host ""
