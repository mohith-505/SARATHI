param (
    [switch]$BackendOnly = $false,
    [switch]$FrontendOnly = $false,
    [switch]$TerminalOnly = $false,
    [switch]$BrowserOnly = $false,
    [switch]$NoBrowser = $false
)

$ErrorActionPreference = "Stop"

Write-Host "`n=======================================================" -ForegroundColor Cyan
Write-Host "  SARATHI ~ Your AI Companion (Environment Validation) " -ForegroundColor Green
Write-Host "=======================================================`n" -ForegroundColor Cyan

# 1. Validate required environment
$RootDir = $PSScriptRoot
if (-not $RootDir) { $RootDir = (Get-Location).Path }

$PythonExe = Join-Path $RootDir ".venv\Scripts\python.exe"
if (!(Test-Path $PythonExe)) {
    Write-Error "Python virtual environment not found at $PythonExe. Please initialize .venv first."
    exit 1
}

# 2. Start the SARATHI backend if necessary
$BackendProcess = $null
if (-not $FrontendOnly) {
    Write-Host "[1/3] Starting SARATHI Backend on 127.0.0.1:8000..." -ForegroundColor Cyan
    $BackendProcess = Start-Process -FilePath $PythonExe -ArgumentList "-m", "uvicorn", "apps.daemon.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory $RootDir -PassThru -NoNewWindow
    # Give the backend a brief moment to bind
    Start-Sleep -Milliseconds 800
}

# 3. Handle Pure Terminal Mode (Explicit Fallback)
if ($TerminalOnly) {
    Write-Host "[2/3] Starting SARATHI Terminal Chat Session..." -ForegroundColor Cyan
    try {
        & $PythonExe -m apps.cli.main chat
    } finally {
        if ($BackendProcess -and -not $BackendProcess.HasExited) {
            Write-Host "`nShutting down SARATHI Backend..." -ForegroundColor Yellow
            try { taskkill /PID $BackendProcess.Id /T /F 2>$null | Out-Null } catch { Stop-Process -Id $BackendProcess.Id -Force -ErrorAction SilentlyContinue }
        }
    }
    exit 0
}

# 4. Start the SARATHI Frontend (Desktop HUD)
$FrontendProcess = $null
if (-not $BackendOnly) {
    Write-Host "[2/3] Starting SARATHI Desktop Frontend on 127.0.0.1:5173..." -ForegroundColor Cyan

    $FrontendDir = Join-Path $RootDir "frontend"
    $UiDir = Join-Path $RootDir "ui"

    if (Test-Path $FrontendDir) {
        if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
            Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
            Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm install" -WorkingDirectory $FrontendDir -Wait -NoNewWindow
        }
        $FrontendProcess = Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev" -WorkingDirectory $FrontendDir -PassThru -NoNewWindow
    } elseif (Test-Path (Join-Path $UiDir "package.json")) {
        if (-not (Test-Path (Join-Path $UiDir "node_modules"))) {
            Write-Host "Installing UI dependencies..." -ForegroundColor Yellow
            Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm install" -WorkingDirectory $UiDir -Wait -NoNewWindow
        }
        $FrontendProcess = Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev" -WorkingDirectory $UiDir -PassThru -NoNewWindow
    } else {
        Write-Warning "Frontend directory not found. Skipping frontend startup."
    }
}

# 5. Launch the Graphical SARATHI Application with Original Welcome Artwork
if (-not $BackendOnly -and -not $NoBrowser) {
    Write-Host "[3/3] Launching SARATHI Graphical Welcome Experience..." -ForegroundColor Green
    # Allow Vite server to initialize
    Start-Sleep -Seconds 1

    if ($BrowserOnly) {
        # Open directly in browser
        Start-Process "http://127.0.0.1:5173"
    } else {
        # Launch dedicated native desktop welcome window
        # Displays the authentic 1024x322 original reference artwork directly
        # and transitions to the SARATHI HUD (127.0.0.1:5173) upon click / Enter / timeout
        Start-Process -FilePath $PythonExe -ArgumentList "-m", "ui.welcome_window", "--timeout", "3.8" -WorkingDirectory $RootDir
    }
}

try {
    Write-Host "`nSARATHI is live and operational." -ForegroundColor Green
    Write-Host "  • Backend Daemon:  http://127.0.0.1:8000" -ForegroundColor Cyan
    Write-Host "  • Desktop HUD:     http://127.0.0.1:5173" -ForegroundColor Cyan
    Write-Host "`nPress Ctrl+C to stop development servers.`n" -ForegroundColor DarkGray
    while ($true) {
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Host "`nShutting down SARATHI development servers..." -ForegroundColor Yellow
    if ($BackendProcess -and -not $BackendProcess.HasExited) {
        try {
            taskkill /PID $BackendProcess.Id /T /F 2>$null | Out-Null
        } catch {
            Stop-Process -Id $BackendProcess.Id -Force -ErrorAction SilentlyContinue
        }
    }
    if ($FrontendProcess -and -not $FrontendProcess.HasExited) {
        try {
            taskkill /PID $FrontendProcess.Id /T /F 2>$null | Out-Null
        } catch {
            Stop-Process -Id $FrontendProcess.Id -Force -ErrorAction SilentlyContinue
        }
    }
    # Clean up any lingering process on ports 8000 and 5173
    $orphanPids = (Get-NetTCPConnection -LocalPort 8000, 5173 -ErrorAction SilentlyContinue).OwningProcess
    foreach ($pidToKill in $orphanPids) {
        try { taskkill /PID $pidToKill /T /F 2>$null | Out-Null } catch {}
    }
}
