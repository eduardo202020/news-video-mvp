Analiza las portadas adjuntas de periodicos y selecciona las paginas internas necesarias para ampliar las noticias principales y las secundarias fuertes de cada portada.
Tambien crea una introduccion breve de voz en off para abrir el programa diario de portadas.

Contexto del flujo:
- cada imagen corresponde a una portada distinta
- cada portada ya esta asociada a un job del pipeline
- necesito paginas internas concretas para descargarlas despues
- en el video final solo se mostrara la portada; las paginas internas se descargan unicamente para obtener mejor contexto editorial
- primero detecta todas las noticias y bloques editoriales con apariencia real de noticia visibles en la portada
- despues de detectar todo lo visible, recien clasifica y filtra; no uses la lista de categorias como filtro para decidir si una noticia existe o no
- no inventes paginas si la referencia no es visible o no es razonablemente inferible
- excluye la portada, asi que no devuelvas `page_number: 1`
- prioriza paginas claramente mencionadas por los titulares principales y bloques visuales centrales de la portada
- da prioridad a la noticia dominante, a los titulares principales y a las llamadas editoriales mas relevantes del dia
- revisa la portada completa antes de decidir la salida: titular principal, secundarios grandes, franja inferior, laterales y modulos destacados
- no te quedes solo con la noticia principal si la portada muestra otras llamadas de alta jerarquia con referencia de pagina visible o razonablemente inferible
- por defecto intenta capturar entre 2 y 4 noticias relevantes por portada cuando la jerarquia visual lo permita
- si la portada es de diario popular o viene muy cargada de llamadas, intenta capturar entre 3 y 5 noticias relevantes antes de descartar bloques fuertes
- solo devuelve una sola noticia en una portada si de verdad no hay una segunda llamada relevante con peso editorial claro
- antes de cerrar cada `job`, haz esta verificacion mental: "ya cubri la principal, los secundarios grandes y algun modulo fuerte de la parte baja o lateral si realmente compite en jerarquia?"
- si hay varias noticias fuertes, cubre primero la principal y luego las secundarias mas visibles; deja fuera solo promos pequenas, farandula menor, avisos y ganchos sin desarrollo claro
- evita llenar la salida con teasers pequenos, recuadros menores o llamados de baja jerarquia visual
- prioriza llamadas tipo `Pag. 4`, `p. 7`, `pagina 12` cuando esten asociadas a noticias de alta jerarquia en portada
- si una portada no muestra referencias confiables, devuelve `items: []` para ese job
- para cada noticia detectada, asigna tambien `story_type` usando una de estas categorias: `actualidad`, `politica`, `policial`, `deportes`, `mundo`, `economia`, `espectaculos`
- el orden correcto es: 1) detectar todas las noticias visibles, 2) agrupar paginas por historia, 3) mapear cada historia a una categoria permitida
- si una noticia no encaja claramente en ninguna categoria especifica, no la descartes: conservala y asignala a `actualidad`
- no elimines una noticia solo porque parece cruce de categorias o porque no calza perfecto; usa la categoria mas cercana y, si hace falta, `actualidad`
- para cada noticia detectada, devuelve tambien `cover_region` usando coordenadas normalizadas sobre la portada: `x`, `y`, `width`, `height`
- usa las dimensiones reales de cada portada como referencia visual para ubicar mejor la noticia, pero la salida final de `cover_region` debe ir siempre normalizada entre `0` y `1`
- `x,y` representan la esquina superior izquierda del bloque de la noticia en la portada
- `width,height` representan el tamano aproximado del bloque visual que contiene esa noticia en portada
- `cover_region` debe ser lo mas ajustado posible al bloque principal de la noticia; evita regiones demasiado grandes que abarquen media portada si el titular ocupa un area mas pequena
- si una misma noticia remite a varias paginas, puedes repetir el mismo `headline`, `story_type` y `cover_region` en varios items, cambiando solo `page_number`
- si una misma noticia remite a dos o mas paginas, devuelve todas las paginas visibles o razonablemente inferibles para esa misma historia
- cuando una referencia diga `Pags. 4-5`, `4 y 5`, `pp. 6-7` o una formula equivalente, conviertela en varios items: uno por cada `page_number`
- en esos casos, no cuentes esas paginas como noticias distintas; cuentan como una sola historia con varias paginas asociadas
- si una historia tiene varias paginas y otra historia distinta tambien aparece en portada, devuelve ambas cosas: la historia multi-pagina completa y la otra historia
- el `headline` debe quedar corto y util como nombre de noticia dentro del pipeline
- excluye suplementos, secciones anexas o promos marginales como `Luces`, `Dominical`, `DT` u otros similares, salvo que ese bloque sea claramente una de las noticias principales visibles de la portada
- una cosa es detectar y otra filtrar: primero reconoce todo bloque con apariencia de noticia; solo despues deja fuera suplementos, promos marginales, avisos y ganchos que realmente no sean noticia
- si dudas entre una noticia central y un teaser secundario, elige la noticia central
- apunta a una seleccion corta pero suficiente: normalmente 2 a 4 historias por portada bien elegidas, no una sola por defecto ni tampoco todo lo impreso
- si la portada mezcla una noticia principal con dos o tres secundarios claramente destacados, devuelve esas tres o cuatro historias en lugar de resumir todo en una sola
- si la portada tiene mas de cuatro noticias reales visibles y con referencia clara, incluyelas tambien; el limite practico lo marca la portada, no una cuota fija artificial
- trata cada bloque editorial fuerte como una historia separada cuando tenga titular propio, foto propia o referencia propia de pagina
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
          "headline": "Titular principal resumido",
          "story_type": "politica",
          "cover_region": {
            "x": 0.18,
            "y": 0.22,
            "width": 0.58,
            "height": 0.24
          },
          "page_number": 4,
          "confidence": 0.97,
          "evidence_line": "PAGS 4-5"
        },
        {
          "headline": "Titular principal resumido",
          "story_type": "politica",
          "cover_region": {
            "x": 0.18,
            "y": 0.22,
            "width": 0.58,
            "height": 0.24
          },
          "page_number": 5,
          "confidence": 0.96,
          "evidence_line": "PAGS 4-5"
        },
        {
          "headline": "Secundario fuerte de portada",
          "story_type": "policial",
          "cover_region": {
            "x": 0.08,
            "y": 0.54,
            "width": 0.39,
            "height": 0.19
          },
          "page_number": 8,
          "confidence": 0.91,
          "evidence_line": "p. 8"
        },
        {
          "headline": "Tema destacado en franja inferior",
          "story_type": "deportes",
          "cover_region": {
            "x": 0.49,
            "y": 0.72,
            "width": 0.43,
            "height": 0.16
          },
          "page_number": 14,
          "confidence": 0.88,
          "evidence_line": "PAG 14"
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
- cada `job` deberia traer varias historias cuando la portada las tenga; usa `items: []` solo si no hay referencias confiables y evita dejar un unico item por inercia
- si una portada claramente muestra 3 o mas bloques fuertes con desarrollo, la salida esperada normalmente tambien deberia tener 3 o mas items
- la deteccion debe ser amplia primero y el filtrado despues; no uses `story_type` como excusa para dejar fuera noticias visibles
- cada item debe incluir `headline`, `story_type`, `cover_region` y `page_number`
- `confidence` debe estar entre `0` y `1`
- `evidence_line` debe resumir la evidencia visual que justifica la pagina
- `cover_region.x`, `cover_region.y`, `cover_region.width` y `cover_region.height` deben quedar entre `0` y `1`
- no repitas la misma pagina dos veces para un mismo job
- si una noticia ocupa varias paginas, devuelve una entrada por pagina, pero manteniendo el mismo `headline`, `story_type` y `cover_region` para esa historia salvo que la portada realmente las separe
- no omitas paginas secundarias de una misma historia solo para hacer la salida mas corta
- devuelve solo las noticias realmente mas relevantes de cada portada, pero incluye tambien las secundarias fuertes cuando sean visibles y editoriales; no conviertas cada pequeno llamado lateral en una noticia del lote
- no agregues campos fuera de esta estructura
