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
- los perfiles en `automation/templates/voices/` ya pueden apuntar a voces clonadas distintas por narrador, no solo al fallback `voicebox-local`
- cambia `tts_voice` en [voicebox-local.json](C:/Users/pc/Documents/proyectos/news-video-mvp/automation/templates/voices/voicebox-local.json:1) o en el perfil del narrador por el `profile_id` real de tu voz clonada
- si tu instancia usa otra URL, ajusta `provider_settings.api_url` o la variable `VOICEBOX_API_URL`
- si alguna voz tarda mucho, sube `generation_timeout_seconds` en `provider_settings`
- `transcribe-job` usa el audio del job por defecto, o uno externo con `--audio-file`
- la CLI `list-voicebox-profiles` te ayuda a verificar nombres, descripciones e IDs reales antes de mapear una voz nueva al pipeline

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

### Estado actual del flujo

Hoy el flujo activo y mas avanzado del repo es este:

1. scrapear solo las portadas y crear un job por periodico
2. usar un prompt manual en ChatGPT para detectar noticias principales de portada
3. importar esa seleccion a los `job-manifest`
4. descargar solo las paginas internas necesarias como contexto editorial
5. usar un segundo prompt para obtener speeches editoriales breves por noticia
6. convertir esos speeches en narrativa util para video, usando `story_type` para asignar narrador, `cover_region` para hacer zoom sobre la portada y una capa separada de `voz_en_off` para apertura, conectores y comentarios puente

Importante:

- en el video final la idea actual es mostrar solo la portada
- las paginas internas no son assets visuales finales; se descargan solo para entender mejor cada noticia
- la unidad narrativa real ya no es la pagina, sino la noticia detectada en portada
- el proyecto de ChatGPT que genera los speeches debe cargar las fuentes en `fuentes-chatgpt/`, que ya reflejan el casting actual de narradores y sus categorias

### Flujo operativo en Streamlit

La app de Streamlit ya soporta este flujo semi-manual:

1. `Scrapear periodicos`
2. revisar `Portadas y Prompt`
3. `Abrir carpeta de portadas`
4. `Copiar prompt`
5. pegar la respuesta JSON de ChatGPT en `Importar Seleccion Batch`
6. aplicar opcionalmente `Filtro editorial del lote`
7. `Descargar paginas del lote`
8. revisar `Ver resultado de descarga de paginas` con miniaturas
9. usar los prompts por bloques de 2 periodicos para resumir las paginas descargadas

Abrir Streamlit:

```powershell
.\.venv\Scripts\python.exe -m streamlit run .\automation\streamlit\app.py
```

Atajo:

```powershell
.\scripts\dev-streamlit.ps1
```

### Que devuelve hoy el primer prompt

El prompt de portadas devuelve JSON por job con `items` como estos:

- `headline`
- `story_type`
- `cover_region`
- `page_number`
- `confidence`
- `evidence_line`

Internamente, al importar, el pipeline conserva:

- `page_selection.candidates`
- `page_selection.selected_page_numbers`
- `page_selection.stories`

`page_selection.stories` ya agrupa automaticamente paginas repetidas de una misma noticia y es la base correcta para la capa narrativa.

### Que hace hoy el segundo prompt

El prompt que se usa sobre paginas internas ya no busca un resumen largo. Ahora produce:

- un `speech` final breve por noticia
- `narrator_profile_id`
- `tone_notes`
- `key_facts_used`
- `safety_notes`
- conservacion de `page_numbers`, `cover_region` y `story_type` por historia

Ese prompt ya asume que:

- las paginas internas sirven solo como contexto
- el speech final sera corto, tipo TikTok
- luego el video debe hablar sobre la portada, no sobre las paginas interiores
- la apertura y los cambios de periodico usan perfiles de `voz_en_off`, separados de los narradores principales de cada historia
- el proyecto de ChatGPT toma como referencia `fuentes-chatgpt/narrator-profiles.json` y `fuentes-chatgpt/story-type-mapping.json`

### Uso recomendado hoy

Si quieres avanzar rapido con el flujo actual:

