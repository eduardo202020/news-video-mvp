# Pipeline Architecture

## Principios

1. Cada etapa consume un manifiesto y produce otro.
2. Ninguna etapa debe depender de paths sueltos no declarados.
3. Toda decision automatica debe quedar registrada.
4. La aprobacion humana debe ser una capacidad del pipeline, no una excepcion manual.

## Contratos

### 1. Source config

Define como leer una fuente.

Campos sugeridos:

- `source_id`
- `display_name`
- `base_url`
- `discovery`
- `selectors`
- `storage`
- `ocr_hints`
- `schedule`

### 2. Job manifest

Representa una corrida editorial de una portada o grupo de portadas.

Campos sugeridos:

- `job_id`
- `source_id`
- `date`
- `approval_mode`
- `status`
- `input_assets`
- `extraction`
- `classification`
- `script`
- `voice`
- `subtitles`
- `video`
- `publication`
- `audit`

### 3. Story manifest

Es el contrato entre la capa editorial y el render.

Campos sugeridos:

- `story_id`
- `video_template`
- `background`
- `music`
- `segments`
- `subtitle_policy`
- `render_output`

## Etapas detalladas

### Ingest

Entrada:

- source config
- fecha objetivo

Salida:

- portada descargada
- html o snapshot si aplica
- metadata de fuente

### Extract

Entrada:

- imagen
- html o pdf
- hints OCR

Salida:

- titulares detectados
- bloques OCR
- score de confianza
- bloques candidatos a publicidad

### Classify

Entrada:

- texto extraido
- reglas editoriales

Salida:

- noticia valida o descartada
- razon de descarte
- prioridad editorial

### Script

Entrada:

- titulares limpios
- plantilla de guion

Salida:

- narracion final
- variantes
- notas editoriales

### Review

Entrada:

- job manifest en estado `scripted`

Salida:

- `approved` o `rejected`
- comentarios

### Voice + Subtitle

Entrada:

- texto aprobado
- perfil de voz
- politica de subtitulos

Salida:

- audio
- timestamps por palabra o frase
- subtitulos

### Compose

Entrada:

- story manifest
- template de video

Salida:

- props finales para Remotion

### Render

Entrada:

- props finales

Salida:

- mp4
- preview
- thumbnail

### Publish

Entrada:

- asset final
- perfil de publicacion

Salida:

- platform post id
- url
- estado final

## Recomendacion de implementacion

Empieza con estos modulos:

- `automation/sources/`
- `automation/rules/`
- `automation/templates/`
- `data/jobs/<date>/<job_id>/`

Y luego crea orquestadores chicos:

- `discover_sources`
- `extract_front_page`
- `classify_front_page`
- `generate_script`
- `approve_script`
- `generate_voice`
- `generate_subtitles`
- `build_story_manifest`
- `render_story`
- `publish_video`

## Estado actual en el repo

Ya existen bases para:

- `init-job`
- `extract-job`
- `generate-script`
- `approve-script`
- `voice-job`
- `compose-job`
- `publish-job`
- `build-story-manifest`

`extract-job` hoy espera OCR externo o texto sidecar y aplica clasificacion heuristica.
Mas adelante se puede reemplazar esa entrada por OCR directo desde una libreria o servicio.
