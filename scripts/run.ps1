param (
    [switch]$TerminalOnly = $false
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if ($TerminalOnly) {
    & ".\dev.ps1" -TerminalOnly
} else {
    & ".\dev.ps1"
}
