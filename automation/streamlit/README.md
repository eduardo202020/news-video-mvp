# Streamlit Review App

Streamlit encaja bien como capa de supervision para este proyecto.

No reemplaza los pipelines declarativos:

- los pipelines siguen viviendo en `job-manifest` y `story-manifest`
- Streamlit actua como panel para ver estado, corregir datos y aprobar etapas

## Casos de uso ideales

- listar jobs por fecha y estado
- visualizar la portada de un job
- mostrar OCR extraido y titulares candidatos
- editar el borrador del narrador
- aprobar o rechazar el guion
- disparar `build-story-manifest`
- previsualizar assets del video antes del render

## Flujo recomendado

1. pipeline crea o actualiza `job-manifest`
2. Streamlit lo lee
3. tu corriges o apruebas
4. Streamlit escribe de vuelta al manifiesto
5. el pipeline continua

## Siguiente paso sugerido

Crear una app con estas vistas:

- `Jobs`
- `OCR Review`
- `Script Review`
- `Compose Preview`
- `Publish Queue`

## Estado actual

Ya existe una primera app en `automation/streamlit/app.py`.

Permite:

- listar jobs desde `data/jobs/`
- ver estado, OCR y portada
- revisar `headline_candidates`
- editar `approved_text`
- guardar cambios
- aprobar el guion

## Como abrirla

```powershell
cd .\
streamlit run .\automation\streamlit\app.py
```

Si todavia no tienes Streamlit:

```powershell
pip install -r .\automation\streamlit\requirements.txt
```
