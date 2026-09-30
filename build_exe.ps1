$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "======================================="
Write-Host " FiltersReporting v1.00 - EXE build"
Write-Host "======================================="
Write-Host ""

$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

$AppEntry = Join-Path $ProjectRoot "filters_reporting\gui\app.py"
$CollectorEntry = Join-Path $ProjectRoot "filters_reporting\collection\data_collector.py"
$VersionFile = Join-Path $ProjectRoot "packaging\version_info.txt"
$RuntimeHook = Join-Path $ProjectRoot "packaging\runtime_hook.py"

if (-not (Test-Path $AppEntry)) {
    throw "Missing app entry point: $AppEntry"
}

if (-not (Test-Path $CollectorEntry)) {
    throw "Missing collector entry point: $CollectorEntry"
}

if (-not (Test-Path $VersionFile)) {
    throw "Missing version file: $VersionFile"
}

if (-not (Test-Path $RuntimeHook)) {
    throw "Missing runtime hook: $RuntimeHook"
}

Write-Host "[1/7] Stopping old processes..."

Get-Process FiltersReporting -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process FiltersReportingCollector -ErrorAction SilentlyContinue | Stop-Process -Force

Write-Host ""
Write-Host "[2/7] Running tests..."

python -m pytest

if ($LASTEXITCODE -ne 0) {
    throw "Pytest failed. Build aborted."
}

Write-Host ""
Write-Host "[3/7] Cleaning old build..."

Remove-Item -Recurse -Force -ErrorAction SilentlyContinue ".\build"
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue ".\dist"
Remove-Item -Force -ErrorAction SilentlyContinue ".\FiltersReporting.spec"
Remove-Item -Force -ErrorAction SilentlyContinue ".\FiltersReportingCollector.spec"

Write-Host ""
Write-Host "[4/7] Building FiltersReporting.exe..."

python -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --windowed `
    --name FiltersReporting `
    --version-file "$VersionFile" `
    --runtime-hook "$RuntimeHook" `
    --collect-all asyncua `
    --copy-metadata asyncua `
    "$AppEntry"

if ($LASTEXITCODE -ne 0) {
    throw "FiltersReporting build failed."
}

$AppExe = Join-Path $ProjectRoot "dist\FiltersReporting\FiltersReporting.exe"

if (-not (Test-Path $AppExe)) {
    throw "FiltersReporting.exe was not found: $AppExe"
}

Write-Host ""
Write-Host "[5/7] Building FiltersReportingCollector.exe..."

python -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --console `
    "--hide-console=hide-early" `
    --name FiltersReportingCollector `
    --runtime-hook "$RuntimeHook" `
    --collect-all asyncua `
    --copy-metadata asyncua `
    "$CollectorEntry"

if ($LASTEXITCODE -ne 0) {
    throw "FiltersReportingCollector build failed."