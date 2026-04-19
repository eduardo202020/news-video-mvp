# News Video MVP

Proyecto local para producir videos verticales de noticias a partir de portadas de periodicos.

Hoy el repo ya soporta dos formas de trabajo:

- flujo clasico para generar videos con Python + Remotion
- flujo declarativo para automatizar etapas con `job-manifest`, `story-manifest` y una app de Streamlit

Ademas, la base ya empezo a separarse en modulos de dominio para evolucionar hacia:

- `scraping/`
- `script_generation/`
- `voice_generation/`
- `subtitles/`
- `video_composition/`
- `orchestration/`

## Arquitectura

### Backend de orquestacion

- `src/news_video_mvp/cli.py`
  CLI clasica para render simple o secuencial.
- `src/news_video_mvp/project.py`
  Defaults del proyecto y resolucion de rutas base.
- `src/news_video_mvp/story_config.py`
  Carga y resolucion de historias JSON.
- `src/news_video_mvp/pipeline.py`
  Casos de uso de render simple, batch y secuencial.
- `src/news_video_mvp/composer.py`
  Sincroniza assets con Remotion, genera `generated-story.js` y puede renderizar el video final.
- `src/news_video_mvp/tts.py`
  Generacion o copia de audio TTS.
- `src/news_video_mvp/subtitles.py`
  Segmentacion base de subtitulos.

### Capa declarativa de automatizacion

- `automation/`
  Fuentes, reglas, templates, manifests y documentacion del pipeline.
- `src/news_video_mvp/automation_cli.py`
  CLI de automatizacion por etapas.
- `src/news_video_mvp/automation_pipeline.py`
  Logica de `init-job`, `extract-job`, `generate-script`, `approve-script`, `voice-job`, `build-story-manifest`, `compose-job` y `publish-job`.
- `automation/streamlit/app.py`
  Panel operativo para revisar jobs, ejecutar etapas y monitorear el pipeline.

### Frontend de video

- `remotion-app/src/Root.jsx`
  Registra composiciones para Studio y render.
- `remotion-app/src/generated-story.js`
  Ultima historia preparada para preview o render.
- `remotion-app/src/story/`
  Defaults, historias demo y normalizacion de props.
- `remotion-app/src/video/`
  Componentes visuales y timeline declarativo.

## Estructura importante

```text
automation/
  architecture/
  rules/
  sources/
  streamlit/
  templates/
data/
  jobs/
examples/
output/
remotion-app/
src/
```

## Preparar el entorno local

### Opcion recomendada: bootstrap automatico

Desde la raiz del repo:

```powershell
.\scripts\bootstrap.ps1
```

Si quieres instalar tambien el extra de Kokoro:

```powershell
.\scripts\bootstrap.ps1 -WithKokoro
```

Esto hace:

- crea `.venv` si no existe
- actualiza `pip`
- instala dependencias Python del proyecto
- instala dependencias de Streamlit
- ejecuta `npm install` en `remotion-app`

Despues puedes activar el entorno con:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Opcion manual

### 1. Crear el entorno virtual

Desde la raiz del repo:

```powershell
python -m venv .venv
```

### 2. Activar el entorno

Si estas en la raiz del repo:

```powershell
.\.venv\Scripts\Activate.ps1
```

Si estas dentro de `remotion-app`:

```powershell
& ..\.venv\Scripts\Activate.ps1
```

### 3. Instalar dependencias Python

```powershell
pip install -e .
pip install -r .\automation\streamlit\requirements.txt
```

Opcional para Kokoro:

```powershell
pip install -e .[kokoro]
```

### 4. Instalar dependencias de Remotion

```powershell
cd .\remotion-app
npm install
cd ..
```

## Scripts de desarrollo

Para levantar Streamlit y Remotion Studio sin escribir varios comandos:

```powershell
.\scripts\dev.ps1
```

Tambien puedes abrir cada servicio por separado:

```powershell
.\scripts\dev-streamlit.ps1
.\scripts\dev-remotion.ps1
```

Script de bootstrap:

```powershell
.\scripts\bootstrap.ps1
```

## Comandos principales

### CLI clasica

Render simple:

```powershell
news-video-mvp `
  --background .\input\calle.jpg `
  --gestures-dir .\input\narrator_gestures `
  --text "Resumen narrado de la noticia..." `
  --output .\output\noticia_tiktok.mp4
```

Render secuencial:

```powershell
news-video-mvp --story-config .\examples\periodicos-secuencia.json
```

### CLI de automatizacion

Inicializar un job:

