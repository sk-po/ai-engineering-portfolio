[CmdletBinding()]
param(
    [switch]$Detach,
    [switch]$NoBuild
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
$dockerExecutable = if ($dockerCommand) {
    $dockerCommand.Source
}
else {
    "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
}

if (-not (Test-Path -LiteralPath $dockerExecutable)) {
    throw "Docker CLI was not found. Install and start Docker Desktop first."
}

$dockerDirectory = Split-Path -Parent $dockerExecutable
if (($env:Path -split ";") -notcontains $dockerDirectory) {
    $env:Path = "$dockerDirectory;$env:Path"
}

$composeArguments = @("compose", "up")

if (-not $NoBuild) {
    $composeArguments += "--build"
}

if ($Detach) {
    $composeArguments += "--detach"
}

Push-Location $projectRoot
try {
    & $dockerExecutable @composeArguments

    if ($LASTEXITCODE -ne 0) {
        throw "docker compose up failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
