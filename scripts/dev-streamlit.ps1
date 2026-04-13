$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$streamlitApp = Join-Path $projectRoot "automation\streamlit\app.py"

if (-not (Test-Path $venvPython)) {
    throw "No se encontro el entorno virtual en .venv. Crealo primero con: python -m venv .venv"
}

& $venvPython -m streamlit run $streamlitApp