```powershell
news-video-mvp-automation init-job `
  --source-config .\automation\sources\diarios\ojo.json `
  --date 2026-04-13 `
  --voice-profile .\automation\templates\voices\cuy-02.json `
  --video-template .\automation\templates\video\vertical-news.json `
  --front-page-image .\remotion-app\public\assets\covers\ojo.png
```

Inicializar un job incluyendo paginas adicionales:

```powershell
news-video-mvp-automation init-job `
  --source-config .\automation\sources\diarios\ojo.json `
  --date 2026-04-13 `
  --voice-profile .\automation\templates\voices\cuy-02.json `
  --video-template .\automation\templates\video\vertical-news.json `
  --front-page-url "https://sitio/portada.jpg" `
  --download-front-page `
  --supporting-page-url "https://sitio/pagina-2.jpg" `
  --supporting-page-url "https://sitio/pagina-3.jpg"
```

Adjuntar paginas a un job existente:

```powershell
news-video-mvp-automation scrape-pages `
  --job-manifest .\data\jobs\2026-04-13\2026-04-13-ojo-frontpage-001\job-manifest.json `
  --page-url "https://sitio/pagina-2.jpg" `
  --page-image .\input\pagina-3.jpg
```

Descubrir portada y paginas desde una fuente HTML:

```powershell
news-video-mvp-automation discover-source `
  --source-config .\automation\sources\diarios\ojo.json `
  --date 2026-04-18 `
  --source-url "https://tu-fuente-real.example/portada"
```

Descubrir portadas/paginas desde el patron `t.prcdn.co`:

```powershell
news-video-mvp-automation discover-source `
  --source-config .\automation\sources\diarios\ojo.json `
  --date 2026-04-18
```

En fuentes `prcdn`, el scraper ahora intenta el mayor `scale` disponible por pagina dentro del rango configurado.
Hoy la configuracion base usa `scale_start=46` y `scale_end=300` para priorizar la mejor resolucion posible para OCR/analisis.

Scrapear la fuente directamente a un job:

```powershell
news-video-mvp-automation scrape-source-job `
  --job-manifest .\data\jobs\2026-04-18\2026-04-18-ojo-frontpage-001\job-manifest.json `
  --source-config .\automation\sources\diarios\ojo.json `
  --source-url "https://tu-fuente-real.example/portada" `
  --force
```

Archivar una fuente por fecha en `data/raw`:

```powershell
news-video-mvp-automation archive-source `
  --source-config .\automation\sources\diarios\ojo.json `
  --date 2026-04-18 `
  --max-supporting-pages 3 `
  --retention-days 7
```

Archivar todos los periodicos configurados:

```powershell
news-video-mvp-automation archive-all-sources `
  --sources-dir .\automation\sources\diarios `
  --date 2026-04-18 `
  --max-supporting-pages 3 `
  --retention-days 7
```

Esto genera carpetas como:

- `data/raw/ojo/2026-04-18/`
- `data/raw/trome/2026-04-18/`
- `data/raw/elcomercio/2026-04-18/`

y conserva solo hasta una semana de antiguedad por fuente.

Extraer OCR y clasificar:

```powershell
news-video-mvp-automation extract-job `
  --job-manifest .\data\jobs\2026-04-13\2026-04-13-ojo-frontpage-001\job-manifest.json `
  --editorial-policy .\automation\rules\editorial-policy.json `
  --ocr-text "OJO. Crisis en el gobierno. Congreso exige respuestas inmediatas."
```

Generar draft:

```powershell
news-video-mvp-automation generate-script `
  --job-manifest .\data\jobs\2026-04-13\2026-04-13-ojo-frontpage-001\job-manifest.json `
  --script-template .\automation\templates\scripts\default-anchor.json
```

Preparar paquete para generar el speech manualmente en ChatGPT:

```powershell
news-video-mvp-automation prepare-script-package `
  --job-manifest .\data\jobs\2026-04-13\2026-04-13-ojo-frontpage-001\job-manifest.json `
  --script-template .\automation\templates\scripts\default-anchor.json
```

Eso genera en `review/script-package/`:

- `script-request.json`
- `chatgpt-prompt.md`
- `images-to-upload.txt`

Importar el speech generado por ChatGPT:

```powershell
news-video-mvp-automation import-script `
  --job-manifest .\data\jobs\2026-04-13\2026-04-13-ojo-frontpage-001\job-manifest.json `
  --generated-text-file .\data\jobs\2026-04-13\2026-04-13-ojo-frontpage-001\review\mi-speech.txt `
  --provider chatgpt_plus_manual `
  --approve
```

Importar paginas seleccionadas manualmente para un job:

