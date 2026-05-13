<#
.SYNOPSIS
    Copy T1 and T2 source files from the Model Testing Suite into GearBox repos/.
    MTS is treated as read-only; this script only reads from it.
.PARAMETER Force
    Overwrite existing repo directories.
.EXAMPLE
    .\setup_repos.ps1
    .\setup_repos.ps1 -Force
#>
[CmdletBinding()]
param([switch]$Force)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$MTSSources = "C:\Users\Admin\Desktop\Model Testing Suite\sources"
$GBRepos    = "C:\Users\Admin\Desktop\GearBox\repos"

# All MTS language folders and the test IDs each one has.
# Only T1 and T2 are copied into GearBox.
$LanguageTests = [ordered]@{
    "CSharp-WinForms" = @("T1-Calculator", "T2-LoginDialog")
    "VB.NET"          = @("T1-Calculator", "T2-LoginDialog")
    "VB6"             = @("T1-Calculator", "T2-LoginDialog")
    "Delphi"          = @("T1-Calculator", "T2-LoginDialog")
    "PowerBuilder"    = @("T1-Calculator", "T2-LoginDialog")
    "Legacy-Java"     = @("T1-Calculator", "T2-LoginDialog")
    "Silverlight"     = @("T1-Calculator", "T2-LoginDialog")
    "FoxPro"          = @("T1-Calculator", "T2-LoginDialog")
    "Clarion"         = @("T1-Calculator", "T2-LoginDialog")
    "ASP-Classic"     = @("T2-LoginDialog")
    "ASP-WebForms"    = @("T2-LoginDialog")
    "Informix-4GL"    = @("T2-LoginDialog")
    "COBOL"           = @("T1-Calculator")
}

if (-not (Test-Path $MTSSources)) {
    throw "MTS sources not found at $MTSSources"
}

New-Item -ItemType Directory -Path $GBRepos -Force | Out-Null

$copied = 0
$skipped = 0
$missing = 0

foreach ($lang in $LanguageTests.Keys) {
    foreach ($testId in $LanguageTests[$lang]) {
        $src = Join-Path $MTSSources "$lang\$testId"
        $dst = Join-Path $GBRepos "$lang\$testId"

        if (-not (Test-Path $src)) {
            Write-Host "  [MISS] $lang/$testId (not in MTS)" -ForegroundColor Yellow
            $missing++
            continue
        }

        if ((Test-Path $dst) -and -not $Force) {
            Write-Host "  [SKIP] $lang/$testId (exists, use -Force to overwrite)" -ForegroundColor DarkGray
            $skipped++
            continue
        }

        if (Test-Path $dst) { Remove-Item $dst -Recurse -Force }
        Copy-Item -Path $src -Destination $dst -Recurse
        $fileCount = (Get-ChildItem $dst -Recurse -File).Count
        Write-Host "  [OK]   $lang/$testId ($fileCount files)" -ForegroundColor Green
        $copied++
    }
}

Write-Host ""
Write-Host "  Repos setup: $copied copied, $skipped skipped, $missing missing" -ForegroundColor White
Write-Host "  Repos root: $GBRepos" -ForegroundColor White
