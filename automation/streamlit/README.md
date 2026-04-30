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

- crear un lote diario de jobs por periodico desde la propia UI
- ver metricas por estado y fuente
- filtrar jobs por fuente, estado y texto
- revisar una bandeja de jobs
- ver portada, OCR, titulares, guion, audio, subtitulos y preview
- editar y aprobar guiones
- revisar y corregir `support_visual` por historia antes del rundown
- ejecutar etapas del pipeline desde botones
- preparar e importar seleccion manual de paginas desde varias portadas
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

Ya no necesitas crear un `job-manifest` por terminal para empezar.

Si `data/jobs/` todavia esta vacio, la app igual abre y muestra el bloque `Crear Lote Diario de Jobs`, desde donde puedes:

1. elegir fecha
2. seleccionar los periodicos
3. definir voice profile y approval mode
4. decidir si quieres descargar la portada al crear
5. crear el lote completo desde la UI

## Flujo recomendado desde la UI

1. abrir Streamlit
2. usar `Crear Lote Diario de Jobs`
3. si trabajas con varias portadas, usar `Seleccion Manual de Paginas desde Portadas`
4. seleccionar un job
5. ejecutar `Extract + Classify`
6. usar `Cover Pages` para analizar OCR, importar JSON manual o descargar paginas seleccionadas
7. ejecutar `Generate Draft`
8. revisar y aprobar el guion
9. revisar `support_visual` si el bloque editorial genero metricas, scorecards o graficos
10. ejecutar `Voice + Subtitle`
11. ejecutar `Build Story Manifest`
12. ejecutar `Compose Job para Preview`
13. abrir `npm run dev` y revisar `NewsVideo-generated`
14. preparar o confirmar la publicacion

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
