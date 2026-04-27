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

El modelo debe:
1. leer los metadatos
2. usar las imagenes como verificacion
3. asignar narrator_profile_id segun story-type-mapping.json
4. escribir speech segun narrator-profiles.json
5. respetar speech-style-rules.md y speech-safety-rules.md
6. devolver solo JSON valido segun output-schema.json

Notas operativas:
- `voz_en_off` es una categoria separada para apertura, cambios de periodico y comentarios puente; no reemplaza al narrador principal de cada noticia.
- Para historias, prioriza el primer narrador listado en `story-type-mapping.json` y usa los siguientes solo como alternativas.
- El `narrator_profile_id` debe coincidir exactamente con los IDs del archivo de mapeo actualizado.
