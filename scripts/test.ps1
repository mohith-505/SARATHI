$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

. .\.venv\Scripts\Activate.ps1

Write-Host "Ruff..." -ForegroundColor Cyan
ruff check .

Write-Host "MyPy..." -ForegroundColor Cyan
mypy core models apps

Write-Host "Pytest..." -ForegroundColor Cyan
pytest
