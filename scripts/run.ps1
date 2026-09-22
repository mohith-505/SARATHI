$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

. .\.venv\Scripts\Activate.ps1
sarathi chat @args
