# Automation Layer

Esta carpeta concentra la capa declarativa de automatizacion del proyecto.

El `README.md` principal explica el flujo operativo completo:

- entorno virtual
- instalacion
- CLI clasica
- CLI de automatizacion
- Streamlit
- preview con Remotion

Este documento queda como referencia tecnica de la capa `automation/`.

La preparacion del entorno y el flujo operativo general viven en:

- [README.md](../README.md)

## Objetivo

La idea es separar configuracion y ejecucion:

- fuentes en `automation/sources/`
- reglas en `automation/rules/`
- templates en `automation/templates/`
- estados y trazabilidad en `job-manifest`
- contrato entre editorial y render en `story-manifest`

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
  streamlit/
    app.py
    README.md
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

## Contratos principales

### Source config

Describe como descubrir o leer una fuente.

Ejemplos:

- `automation/sources/diarios/ojo.json`
- `automation/sources/diarios/libero.json`

Campos tipicos:

- `source_id`
- `display_name`
- `base_url`
- `discovery`
- `selectors`
- `storage`
- `ocr_hints`
- `schedule`

### Job manifest

Representa el estado operativo de una portada o job editorial.

Template:

- `automation/jobs/templates/job-manifest.json`

Responsabilidades:

- guardar input assets
- guardar OCR y clasificacion
- guardar draft y aprobacion
- guardar audio, subtitulos y preview
- guardar metadata de publicacion
- guardar auditoria de etapas

### Story manifest

Es el contrato entre la capa editorial y la capa de video.

Template:

- `automation/jobs/templates/story-manifest.json`

Responsabilidades:

- definir segmentos
- indicar fondo, musica y narrador
- declarar archivos de audio y subtitulos
- servir de entrada para la composicion visual

## Reglas y templates

### Rules

- `automation/rules/editorial-policy.json`
  Reglas heuristicas para clasificar noticia vs publicidad.
- `automation/rules/subtitle-policy.json`
  Politica de subtitulos legibles para video vertical.

### Templates

- `automation/templates/scripts/default-anchor.json`
  Plantilla base para speech del narrador.
- `automation/templates/video/vertical-news.json`
  Template principal del video vertical.
- `automation/templates/voices/*.json`
  Perfiles de voz y narrador.
- `automation/templates/publishing/tiktok.json`
  Perfil declarativo de publicacion.

## Etapas ya implementadas

Estas etapas ya existen en `src/news_video_mvp/automation_pipeline.py` y se exponen por CLI y Streamlit:

- `init-job`
- `extract-job`
- `prepare-script-package`
- `generate-script`
- `import-script`
- `approve-script`
- `voice-job`
- `build-story-manifest`
- `compose-job`
- `publish-job`

## Estado actual

Hoy la automatizacion ya permite:

- crear jobs declarativos
- cargar OCR externo o sidecar
- clasificar portada como noticia o publicidad
- preparar un paquete para ChatGPT con imagenes y contexto del job
- generar draft del narrador
- importar un speech escrito externamente
- sintetizar voz local con Voicebox via REST API local
- aprobar texto final
- generar audio y subtitulos
- construir `story-manifest`
- preparar preview para `NewsVideo-generated`
- preparar metadata declarativa de publicacion

## Limites actuales

- `extract-job` todavia no hace OCR directo; espera OCR externo o sidecar `.txt`
- `publish-job` aun no llama una API real de plataforma
- el timing de subtitulos sigue siendo segmentado por texto, no por alineacion palabra a palabra

## Siguiente evolucion natural

Las siguientes mejoras encajan bien sobre esta base:

1. OCR real desde libreria o servicio
2. aprobacion y creacion de jobs desde Streamlit
3. alineacion real audio-subtitulo
4. integracion con una API real de publicacion

## Documentacion relacionada

- [README.md](../README.md)
- [architecture/pipeline.md](./architecture/pipeline.md)
- [architecture/modularization.md](./architecture/modularization.md)
- [streamlit/README.md](./streamlit/README.md)
