# SARATHI setup (Windows / PowerShell)
# Creates a virtual environment and installs SARATHI with dev dependencies.

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv .venv
}

Write-Host "Activating venv..." -ForegroundColor Cyan
. .\.venv\Scripts\Activate.ps1

Write-Host "Upgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

Write-Host "Installing SARATHI (editable, with dev deps)..." -ForegroundColor Cyan
pip install -e ".[dev]"

Write-Host ""
Write-Host "Done. Activate with: .\.venv\Scripts\Activate.ps1" -ForegroundColor Green
Write-Host "Then run: sarathi chat" -ForegroundColor Green
