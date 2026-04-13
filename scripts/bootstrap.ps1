$ErrorActionPreference = "Stop"

param(
    [switch]$WithKokoro
)

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$venvDir = Join-Path $projectRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$remotionDir = Join-Path $projectRoot "remotion-app"

if (-not (Test-Path $venvPython)) {
    Write-Host "Creando entorno virtual en .venv..." -ForegroundColor Cyan
    python -m venv $venvDir
}
else {
    Write-Host "Reutilizando entorno virtual existente en .venv..." -ForegroundColor DarkCyan
}

Write-Host "Actualizando pip..." -ForegroundColor Cyan
& $venvPython -m pip install --upgrade pip

Write-Host "Instalando dependencias Python del proyecto..." -ForegroundColor Cyan
Push-Location $projectRoot
try {
    if ($WithKokoro) {
        & $venvPython -m pip install -e ".[kokoro]"
    }
    else {
        & $venvPython -m pip install -e .
    }

    Write-Host "Instalando dependencias de Streamlit..." -ForegroundColor Cyan
    & $venvPython -m pip install -r .\automation\streamlit\requirements.txt
}
finally {
    Pop-Location
}

if (-not (Test-Path (Join-Path $remotionDir "package.json"))) {
    throw "No se encontro remotion-app/package.json"
}

Write-Host "Instalando dependencias de Remotion..." -ForegroundColor Cyan
Push-Location $remotionDir
try {
    npm install
}
finally {
    Pop-Location
}

Write-Host "" 
Write-Host "Bootstrap completado." -ForegroundColor Green
Write-Host "Activa el entorno con: .\.venv\Scripts\Activate.ps1" -ForegroundColor Green
Write-Host "O abre el entorno de desarrollo con: .\scripts\dev.ps1" -ForegroundColor Green
