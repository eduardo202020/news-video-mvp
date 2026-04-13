# Remotion MVP

App de Remotion para revisar y renderizar el layout vertical del proyecto.

## Scripts

```powershell
npm run dev
npm run dev:latest
npm run clean:generated
npm run render:trome
npm run render:comercio
```

## Estructura interna

```text
src/
  Root.jsx
  NewsVideo.jsx
  data.js
  generated-story.js
  utils.js
  video/
    CaptionBar.jsx
    CoverStage.jsx
    NarratorStage.jsx
    constants.js
    helpers.js
    layouts.js
public/assets/
  audio/
  backgrounds/
  covers/
  fondo-musical/
  generated/
  gestures/
```

## Como trabajamos aqui

### `src/data.js`

Es la fuente estable para Studio.
Sirve para revisar layout, motion y posicionamiento sin depender del pipeline generado en ese momento.

### `src/story/`

Contiene la capa declarativa del proyecto:

- `defaults.js`
  Spec base del video y defaults de audio.
- `demo-stories.js`
  Historias demo estables.
- `normalize.js`
  Normalizacion de props para Studio y renders generados.

### `src/generated-story.js`

Es la historia que escribe Python cuando corre la CLI.
Sirve como snapshot de la ultima corrida automatica.

### `src/NewsVideo.jsx`

Orquesta el video ya normalizado:

- audio principal
- musica de fondo
- timing por segmentos
- subtitulos
- cambio de narrador
- transicion entre portadas

La logica de timeline y seleccion de segmento vive en `src/video/timeline.js`.

### `src/video/`

Contiene las piezas visuales separadas para iterar mas facil:

- `CoverStage.jsx`
  Hero de la portada y cambio de pagina.
- `NarratorStage.jsx`
  Presentador, sombra de contacto y layouts por personaje.
- `CaptionBar.jsx`
  Franja de subtitulos.
- `constants.js`
  Valores globales del template.
- `layouts.js`
  Variantes visuales por narrador.
- `helpers.js`
  Utilidades del template.

Presentadores actuales:

- `Cuy-01` -> `public/assets/gestures/cuy/01`
- `Cuy-02` -> `public/assets/gestures/cuy/02`
- `Cuy-Depor` -> `public/assets/gestures/cuy/depor`

## Flujo recomendado

1. Corre la CLI principal desde la raiz del repo si quieres generar historia y assets nuevos.
2. Entra a `remotion-app` y abre `npm run dev`.
3. Revisa composiciones estables en Studio.
4. Ajusta layout en `src/video/` o `src/NewsVideo.jsx`.
5. Cuando el layout este listo, vuelve a renderizar desde Python o desde Remotion.

Secuencia estable actual en Studio:

1. `Trome` con `Cuy-01`
2. `Ojo` con `Cuy-02`
3. `Libero` con `Cuy-Depor`

## Composiciones importantes

- `NewsVideo`
  Composicion principal de trabajo.
- `NewsVideo-generated`
  Ultima historia generada por Python, ya normalizada para Studio.
- `NewsVideo-periodicos-secuencia-demo`
  Demo con varios periodicos.
- `NewsVideo-trome`
- `NewsVideo-ojo`
- `NewsVideo-libero`

## Notas practicas

- El proyecto esta orientado a `1080 x 1920`.
- Si Studio no refleja cambios, reinicia `npm run dev`.
- Si falta audio, revisa primero la ruta dentro de `data.js`.
- Si el fondo musical no suena, revisa el archivo dentro de `public/assets/fondo-musical/`.
- `src/data.js` se usa para previsualizacion estable.
- `src/generated-story.js` se actualiza cuando corres `python -m news_video_mvp.cli --story-config .\examples\periodicos-secuencia.json`.
