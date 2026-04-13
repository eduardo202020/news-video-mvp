$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$streamlitScript = Join-Path $projectRoot "scripts\dev-streamlit.ps1"
$remotionScript = Join-Path $projectRoot "scripts\dev-remotion.ps1"

if (-not (Test-Path (Join-Path $projectRoot ".venv\Scripts\python.exe"))) {
    throw "No se encontro el entorno virtual en .venv. Crealo primero con: python -m venv .venv"
}

Write-Host "Abriendo Streamlit..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $streamlitScript
)

Write-Host "Abriendo Remotion Studio..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $remotionScript
)

Write-Host "Listo. Se abrieron dos ventanas: Streamlit y Remotion." -ForegroundColor Green
