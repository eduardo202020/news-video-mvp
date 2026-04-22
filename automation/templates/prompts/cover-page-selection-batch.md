Analiza las portadas adjuntas de periodicos y selecciona solo las paginas internas necesarias para ampliar las noticias principales de cada portada.
Tambien crea una introduccion breve de voz en off para abrir el programa diario de portadas.

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
- genera `rundown_intro.speech` como saludo/presentacion del programa: debe mencionar la fecha del lote, anticipar el recorrido por portadas y conectar con algun dato o referencia del dia
- para la referencia del dia, usa primero la pagina peruana de efemerides de Adonde.com si tienes navegacion web disponible
- la URL de referencia sigue este patron: `https://adonde.com/aqui/efemerides/{mes}{dia}.php`
- `{mes}` debe ir en minusculas y sin tilde: `enero`, `febrero`, `marzo`, `abril`, `mayo`, `junio`, `julio`, `agosto`, `septiembre`, `octubre`, `noviembre`, `diciembre`
- `{dia}` debe ir sin cero inicial: para 22 de abril usa `abril22.php`; para 5 de mayo usa `mayo5.php`
- ejemplo para 22 de abril: `https://adonde.com/aqui/efemerides/abril22.php`
- desde esa pagina, prioriza efemerides peruanas: fechas historicas, aniversarios de ciudades, nacimientos o fallecimientos de figuras peruanas, celebraciones regionales, hitos culturales o civicos
- si la pagina incluye una efemeride mundial muy fuerte junto a efemerides peruanas, puedes mencionarla solo si ayuda a abrir el programa, pero no desplaces una referencia peruana clara
- si no encuentras una referencia peruana confiable para esa fecha, usa una efemeride mundial sobria y relevante
- si no puedes verificar una efemeride, no inventes; usa una intro basada solo en la fecha y en los temas visibles de las portadas
- la intro debe sonar como voz en off de presentador, no como noticia independiente
- `rundown_intro.speech` debe tener entre 180 y 360 caracteres, sin hashtags ni emojis
- `rundown_intro.source_scope` debe ser `peru`, `world` o `none`
- `rundown_intro.date_reference` debe resumir la efemeride elegida y, si usaste Adonde.com, incluir una referencia breve tipo `Adonde.com efemerides abril22`
- manten la intro realmente corta y directa; evita saludos largos o rodeos

Metadatos de las portadas:

```text
{{PORTADAS}}
```

Devuelve solo JSON valido, sin explicacion adicional, con esta estructura exacta:

```json
{
  "notes": "Seleccion manual desde ChatGPT para varias portadas.",
  "rundown_intro": {
    "speech": "Hola. Hoy, 21 de abril, revisamos las portadas con una agenda marcada por politica, economia y deporte. En una fecha que tambien invita a mirar el pais con memoria, vamos diario por diario con lo central y sin rodeos.",
    "date_reference": "Referencia breve usada para abrir el programa",
    "source_scope": "peru",
    "why_it_fits": "Conecta la fecha del lote con el tono editorial del recorrido."
  },
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
- incluye `rundown_intro` una sola vez a nivel raiz del JSON
- `rundown_intro.speech` debe estar listo para narracion y no debe depender de ver paginas internas
- `items` debe ser una lista
- cada item debe incluir `headline`, `story_type`, `cover_region` y `page_number`
- `confidence` debe estar entre `0` y `1`
- `evidence_line` debe resumir la evidencia visual que justifica la pagina
- `cover_region.x`, `cover_region.y`, `cover_region.width` y `cover_region.height` deben quedar entre `0` y `1`
- no repitas la misma pagina dos veces para un mismo job
- si una noticia ocupa varias paginas, no inventes headlines distintos para la misma historia salvo que la portada realmente las separe
- devuelve solo las noticias realmente mas relevantes de cada portada; no conviertas cada pequeno llamado lateral en una noticia del lote
- no agregues campos fuera de esta estructura
