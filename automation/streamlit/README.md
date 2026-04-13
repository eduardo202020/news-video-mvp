# Streamlit Review App

App de Streamlit para operar y revisar el pipeline declarativo desde una UI local.

Este documento se enfoca en uso practico.

Para contexto de arquitectura:

- flujo general: [README.md](../../README.md)
- capa declarativa: [../README.md](../README.md)
- pipeline tecnico: [../architecture/pipeline.md](../architecture/pipeline.md)

## Preparacion recomendada

Antes de abrir Streamlit, lo mas comodo es preparar el entorno con:

```powershell
.\scripts\bootstrap.ps1
```

## Que hace

La app en `automation/streamlit/app.py` permite:

- ver metricas por estado y fuente
- filtrar jobs por fuente, estado y texto
- revisar una bandeja de jobs
- ver portada, OCR, titulares, guion, audio, subtitulos y preview
- editar y aprobar guiones
- ejecutar etapas del pipeline desde botones
- preparar publicacion declarativa
- revisar el timeline de eventos del job

## Como abrirla

Desde la raiz del repo y con `.venv` activado:

```powershell
streamlit run .\automation\streamlit\app.py
```

Alternativa:

```powershell
.\scripts\dev-streamlit.ps1
```

Si todavia no tienes Streamlit instalado:

```powershell
pip install -r .\automation\streamlit\requirements.txt
```

## Requisito minimo

La app necesita al menos un `job-manifest` en `data/jobs/`.

Si no existe ninguno, veras el mensaje:

```text
No se encontraron jobs en data/jobs/.
```

Puedes crear uno con:

```powershell
news-video-mvp-automation init-job `
  --source-config .\automation\sources\diarios\ojo.json `
  --date 2026-04-13 `
  --voice-profile .\automation\templates\voices\cuy-02.json `
  --video-template .\automation\templates\video\vertical-news.json `
  --front-page-image .\remotion-app\public\assets\covers\ojo.png
```

## Flujo recomendado desde la UI

1. abrir Streamlit
2. seleccionar un job
3. ejecutar `Extract + Classify`
4. ejecutar `Generate Draft`
5. revisar y aprobar el guion
6. ejecutar `Voice + Subtitle`
7. ejecutar `Build Story Manifest`
8. ejecutar `Compose Job para Preview`
9. abrir `npm run dev` y revisar `NewsVideo-generated`
10. preparar o confirmar la publicacion

## Relacion con Remotion

La app no renderiza video final por si sola.

Cuando ejecutas `compose-job` desde la UI:

- sincroniza assets en `remotion-app/public/assets/generated/`
- actualiza `remotion-app/src/generated-story.js`

Luego revisas el resultado en Remotion Studio:

```powershell
cd .\remotion-app
npm run dev
```

Composicion recomendada:

- `NewsVideo-generated`

## Nota

La app usa las mismas funciones del pipeline que la CLI, asi que UI y terminal comparten la misma logica.
