Analiza las portadas adjuntas de periodicos y selecciona solo las paginas internas necesarias para ampliar las noticias principales de cada portada.

Contexto del flujo:
- cada imagen corresponde a una portada distinta
- cada portada ya esta asociada a un job del pipeline
- necesito paginas internas concretas para descargarlas despues
- en el video final solo se mostrara la portada; las paginas internas se descargan unicamente para obtener mejor contexto editorial
- no inventes paginas si la referencia no es visible o no es razonablemente inferible
- excluye la portada, asi que no devuelvas `page_number: 1`
- prioriza paginas claramente mencionadas por los titulares principales y bloques visuales centrales de la portada
- da prioridad a la noticia dominante, a los titulares principales y a las llamadas editoriales mas relevantes del dia
- evita llenar la salida con teasers pequenos, recuadros menores o llamados de baja jerarquia visual
- prioriza llamadas tipo `Pag. 4`, `p. 7`, `pagina 12` cuando esten asociadas a noticias de alta jerarquia en portada
- si una portada no muestra referencias confiables, devuelve `items: []` para ese job
- para cada noticia detectada, asigna tambien `story_type` usando una de estas categorias: `actualidad`, `politica`, `policial`, `deportes`, `mundo`, `economia`, `espectaculos`
- para cada noticia detectada, devuelve tambien `cover_region` usando coordenadas normalizadas sobre la portada: `x`, `y`, `width`, `height`
- usa las dimensiones reales de cada portada como referencia visual para ubicar mejor la noticia, pero la salida final de `cover_region` debe ir siempre normalizada entre `0` y `1`
- `x,y` representan la esquina superior izquierda del bloque de la noticia en la portada
- `width,height` representan el tamano aproximado del bloque visual que contiene esa noticia en portada
- `cover_region` debe ser lo mas ajustado posible al bloque principal de la noticia; evita regiones demasiado grandes que abarquen media portada si el titular ocupa un area mas pequena
- si una misma noticia remite a varias paginas, puedes repetir el mismo `headline`, `story_type` y `cover_region` en varios items, cambiando solo `page_number`
- el `headline` debe quedar corto y util como nombre de noticia dentro del pipeline
- excluye suplementos, secciones anexas o promos marginales como `Luces`, `Dominical`, `DT` u otros similares, salvo que ese bloque sea claramente una de las noticias principales visibles de la portada
- si dudas entre una noticia central y un teaser secundario, elige la noticia central
- apunta idealmente a pocas noticias pero bien elegidas, no a capturar todo lo que aparece impreso

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
          "story_type": "politica",
          "cover_region": {
            "x": 0.18,
            "y": 0.22,
            "width": 0.58,
            "height": 0.24
          },
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
- cada item debe incluir `headline`, `story_type`, `cover_region` y `page_number`
- `confidence` debe estar entre `0` y `1`
- `evidence_line` debe resumir la evidencia visual que justifica la pagina
- `cover_region.x`, `cover_region.y`, `cover_region.width` y `cover_region.height` deben quedar entre `0` y `1`
- no repitas la misma pagina dos veces para un mismo job
- si una noticia ocupa varias paginas, no inventes headlines distintos para la misma historia salvo que la portada realmente las separe
- devuelve solo las noticias realmente mas relevantes de cada portada; no conviertas cada pequeno llamado lateral en una noticia del lote
- no agregues campos fuera de esta estructura