```powershell
news-video-mvp-automation import-cover-pages `
  --job-manifest .\data\jobs\2026-04-19\2026-04-19-ojo-frontpage-001\job-manifest.json `
  --selection-file .\data\ocr-imports\2026-04-19-ojo\manual-selection.json `
  --provider chatgpt_plus_manual `
  --force
```

Importar paginas seleccionadas manualmente para varios jobs a la vez:

```powershell
news-video-mvp-automation import-cover-pages-batch `
  --selection-file .\data\ocr-imports\2026-04-19\cover-selections-batch.json `
  --provider chatgpt_plus_manual `
  --force
```

Descargar solo las paginas seleccionadas de un job:

```powershell
news-video-mvp-automation scrape-selected-pages `
  --job-manifest .\data\jobs\2026-04-19\2026-04-19-ojo-frontpage-001\job-manifest.json `
  --source-config .\automation\sources\diarios\ojo.json `
  --force
```

Aprobar guion:

```powershell
news-video-mvp-automation approve-script `
  --job-manifest .\data\jobs\2026-04-13\2026-04-13-ojo-frontpage-001\job-manifest.json `
  --review-notes "Aprobado para locucion"
```

Generar voz y subtitulos:

```powershell
news-video-mvp-automation voice-job `
  --job-manifest .\data\jobs\2026-04-13\2026-04-13-ojo-frontpage-001\job-manifest.json `
  --voice-profile .\automation\templates\voices\cuy-02.json `
  --subtitle-policy .\automation\rules\subtitle-policy.json
```

Listar perfiles locales de Voicebox:

```powershell
news-video-mvp-automation list-voicebox-profiles
```

Transcribir un audio del job con Voicebox:

```powershell
news-video-mvp-automation transcribe-job `
  --job-manifest .\data\jobs\2026-04-18\2026-04-18-voicebox-test\job-manifest.json `
  --voice-profile .\automation\templates\voices\voicebox-local.json
```

Usar Voicebox local para la voz:

```powershell
news-video-mvp-automation voice-job `
  --job-manifest .\data\jobs\2026-04-13\2026-04-13-ojo-frontpage-001\job-manifest.json `
  --voice-profile .\automation\templates\voices\voicebox-local.json `
  --subtitle-policy .\automation\rules\subtitle-policy.json
```

Notas para Voicebox:

- instala y abre Voicebox local antes de ejecutar `voice-job`
- por defecto se usa `http://localhost:17493`
- cambia `tts_voice` en [voicebox-local.json](C:/Users/pc/Documents/proyectos/news-video-mvp/automation/templates/voices/voicebox-local.json:1) por el `profile_id` real de tu voz clonada
- si tu instancia usa otra URL, ajusta `provider_settings.api_url` o la variable `VOICEBOX_API_URL`
- `transcribe-job` usa el audio del job por defecto, o uno externo con `--audio-file`

Construir story manifest:

```powershell
news-video-mvp-automation build-story-manifest `
  --job-manifest .\data\jobs\2026-04-13\2026-04-13-ojo-frontpage-001\job-manifest.json `
  --voice-profile .\automation\templates\voices\cuy-02.json `
  --video-template .\automation\templates\video\vertical-news.json
```

Preparar preview en Remotion sin render final:

```powershell
news-video-mvp-automation compose-job `
  --job-manifest .\data\jobs\2026-04-13\2026-04-13-ojo-frontpage-001\job-manifest.json `
  --video-template .\automation\templates\video\vertical-news.json
```

Preparar publicacion:

```powershell
news-video-mvp-automation publish-job `
  --job-manifest .\data\jobs\2026-04-13\2026-04-13-ojo-frontpage-001\job-manifest.json `
  --publishing-profile .\automation\templates\publishing\tiktok.json `
  --confirm
```

## Flujo recomendado de trabajo

### Flujo manual recomendado para varias portadas

1. descubre o descarga solo la portada de cada periodico y crea un job por periodico
2. abre [cover-page-selection-batch.md](./automation/templates/prompts/cover-page-selection-batch.md)
3. reemplaza `{{PORTADAS}}` por una lista como esta:

```text
- portada 1
  newspaper_name: Ojo
  job_id: 2026-04-19-ojo-frontpage-001
  job_manifest_path: data/jobs/2026-04-19/2026-04-19-ojo-frontpage-001/job-manifest.json
- portada 2
  newspaper_name: Trome
  job_id: 2026-04-19-trome-frontpage-001
  job_manifest_path: data/jobs/2026-04-19/2026-04-19-trome-frontpage-001/job-manifest.json
```

