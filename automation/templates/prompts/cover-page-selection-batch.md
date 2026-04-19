Analiza las portadas adjuntas de periodicos y selecciona solo las paginas internas necesarias para ampliar las noticias principales de cada portada.

Contexto del flujo:
- cada imagen corresponde a una portada distinta
- cada portada ya esta asociada a un job del pipeline
- necesito paginas internas concretas para descargarlas despues
- no inventes paginas si la referencia no es visible o no es razonablemente inferible
- excluye la portada, asi que no devuelvas `page_number: 1`
- prioriza paginas claramente mencionadas por titulares principales, bajadas, cintillos o llamadas tipo `Pag. 4`, `p. 7`, `pagina 12`
- si una portada no muestra referencias confiables, devuelve `items: []` para ese job

Metadatos de las portadas:

```text
{{PORTADAS}}
```

Devuelve solo JSON valido, sin explicacion adicional, con esta estructura exacta:

```json
{
  "notes": "Seleccion manual desde ChatGPT para varias portadas.",
  "jobs": [
    {
      "job_manifest_path": "data/jobs/2026-04-19/2026-04-19-ojo-frontpage-001/job-manifest.json",
      "job_id": "2026-04-19-ojo-frontpage-001",
      "newspaper_name": "Ojo",
      "notes": "Paginas detectadas visualmente desde la portada.",
      "items": [
        {
          "headline": "Titular o tema resumido",
          "page_number": 4,
          "confidence": 0.97,
          "evidence_line": "PAG 4"
        }
      ]
    }
  ]
}
```

Reglas de salida:
- conserva exactamente `job_manifest_path`, `job_id` y `newspaper_name` como aparecen en los metadatos
- `items` debe ser una lista
- cada item debe incluir `headline` y `page_number`
- `confidence` debe estar entre `0` y `1`
- `evidence_line` debe resumir la evidencia visual que justifica la pagina
- no repitas la misma pagina dos veces para un mismo job
- no agregues campos fuera de esta estructura
