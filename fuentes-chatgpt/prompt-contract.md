# Prompt Contract

Cada solicitud al proyecto incluira:
- metadatos del bloque
- job_id
- newspaper_name
- historias detectadas desde portada
- story_type
- headline
- summary
- page_numbers
- cover_region
- key_facts
- notes
- imagenes adjuntas de paginas internas
- opcion de devolver `support_visual` cuando la historia necesite contexto numerico

El modelo debe:
1. leer los metadatos
2. usar las imagenes como verificacion
3. asignar narrator_profile_id segun story-type-mapping.json
4. escribir speech segun narrator-profiles.json
5. si una historia mejora con datos de crecimiento, avance, porcentajes, precios, votos, ranking o comparaciones, buscar contexto numerico confiable y devolver `support_visual`
6. respetar speech-style-rules.md y speech-safety-rules.md
7. devolver solo JSON valido segun output-schema.json

Notas operativas:
- `voz_en_off` es una categoria separada para apertura, cambios de periodico y comentarios puente; no reemplaza al narrador principal de cada noticia.
- Para historias, prioriza el primer narrador listado en `story-type-mapping.json` y usa los siguientes solo como alternativas.
- El `narrator_profile_id` debe coincidir exactamente con los IDs del archivo de mapeo actualizado.
- `support_visual` es opcional y hoy esta pensado para un grafico numerico simple con `chart_type` igual a `line`, `bar` o `area`.
- Si usas `support_visual`, entrega entre 2 y 6 puntos en `points`, con `label` y `value`, y anota la procedencia resumida en `data_source_note`.
- Para pruebas manuales del feature, usa como base `fuentes-chatgpt/support-visual-prompt.md`.
