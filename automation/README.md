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
