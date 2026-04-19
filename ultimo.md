

Lo dejé integrado y probado con una portada real de `Ojo`.

La integración quedó en:
- motor OCR nuevo: [paddle.py](C:/Users/pc/Documents/proyectos/news-video-mvp/src/news_video_mvp/ocr/paddle.py:1)
- export del módulo OCR: [__init__.py](C:/Users/pc/Documents/proyectos/news-video-mvp/src/news_video_mvp/ocr/__init__.py:1)
- pipeline `extract-job` con `--ocr-engine paddleocr` y `--ocr-scope`: [automation_pipeline.py](C:/Users/pc/Documents/proyectos/news-video-mvp/src/news_video_mvp/automation_pipeline.py:691)
- CLI nueva para usarlo: [automation_cli.py](C:/Users/pc/Documents/proyectos/news-video-mvp/src/news_video_mvp/automation_cli.py:152)
- dependencia opcional: [pyproject.toml](C:/Users/pc/Documents/proyectos/news-video-mvp/pyproject.toml:24)

Lo probé sobre este job:
- [job-manifest.json](C:/Users/pc/Documents/proyectos/news-video-mvp/data/jobs/2026-04-18/2026-04-18-ojo-cover-first-test/job-manifest.json:1)

Comparación real contra el OCR anterior en la misma portada:
- OCR anterior: `73` caracteres, `4` líneas
- PaddleOCR: `992` caracteres, `30` líneas
- OCR anterior detectaba páginas: `2`, `5`
- PaddleOCR detectó referencias: `2`, `6`, `13`

Conclusión honesta: **PaddleOCR sí mejora mucho la lectura general de la portada**, pero **no mejoró todavía la precisión de páginas para este caso**. Ganamos bastante contexto y texto útil, pero en referencias pequeñas de portada sigue habiendo ruido; incluso perdió la página `5` que el OCR manual sí tenía en este ejemplo.

Así que la mejor estrategia por ahora sería:
- usar `PaddleOCR` para extraer mejor titulares y contexto de portada
- mantener el fallback manual con tu ChatGPT para decidir páginas cuando la selección automática no sea confiable

Comando para usarlo:
```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m news_video_mvp.automation_cli extract-job `
  --job-manifest .\data\jobs\2026-04-18\2026-04-18-ojo-cover-first-test\job-manifest.json `
  --editorial-policy .\automation\rules\editorial-policy.json `
  --ocr-engine paddleocr `
  --ocr-scope front_page
```

Y luego:
```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m news_video_mvp.automation_cli analyze-cover-pages `
  --job-manifest .\data\jobs\2026-04-18\2026-04-18-ojo-cover-first-test\job-manifest.json `
  --force
```

Verifiqué también que el código compile con `.venv` usando `python -m compileall src`.

El siguiente paso que más vale la pena es endurecer `analyze-cover-pages` con heurísticas para filtrar falsos positivos de PaddleOCR y priorizar patrones tipo `PAG. X` cerca de titulares grandes.