1. trabaja desde Streamlit hasta descargar paginas
2. usa los prompts generados por la misma app
3. guarda los JSON devueltos por ChatGPT en `data/ocr-imports/`
4. deja Remotion para la siguiente etapa, cuando ya exista la capa narrativa cerrada

## Como usar Streamlit

La app de Streamlit es hoy el panel principal del pipeline manual-asistido.

Ya permite:

- crear un lote diario de jobs, uno por periodico
- descargar portadas
- mostrar solo un job activo por fuente
- copiar el prompt dinamico de portadas
- importar seleccion batch desde ChatGPT
- aplicar filtro editorial por categoria, suplementos o palabras clave
- descargar paginas del lote reutilizando las ya existentes cuando coinciden
- mostrar miniaturas de paginas descargadas
- generar prompts posteriores por bloques de 2 periodicos
- importar desde Streamlit el JSON del segundo prompt con speeches editoriales por historia
- ajustar manualmente `cover_region` por historia desde Streamlit
- corregir enfoque por cualquier periodico del lote desde `Ajuste Manual de Enfoque del Lote`
- ver una previsualizacion inmediata del recorte antes de guardar el zoom

Si al abrirla aparece:

```text
No se encontraron jobs en `data/jobs/`.
```

todavia no existe ningun lote diario. Crea uno desde la misma UI o con CLI.

## Lo que ya quedo implementado

- scraping de portadas por lote diario desde Streamlit
- recorte automatico de margenes blancos en portadas nuevas al descargarlas o copiarlas al job
- un job visible por periodico en la UI
- prompt dinamico para varias portadas
- importacion batch del JSON devuelto por ChatGPT
- soporte para `story_type`
- soporte para `cover_region` normalizado
- agrupacion interna por historias en `page_selection.stories`
- filtro editorial del lote antes de descargar paginas
- descarga batch de paginas seleccionadas
- reutilizacion de paginas ya descargadas cuando coincide la seleccion
- miniaturas de paginas descargadas por periodico
- prompts posteriores por bloques de 2 periodicos para respetar el limite de imagenes de ChatGPT
- speeches editoriales pensados para voz breve, no para nota larga
- modo desarrollo en Streamlit para cachear respuestas pegadas de ChatGPT y recargarlas al reabrir la app
- importacion de speeches editoriales con enriquecimiento automatico desde portada
- manifiesto narrativo intermedio por job para conectar historias importadas con `story-manifest`
- mapeo formal `story_type -> narrator_profile_id` desde `automation/templates/narrators/story-type-map.json`
- separacion formal entre narradores de noticia y voces de `voz_en_off` para intro, conectores y comentarios puente
- integracion de voces reales de Voicebox por categoria editorial, incluyendo politica, policial, espectaculos, economia y deportes
- construccion de `programa diario` para preview desde Streamlit
- modo desarrollo del `programa diario` para trabajar solo con intro + primer bloque de 2 periodicos
- reintento del `programa diario` desde audios existentes, sin volver a generar TTS cuando ya existe una corrida previa
- reutilizacion automatica del ultimo rundown del dia como semilla al reconstruir el `programa diario`
- reconstruccion del `programa diario` respetando cambios guardados de `cover_region` aunque se reutilicen audios
- feedback por etapas durante la construccion del `programa diario`
- sincronizacion del preview diario con `NewsVideo-generated` en Remotion
- soporte de segmentos narrativos con intro, historias y conectores entre periodicos
- transicion entre diarios sin tarjeta central que tape la portada
- uso de `cover_region` en Remotion para zoom por noticia sobre la portada
- transicion visual entre noticias del mismo diario para volver a portada completa antes del siguiente zoom
- intro animada en Remotion con aparicion secuencial de portadas de periodicos y fecha visible en la apertura
- subtitulos sincronizados por segmentos reales de audio, incluyendo conectores entre periodicos
- subtitulos partidos en bloques practicos de hasta 2 lineas
- ajuste visual del bloque de subtitulos para ancho, posicion y lectura
- velocidad de voz configurable desde los perfiles TTS, con base actual de `1.4`
- optimizaciones visuales del preview para reducir costo de exportacion

