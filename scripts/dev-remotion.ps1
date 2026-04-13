$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$remotionDir = Join-Path $projectRoot "remotion-app"

if (-not (Test-Path (Join-Path $remotionDir "package.json"))) {
    throw "No se encontro remotion-app/package.json"
}

Push-Location $remotionDir
try {
    npm run dev
}
finally {
    Pop-Location
}
