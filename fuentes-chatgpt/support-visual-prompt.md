# Prompt de prueba para `support_visual`

Usa este prompt cuando quieras probar historias que pueden beneficiarse de contexto numerico y grafico animado.

## Prompt

Analiza el contexto editorial adjunto de las noticias detectadas desde portada y devuelve el JSON final por historia.

Objetivo adicional de esta prueba:
- cuando una historia tenga sentido con contexto numerico verificable, agrega `support_visual`
- `support_visual` debe ayudar a que el video muestre un grafico animado breve y claro
- usa `support_visual` sobre todo en crecimiento, caidas, avances, comparaciones, votos, porcentajes, produccion, precios, inflacion, ranking, goles, puntos o resultados acumulados

Reglas:
- mantente dentro de las historias ya detectadas desde portada
- usa paginas internas si existen como fuente principal de verificacion
- si falta contexto numerico puntual, puedes buscar en la web datos complementarios confiables
- no inventes cifras
- si usas la web, resume la procedencia en `support_visual.data_source_note`
- si una historia no necesita grafico, devuelve `support_visual: null`
- si una historia si necesita grafico, devuelve un objeto `support_visual`
- `support_visual.type` debe ser exactamente `numeric_chart`
- `support_visual.chart_type` debe ser exactamente uno de estos: `line`, `bar`, `area`
- `support_visual.points` debe tener entre 2 y 6 puntos
- cada punto debe tener `label` y `value`
- `title` debe ser corto y visual
- `subtitle` es opcional
- `unit` es opcional y debe ser breve, por ejemplo `%`, `pts`, `S/`, `mil`
- `highlight_label` es opcional y sirve para remarcar el angulo editorial
- el `speech` debe seguir siendo breve, fuerte y apto para narracion

Devuelve solo JSON valido con esta estructura:

```json
{
  "newspapers": [
    {
      "newspaper_name": "gestion",
      "job_id": "2026-04-27-gestion-frontpage-001",
      "stories": [
        {
          "headline": "Inflacion baja por segundo mes",
          "story_type": "economia",
          "narrator_profile_id": "jaime_bayly",
          "speech": "La inflacion baja otra vez, pero el alivio aun no se siente parejo. El dato mejora el clima economico, aunque el golpe acumulado al consumo sigue pesando en los hogares.",
          "tone_notes": ["analitico", "claro", "sobrio"],
          "key_facts_used": ["segunda caida mensual", "mejora del indice", "efecto sobre consumo"],
          "safety_notes": "Se resume solo con cifras verificables.",
          "support_visual": {
            "type": "numeric_chart",
            "chart_type": "line",
            "title": "Inflacion mensual",
            "subtitle": "Ultimos 4 meses",
            "unit": "%",
            "highlight_label": "Tendencia",
            "data_source_note": "Cifras verificadas con fuente periodistica y referencia oficial resumida.",
            "points": [
              {"label": "Ene", "value": 0.4},
              {"label": "Feb", "value": 0.5},
              {"label": "Mar", "value": 0.3},
              {"label": "Abr", "value": 0.2}
            ]
          }
        },
        {
          "headline": "Congreso debate nueva norma",
          "story_type": "politica",
          "narrator_profile_id": "beto_ortiz",
          "speech": "El debate vuelve a encender al Congreso y otra vez la disputa no es solo legal, sino politica. El punto clave ahora es quien gana margen real si la norma avanza.",
          "tone_notes": ["directo", "politico", "filoso"],
          "key_facts_used": ["debate en Congreso", "impacto politico", "norma en discusion"],
          "safety_notes": "Sin cifras centrales para graficar.",
          "support_visual": null
        }
      ]
    }
  ]
}
```

Instruccion final:
- devuelve `support_visual` solo cuando realmente haga mas clara la historia
- si el grafico no aporta, dejalo en `null`
- devuelve solo JSON valido, sin explicacion adicional
