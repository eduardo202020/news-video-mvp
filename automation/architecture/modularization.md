# Modularizacion Propuesta

Esta es la separacion objetivo para convertir el repo en un pipeline mas mantenible y conectable con herramientas externas.

## Modulos

### `scraping/`

Responsabilidad:

- descargar portada y paginas relevantes
- guardar imagenes originales dentro del job
- registrar metadata de origen

Entrada:

- URLs de portada y paginas
- opcionalmente archivos ya descargados

Salida:

- `input_assets.front_page_image`
- `input_assets.pages[]`

### `script_generation/`

Responsabilidad:

- preparar el contexto editorial
- entregar a una IA externa las imagenes, OCR y titulares
- guardar el speech generado

Entrada:

- `input_assets`
- `extraction`

Salida:

- `script.draft`
- `script.approved_text`

### `voice_generation/`

Responsabilidad:

- convertir el speech en audio final
- permitir proveedores locales o externos

Entrada:

- `script.approved_text`
- perfil de voz

Salida:

- `voice.audio_path`

### `subtitles/`

Responsabilidad:

- alinear texto y audio
- producir segmentos de subtitulos

Entrada:

- `voice.audio_path`
- speech aprobado

Salida:

- `subtitles.segments_path`

### `video_composition/`

Responsabilidad:

- sincronizar audio, subtitulos, portadas, paginas y narrador
- preparar preview y render en Remotion

Entrada:

- `input_assets`
- `voice`
- `subtitles`
- `video`

Salida:

- `story-manifest.json`
- assets sincronizados para Remotion

### `orchestration/`

Responsabilidad:

- coordinar etapas
- actualizar estados del `job-manifest`
- ofrecer CLI y panel operativo

## Contrato minimo de job

```json
{
  "input_assets": {
    "front_page_image": "data/jobs/.../input/front-page.jpg",
    "front_page_url": "https://...",
    "pages": [
      {
        "role": "front_page",
        "label": "Portada",
        "page_number": 1,
        "source_url": "https://...",
        "local_path": "data/jobs/.../input/front-page.jpg"
      },
      {
        "role": "supporting_page",
        "label": "Pagina 2",
        "page_number": 2,
        "source_url": "https://...",
        "local_path": "data/jobs/.../input/pages/page-02.jpg"
      }
    ]
  },
  "script": {
    "provider": "manual_or_external_ai",
    "model": null,
    "draft": "",
    "approved_text": ""
  },
  "voice": {
    "provider": "system",
    "external_provider": null,
    "audio_path": null
  }
}
```

## Orden recomendado de implementacion

1. `scraping/`
2. contrato de `job-manifest`
3. `script_generation/`
4. `voice_generation/`
5. `subtitles/`
6. `video_composition/`
