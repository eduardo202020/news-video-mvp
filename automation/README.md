# Automation Layer

Esta carpeta define la capa declarativa para automatizar el proyecto de punta a punta.

Objetivo:

- describir fuentes, reglas, voces y publicaciones sin hardcodear logica
- separar cada etapa del pipeline con contratos claros
- permitir aprobacion humana en puntos especificos
- dejar trazabilidad completa por job

## Estructura

```text
automation/
  README.md
  architecture/
    pipeline.md
  jobs/
    templates/
      job-manifest.json
      story-manifest.json
  rules/
    editorial-policy.json
    subtitle-policy.json
  sources/
    diarios/
      libero.json
      ojo.json
      trome.json
  templates/
    publishing/
      tiktok.json
    scripts/
      default-anchor.json
    video/
      vertical-news.json
    voices/
      cuy-01.json
      cuy-02.json
      cuy-depor.json
```

## Pipeline objetivo

1. `ingest`
   Descubre o descarga portadas y metadata de fuentes.
2. `extract`
   Ejecuta OCR, limpia bloques y clasifica noticia vs publicidad.
3. `select`
   Decide si la portada entra al flujo editorial.
4. `script`
   Genera el speech del narrador.
5. `review`
   Espera aprobacion humana cuando el modo del job lo requiera.
6. `voice`
   Genera audio y timestamps.
7. `subtitle`
   Construye subtitulos sincronizados.
8. `compose`
   Arma el manifiesto final del video.
9. `render`
   Produce assets y video.
10. `publish`
    Publica y registra resultado.

## Comandos disponibles

Inicializar un job declarativo:

```powershell
news-video-mvp-automation init-job `
  --source-config .\automation\sources\diarios\ojo.json `
  --date 2026-04-13 `
  --voice-profile .\automation\templates\voices\cuy-02.json `
  --video-template .\automation\templates\video\vertical-news.json `
  --front-page-image .\remotion-app\public\assets\covers\ojo.png
```

Construir el `story-manifest` desde un job ya editado o aprobado:

```powershell
news-video-mvp-automation build-story-manifest `
  --job-manifest .\data\jobs\2026-04-13\2026-04-13-ojo-frontpage-001\job-manifest.json `
  --voice-profile .\automation\templates\voices\cuy-02.json `
  --video-template .\automation\templates\video\vertical-news.json
```

Extraer OCR y clasificar la portada:

```powershell
news-video-mvp-automation extract-job `
  --job-manifest .\data\jobs\2026-04-13\2026-04-13-ojo-frontpage-001\job-manifest.json `
  --editorial-policy .\automation\rules\editorial-policy.json `
  --ocr-text-file .\data\ocr\ojo-2026-04-13.txt `
  --ocr-confidence 0.82
```

Generar el borrador del narrador:

```powershell
news-video-mvp-automation generate-script `
  --job-manifest .\data\jobs\2026-04-13\2026-04-13-ojo-frontpage-001\job-manifest.json `
  --script-template .\automation\templates\scripts\default-anchor.json
```

Aprobar el guion:

```powershell
news-video-mvp-automation approve-script `
  --job-manifest .\data\jobs\2026-04-13\2026-04-13-ojo-frontpage-001\job-manifest.json `
  --review-notes "Ajustado tono y aprobado para locucion"
```

Generar voz y subtitulos:

```powershell
news-video-mvp-automation voice-job `
  --job-manifest .\data\jobs\2026-04-13\2026-04-13-ojo-frontpage-001\job-manifest.json `
  --voice-profile .\automation\templates\voices\cuy-02.json `
  --subtitle-policy .\automation\rules\subtitle-policy.json
```

Nota:

- `init-job` no renderiza video
- `extract-job` no renderiza video
- `generate-script` no renderiza video
- `approve-script` no renderiza video
- `voice-job` no renderiza video
- `build-story-manifest` tampoco renderiza
- ambos comandos estan pensados para ser rapidos y compatibles con tu flujo usando `npm run dev`

## Modo de aprobacion

El job debe definir uno de estos modos:

- `manual`
- `semi_auto`
- `full_auto`

Punto recomendado de aprobacion:

- despues de `script`
- opcionalmente despues de `compose`

## Estado minimo de un job

- `discovered`
- `scraped`
- `extracted`
- `classified`
- `scripted`
- `review_pending`
- `approved`
- `voiced`
- `subtitled`
- `composed`
- `rendered`
- `published`
- `failed`
