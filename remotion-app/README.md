# Remotion MVP

Version del MVP rehecha en Remotion para controlar mejor layout, timing y animacion.

## Scripts

```powershell
npm run dev
npm run dev:latest
npm run clean:generated
npm run render:trome
npm run render:comercio
```

`npm run dev` y `npm run dev:latest` abren Remotion Studio usando la ultima historia generada por la CLI de Python, leida desde `src/generated-story.js`.

Cada vez que ejecutas la app principal (`python -m news_video_mvp.cli ...`), se actualiza esa historia y se limpian automaticamente los assets generados viejos, dejando solo la corrida mas reciente en `public/assets/generated/`.

## Estructura

- `src/NewsVideo.jsx`: plantilla principal del video vertical
- `src/data.js`: historias y assets
- `src/generated-story.js`: ultima historia sincronizada desde la CLI
- `public/assets/`: fondos, portadas, gestos y audio

## Objetivo visual

- portada arriba
- narradora debajo
- fondo urbano desenfocado
- cambio de gesto cada 2 segundos
- subtitulos simples sincronizados por bloques

## Flujo recomendado

1. Ejecuta la CLI principal para generar audio, copiar assets y sincronizar la ultima historia.
2. Abre `npm run dev` para revisar esa misma historia en Remotion Studio.
3. Si quieres limpiar manualmente assets generados, usa `npm run clean:generated`.