4. sube todas las portadas al mismo chat y pega el prompt
5. guarda la respuesta JSON usando como referencia [cover-page-selection-batch.example.json](./automation/templates/prompts/cover-page-selection-batch.example.json)
6. importa el lote con `import-cover-pages-batch`
7. para cada job, ejecuta `scrape-selected-pages`

### Flujo 1: Preview rapido con Streamlit + Remotion

1. activa `.venv`
2. abre Streamlit
3. crea o carga un job
4. ejecuta etapas hasta `compose-job`
5. abre Remotion Studio con `npm run dev`
6. revisa `NewsVideo-generated`

Abrir Streamlit:

```powershell
streamlit run .\automation\streamlit\app.py
```

Abrir Remotion Studio:

```powershell
cd .\remotion-app
npm run dev
```

Alternativa rapida:

```powershell
.\scripts\dev.ps1
```

Uso recomendado en Studio:

1. `NewsVideo-generated`
   Ultima historia preparada por el pipeline declarativo.
2. `NewsVideo`
   Composicion base de trabajo.
3. demos fijas como `NewsVideo-periodicos-secuencia-demo`

### Flujo 2: Render final tradicional

1. prepara assets o story config
2. corre la CLI clasica
3. revisa salida en `output/`

### Flujo 3: Pipeline declarativo completo

1. `init-job`
2. `extract-job`
3. `generate-script`
4. `approve-script`
5. `voice-job`
6. `build-story-manifest`
7. `compose-job`
8. revisar en `npm run dev`
9. `publish-job`
10. opcionalmente render final

## Como usar Streamlit

La app de Streamlit sirve como panel operativo. No reemplaza el pipeline; lo controla.

Hoy permite:

- ver metricas por estado y fuente
- filtrar jobs
- revisar OCR, titulares, guion, audio, subtitulos y preview
- ejecutar etapas del pipeline desde botones
- editar y aprobar guiones
- preparar publicacion declarativa
- inspeccionar el timeline de eventos del job

Si al abrirla aparece:

```text
No se encontraron jobs en data/jobs/.
```

todavia no existe ningun `job-manifest`. Crea uno primero con `init-job`.

## Ejemplo minimo para poblar Streamlit

```powershell
news-video-mvp-automation init-job `
  --source-config .\automation\sources\diarios\ojo.json `
  --date 2026-04-13 `
  --voice-profile .\automation\templates\voices\cuy-02.json `
  --video-template .\automation\templates\video\vertical-news.json `
  --front-page-image .\remotion-app\public\assets\covers\ojo.png
```

Luego recarga Streamlit y el job aparecera en el panel.

## Flujo de preview sin render pesado

Si quieres iterar rapido, el camino recomendado es:

1. llegar hasta `compose-job`
2. abrir `npm run dev`
3. revisar `NewsVideo-generated`

Eso actualiza:

- `remotion-app/public/assets/generated/`
- `remotion-app/src/generated-story.js`

sin lanzar `remotion render`.

## Donde tocar cada cosa

### Plantillas declarativas

- fuentes: `automation/sources/`
- reglas: `automation/rules/`
- guion: `automation/templates/scripts/`
- voces: `automation/templates/voices/`
- video: `automation/templates/video/`
- publicacion: `automation/templates/publishing/`

### UI de operaciones

- `automation/streamlit/app.py`

### Layout de video

- `remotion-app/src/NewsVideo.jsx`
- `remotion-app/src/video/CoverStage.jsx`
- `remotion-app/src/video/NarratorStage.jsx`
- `remotion-app/src/video/CaptionBar.jsx`
- `remotion-app/src/video/constants.js`

## Convenciones actuales

- formato vertical: `1080 x 1920`
- subtitulos maximo 2 lineas
- audio principal en espanol
- fondo musical suave en `public/assets/fondo-musical/`
- narradores actuales:
  - `Cuy-01`
  - `Cuy-02`
  - `Cuy-Depor`

## Troubleshooting

- si PowerShell no encuentra `Activate.ps1`, revisa desde que carpeta estas ejecutando el comando
- si Streamlit no muestra jobs, primero crea uno con `init-job`
- si `compose-job` falla, revisa que el job tenga audio y `story-manifest`
- si `npm run dev` muestra un estado viejo, reinicia Studio
- si el audio o assets no aparecen en Studio, revisa `remotion-app/src/generated-story.js`
- si el fondo musical no suena, valida el archivo dentro de `public/assets/fondo-musical/`

## Documentacion relacionada

- [automation/README.md](./automation/README.md)
- [automation/architecture/pipeline.md](./automation/architecture/pipeline.md)
- [automation/streamlit/README.md](./automation/streamlit/README.md)
- [remotion-app/README.md](./remotion-app/README.md)
