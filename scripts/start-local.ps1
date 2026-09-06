[CmdletBinding()]
param(
    [ValidateRange(0, 3600)]
    [int]$AutoStopAfterSeconds = 0
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$frontendDirectory = Join-Path $projectRoot "frontend"
$backendDirectory = Join-Path $projectRoot "backend"
$backendPython = Join-Path $backendDirectory ".venv\Scripts\python.exe"
$frontendProcess = $null
$backendProcess = $null

function Assert-CommandSucceeded {
    param([Parameter(Mandatory)][string]$Step)

    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE."
    }
}

function Wait-ForService {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$Url,
        [Parameter(Mandatory)][System.Diagnostics.Process]$Process
    )

    $deadline = (Get-Date).AddSeconds(15)

    while ((Get-Date) -lt $deadline) {
        if ($Process.HasExited) {
            throw "$Name stopped during startup with exit code $($Process.ExitCode)."
        }

        try {
            $response = Invoke-WebRequest -Uri $Url -TimeoutSec 1 -UseBasicParsing
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
                return
            }
        }
        catch {
            Start-Sleep -Milliseconds 250
        }
    }

    throw "$Name did not become ready within 15 seconds."
}

try {
    Write-Host "[setup] Installing frontend dependencies..." -ForegroundColor Cyan
    Push-Location $frontendDirectory
    try {
        & npm install
        Assert-CommandSucceeded "npm install"
    }
    finally {
        Pop-Location
    }

    if (-not (Test-Path -LiteralPath $backendPython)) {
        Write-Host "[setup] Creating the Python 3.13 virtual environment..." -ForegroundColor Cyan
        & py -3.13 -m venv (Join-Path $backendDirectory ".venv")
        Assert-CommandSucceeded "Python virtual environment creation"
    }

    Write-Host "[setup] Installing backend dependencies..." -ForegroundColor Cyan
    & $backendPython -m pip install --disable-pip-version-check -r (Join-Path $backendDirectory "requirements-dev.txt")
    Assert-CommandSucceeded "Backend dependency installation"

    $nodeExecutable = (Get-Command node -ErrorAction Stop).Source

    Write-Host "[start] Starting frontend and backend..." -ForegroundColor Cyan
    $frontendProcess = Start-Process `
        -FilePath $nodeExecutable `
        -ArgumentList "server.js" `
        -WorkingDirectory $frontendDirectory `
        -NoNewWindow `
        -PassThru
    $backendProcess = Start-Process `
        -FilePath $backendPython `
        -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
        -WorkingDirectory $backendDirectory `
        -NoNewWindow `
        -PassThru

    Wait-ForService -Name "Frontend" -Url "http://127.0.0.1:3000/" -Process $frontendProcess
    Wait-ForService -Name "Backend" -Url "http://127.0.0.1:8000/health" -Process $backendProcess

    Write-Host ""
    Write-Host "Frontend: http://127.0.0.1:3000" -ForegroundColor Green
    Write-Host "Backend:  http://127.0.0.1:8000" -ForegroundColor Green
    Write-Host "API docs: http://127.0.0.1:8000/docs" -ForegroundColor Green
    Write-Host "Press Ctrl+C to stop both services." -ForegroundColor Yellow

    $startedAt = Get-Date
    while (-not $frontendProcess.HasExited -and -not $backendProcess.HasExited) {
        if ($AutoStopAfterSeconds -gt 0 -and ((Get-Date) - $startedAt).TotalSeconds -ge $AutoStopAfterSeconds) {
            Write-Host "[test] Automatic stop requested." -ForegroundColor Yellow
            return
        }

        Start-Sleep -Seconds 1
    }

    if ($frontendProcess.HasExited) {
        throw "Frontend stopped unexpectedly with exit code $($frontendProcess.ExitCode)."
    }

    throw "Backend stopped unexpectedly with exit code $($backendProcess.ExitCode)."
}
finally {
    Write-Host ""
    Write-Host "[stop] Stopping local services..." -ForegroundColor Cyan

    foreach ($process in @($frontendProcess, $backendProcess)) {
        if ($null -ne $process -and -not $process.HasExited) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
    }
}
