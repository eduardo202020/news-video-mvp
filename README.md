# News Video MVP

MVP local para generar un video vertical tipo TikTok con:

- fondo urbano estatico,
- portada de periodico en la parte superior,
- narrador con gestos que cambian cada 2 segundos,
- audio TTS,
- subtitulos simples sincronizados por segmentos.

Ahora, en modo simple:

- la voz del TTS del sistema intenta salir en espanol por defecto,
- si no pasas `--cover`, se usa automaticamente la primera portada encontrada en `input/periodicos/`.

## Flujo

1. Coloca una imagen de fondo urbano.
2. Coloca una portada de periodico.
3. Coloca varias poses del narrador en `input/narrator_gestures/`.
4. Escribe el texto narrado.
5. Ejecuta el render.

## Instalacion

```powershell
cd C:\Users\pc\Documents\proyectos\news-video-mvp
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

Opcional para Kokoro TTS:

```powershell
pip install -e .[kokoro]
```

## Estructura esperada

```text
input/
  calle.jpg
  periodicos/
    aja.png
    ojo.png
    trome.png
  narrator_gestures/
    mascaly01.png
    mascaly-02.png
    mascaly-03.png
output/
assets/
```

## Uso rapido

Con TTS del sistema:

```powershell
news-video-mvp `
  --background .\input\calle.jpg `
  --gestures-dir .\input\narrator_gestures `
  --text "Resumen narrado de la noticia..." `
  --output .\output\noticia_tiktok.mp4
```

Con audio ya generado:

```powershell
news-video-mvp `
  --background .\input\calle.jpg `
  --gestures-dir .\input\narrator_gestures `
  --text "Resumen narrado de la noticia..." `
  --audio-file .\output\narracion.wav `
  --output .\output\noticia_tiktok.mp4
```

Con Kokoro si esta instalado y configurado:

```powershell
news-video-mvp `
  --background .\input\calle.jpg `
  --gestures-dir .\input\narrator_gestures `
  --text "Resumen narrado de la noticia..." `
  --tts-provider kokoro `
  --output .\output\noticia_tiktok.mp4
```

## Secuencia de periodicos en un solo video

Tambien puedes recorrer varias portadas dentro de un solo video con transicion tipo cambio de pagina:

```powershell
news-video-mvp --story-config .\examples\periodicos-secuencia.json
```

En ese modo:

- cada item de `stories` aporta su propia portada y texto,
- la CLI genera un audio por segmento y luego los concatena,
- Remotion muestra el paso de un periodico al siguiente con una transicion de pagina.

## Notas del MVP

- El cambio de gesto ocurre cada 2 segundos.
- La sincronizacion del narrador se logra haciendo que la secuencia de poses tenga la misma duracion que el audio.
- Los subtitulos se generan en bloques cortos estimados a partir de la duracion del audio.
- El layout esta optimizado para formato 1080x1920.
- La plantilla visual esta pensada para usar `calle.jpg` como fondo y `mascaly` como presentadora en primer plano.
- Si no tienes `ffmpeg` en el sistema, `moviepy` usara el binario que trae `imageio-ffmpeg`.

## Siguientes mejoras

- Lip sync real con un avatar talking-head.
- Plantillas por seccion de noticia.
- Integracion directa con Kokoro o MeloTTS mas avanzada.
- Export de metadata para publicacion automatica.
