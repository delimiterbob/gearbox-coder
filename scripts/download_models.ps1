<#
.SYNOPSIS
    Download the Gearbox controller and coder GGUF models from Hugging Face.
.PARAMETER SkipController
    Skip downloading the controller model (Qwen3-4B).
.PARAMETER SkipCoder
    Skip downloading the coder model (Phi-4).
.EXAMPLE
    .\download_models.ps1
    .\download_models.ps1 -SkipCoder
#>
[CmdletBinding()]
param(
    [switch]$SkipController,
    [switch]$SkipCoder
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$GgufDir = "I:\gguf-models"

$Models = @{
    controller = @{
        Name     = "Qwen3-4B (Controller)"
        FileName = "Qwen3-4B-Q4_K_M.gguf"
        Url      = "https://huggingface.co/bartowski/Qwen3-4B-GGUF/resolve/main/Qwen3-4B-Q4_K_M.gguf"
        Skip     = $SkipController
    }
    coder = @{
        Name     = "Phi-4 14B (Coder)"
        FileName = "phi-4-Q4_K_M.gguf"
        Url      = "https://huggingface.co/bartowski/phi-4-GGUF/resolve/main/phi-4-Q4_K_M.gguf"
        Skip     = $SkipCoder
    }
}

if (-not (Test-Path $GgufDir)) {
    New-Item -ItemType Directory -Path $GgufDir -Force | Out-Null
}

foreach ($key in $Models.Keys) {
    $info = $Models[$key]
    if ($info.Skip) {
        Write-Host "  [SKIP] $($info.Name)" -ForegroundColor DarkGray
        continue
    }

    $dest = Join-Path $GgufDir $info.FileName

    if (Test-Path $dest) {
        $sizeMB = [math]::Round((Get-Item $dest).Length / 1MB, 1)
        if ($sizeMB -lt 1000) {
            Write-Host "  [WARN] $($info.Name) exists but is only $sizeMB MB -- re-downloading" -ForegroundColor Yellow
            Remove-Item $dest -Force
        } else {
            Write-Host "  [OK]   $($info.Name) already present ($sizeMB MB)" -ForegroundColor Green
            continue
        }
    }

    Write-Host ""
    Write-Host "  [DL] $($info.Name)" -ForegroundColor Cyan
    Write-Host "       $($info.Url)" -ForegroundColor DarkGray
    Write-Host "       -> $dest" -ForegroundColor DarkGray

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    & curl.exe -4 -L --continue-at - --progress-bar -o $dest $info.Url
    $sw.Stop()

    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 33) {
        Write-Host "  [FAIL] Download failed (curl exit $LASTEXITCODE)" -ForegroundColor Red
        if (Test-Path $dest) { Remove-Item $dest -Force -ErrorAction SilentlyContinue }
        exit 1
    }

    $sizeGB = [math]::Round((Get-Item $dest).Length / 1GB, 2)
    Write-Host "  [OK]  Downloaded: $sizeGB GB in $([math]::Round($sw.Elapsed.TotalMinutes, 1)) min" -ForegroundColor Green
}

Write-Host ""
Write-Host "  Models ready in $GgufDir" -ForegroundColor White