## Lo que falta

### Capa editorial / datos

- seguir afinando el prompt editorial para cubrir todas las historias detectadas sin inventar ni omitir casos limite
- documentar mejor el contrato del manifiesto narrativo intermedio y sus campos finales

### Capa de video

- seguir afinando el balance entre cantidad de palabras por bloque y comodidad de lectura en subtitulos
- validar en renders largos la velocidad de voz `1.4x` y ajustar por narrador si hace falta
- seguir afinando la intro de portadas para que la secuencia inicial quede cerrada visualmente
- seguir afinando el comportamiento del zoom sobre portadas grandes o de composicion irregular
- seguir puliendo la posicion relativa entre portadas, subtitulos y narrador para distintos diarios

### Automatizacion futura

- reemplazar el paso manual de ChatGPT por API de OpenAI
- automatizar de punta a punta la seleccion desde portada
- automatizar la generacion del micro-script por noticia

### Limpieza / producto

- revisar si conviene ocultar aun mas informacion en Streamlit para dejarlo como wizard de pocos pasos
- documentar mejor el formato del manifiesto narrativo futuro
- consolidar README secundarios cuando el flujo ya no cambie tanto

## Flujo de preview sin render pesado

La parte de preview con Remotion sigue disponible, pero aun no esta cerrada para este nuevo flujo de portadas con zoom narrativo.

Cuando exista `story-manifest` listo:

1. ejecutar `compose-job`
2. abrir `npm run dev`
3. revisar `NewsVideo-generated`

Eso actualiza:

- `remotion-app/public/assets/generated/`
- `remotion-app/src/generated-story.js`

sin lanzar `remotion render`.

Para el `programa diario`, el flujo practico hoy es:

1. construir el preview rapido en modo desarrollo si quieres validar voces y ritmo
2. corregir speeches o `cover_region` desde Streamlit si hace falta
3. reconstruir el `programa diario`

Si ya existe una corrida previa del mismo dia, la app intenta reutilizar audios existentes y solo actualiza manifests + Remotion cuando el texto no cambio.

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
- velocidad base de voz actual: `1.4`
- fondo musical suave en `public/assets/fondo-musical/`
- el fallback de voz suele vivir en `voicebox-local.json`
- los narradores editoriales reales se resuelven desde `automation/templates/narrators/story-type-map.json`
- cada narrador puede usar su propio perfil de Voicebox en `automation/templates/voices/`
- el proyecto de ChatGPT consume sus fuentes desde `fuentes-chatgpt/`, no solo desde `proyect.md`
- categorias activas hoy en el casting:
- `voz_en_off`: `thanos`, `narrador_dbz`, `skipper`, `ironman`
- `politica`: `beto_ortiz`, `jaime_bayly`, `ted`
- `economia`: `jaime_bayly`, `ted`
- `deportes`: `mr_peet`, `gonzalo_nunez`
- `policial`: `reportero_panorama`
- `espectaculos`: `reportero_magaly`, `reportera_magaly`

## Troubleshooting

- si PowerShell no encuentra `Activate.ps1`, revisa desde que carpeta estas ejecutando el comando
- si Streamlit no muestra jobs, primero crea uno con `init-job`
- si `compose-job` falla, revisa que el job tenga audio y `story-manifest`
- si `npm run dev` muestra un estado viejo, reinicia Studio
- si el audio o assets no aparecen en Studio, revisa `remotion-app/src/generated-story.js`
- si el fondo musical no suena, valida el archivo dentro de `public/assets/fondo-musical/`
- si ajustaste un zoom y no lo ves reflejado, guarda el enfoque y reconstruye o reintenta el `programa diario` desde audios existentes
- si Voicebox tarda demasiado y corta la generacion, sube `generation_timeout_seconds` en el perfil de voz usado

## Documentacion relacionada

- [automation/README.md](./automation/README.md)
- [automation/architecture/pipeline.md](./automation/architecture/pipeline.md)
- [automation/streamlit/README.md](./automation/streamlit/README.md)
- [remotion-app/README.md](./remotion-app/README.md)
