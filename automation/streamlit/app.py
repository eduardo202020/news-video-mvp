from __future__ import annotations

from collections import Counter
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import sys

import streamlit as st
import streamlit.components.v1 as components


PROJECT_DIR = Path(__file__).resolve().parents[2]
JOBS_DIR = PROJECT_DIR / "data" / "jobs"
SOURCES_DIR = PROJECT_DIR / "automation" / "sources" / "diarios"
SRC_DIR = PROJECT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from news_video_mvp.automation_pipeline import (  # noqa: E402
    analyze_cover_page_references_for_job,
    approve_script_for_job,
    build_job_id,
    build_story_manifest_from_job,
    compose_job_for_preview,
    create_job_manifest,
    extract_and_classify_job,
    generate_script_from_job,
    generate_voice_and_subtitles_for_job,
    import_cover_page_selection_batch,
    import_cover_page_selection_for_job,
    publish_job,
    scrape_source_into_job,
    scrape_selected_pages_for_job,
)


DEFAULT_EDITORIAL_POLICY = PROJECT_DIR / "automation" / "rules" / "editorial-policy.json"
DEFAULT_SCRIPT_TEMPLATE = PROJECT_DIR / "automation" / "templates" / "scripts" / "default-anchor.json"
DEFAULT_VIDEO_TEMPLATE = PROJECT_DIR / "automation" / "templates" / "video" / "vertical-news.json"
DEFAULT_SUBTITLE_POLICY = PROJECT_DIR / "automation" / "rules" / "subtitle-policy.json"
DEFAULT_PUBLISHING_PROFILE = PROJECT_DIR / "automation" / "templates" / "publishing" / "tiktok.json"
DEFAULT_COVER_BATCH_PROMPT = (
    PROJECT_DIR / "automation" / "templates" / "prompts" / "cover-page-selection-batch.md"
)
VOICE_PROFILES_DIR = PROJECT_DIR / "automation" / "templates" / "voices"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_DIR).as_posix()


def discover_jobs() -> list[Path]:
    if not JOBS_DIR.exists():
        return []
    return sorted(JOBS_DIR.glob("*/*/job-manifest.json"), reverse=True)


def discover_source_configs() -> list[Path]:
    if not SOURCES_DIR.exists():
        return []
    return sorted(SOURCES_DIR.glob("*.json"))


def load_jobs() -> list[dict]:
    jobs_by_source: dict[str, dict] = {}
    for path in discover_jobs():
        job = read_json(path)
        job["_path"] = path
        source_id = str(job.get("source_id") or "sin-source")
        current = jobs_by_source.get(source_id)
        if current is None or _job_sort_key(job) > _job_sort_key(current):
            jobs_by_source[source_id] = job
    return sorted(jobs_by_source.values(), key=_job_sort_key, reverse=True)


def _job_sort_key(job: dict) -> tuple[str, str, str]:
    updated_at = str(job.get("audit", {}).get("updated_at") or "")
    created_at = str(job.get("audit", {}).get("created_at") or "")
    return (
        str(job.get("date") or ""),
        updated_at,
        created_at,
    )


def get_voice_profile_path(profile_id: str | None) -> Path | None:
    if not profile_id:
        return None
    candidate = VOICE_PROFILES_DIR / f"{profile_id}.json"
    return candidate if candidate.exists() else None


def create_daily_jobs_batch(
    *,
    job_date: str,
    source_ids: list[str],
    voice_profile_path: Path,
    approval_mode: str,
    scrape_front_pages: bool,
    max_supporting_pages: int,
    force_scrape_existing: bool,
) -> list[dict[str, object]]:
    source_configs = {path.stem: path for path in discover_source_configs()}
    results: list[dict[str, object]] = []

    for source_id in source_ids:
        source_config_path = source_configs.get(source_id)
        if source_config_path is None:
            results.append({"source_id": source_id, "status": "missing_source_config"})
            continue

        job_id = build_job_id(job_date=job_date, source_id=source_id)
        manifest_path = JOBS_DIR / job_date / job_id / "job-manifest.json"
        created_now = False
        if not manifest_path.exists():
            manifest_path = create_job_manifest(
                source_config_path=source_config_path,
                job_date=job_date,
                approval_mode=approval_mode,
                voice_profile_path=voice_profile_path,
                video_template_path=DEFAULT_VIDEO_TEMPLATE,
                script_template_id="default-anchor",
                publish_profile_id="tiktok",
                subtitle_policy_id="default-2-lines",
                job_id=job_id,
            )
            created_now = True

        status = "created" if created_now else "existing"
        if scrape_front_pages:
            scrape_source_into_job(
                job_manifest_path=manifest_path,
                source_config_path=source_config_path,
                max_supporting_pages=max_supporting_pages,
                force=force_scrape_existing,
            )
            status = "scraped" if created_now else "existing_scraped"

        results.append(
            {
                "source_id": source_id,
                "job_id": job_id,
                "job_manifest_path": rel(manifest_path),
                "status": status,
            }
        )

    return results


def download_selected_pages_batch(*, jobs: list[dict], force: bool = True) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for job in jobs:
        page_selection = job.get("page_selection", {})
        selected_page_numbers = [
            int(page_number)
            for page_number in page_selection.get("selected_page_numbers", [])
            if int(page_number) > 1
        ]
        if not selected_page_numbers:
            continue

        source_config_value = job.get("source", {}).get("source_config_path") or job.get("input_assets", {}).get(
            "source_config"
        )
        if not source_config_value:
            results.append(
                {
                    "job_id": job.get("job_id", ""),
                    "source_id": job.get("source_id", ""),
                    "status": "missing_source_config",
                }
            )
            continue

        source_config_path = PROJECT_DIR / str(source_config_value)
        manifest_path = job.get("_path")
        if not isinstance(manifest_path, Path):
            results.append(
                {
                    "job_id": job.get("job_id", ""),
                    "source_id": job.get("source_id", ""),
                    "status": "missing_manifest_path",
                }
            )
            continue

        current_pages = [
            {
                "page_number": int(page.get("page_number") or 0),
                "local_path": page.get("local_path"),
            }
            for page in job.get("input_assets", {}).get("pages", [])
            if int(page.get("page_number") or 0) > 1
        ]
        current_page_numbers = [page["page_number"] for page in current_pages]
        if not force and set(selected_page_numbers).issubset(set(current_page_numbers)):
            results.append(
                {
                    "job_id": job.get("job_id", ""),
                    "source_id": job.get("source_id", ""),
                    "selected_page_numbers": selected_page_numbers,
                    "downloaded_page_numbers": selected_page_numbers,
                    "downloaded_pages": [
                        page for page in current_pages if page["page_number"] in set(selected_page_numbers)
                    ],
                    "status": "reused",
                }
            )
            continue

        scrape_selected_pages_for_job(
            job_manifest_path=manifest_path,
            source_config_path=source_config_path,
            force=force,
        )
        refreshed_job = read_json(manifest_path)
        downloaded_page_numbers = list(
            refreshed_job.get("page_selection", {}).get("downloaded_page_numbers", [])
        )
        downloaded_pages = [
            {
                "page_number": int(page.get("page_number") or 0),
                "local_path": page.get("local_path"),
            }
            for page in refreshed_job.get("input_assets", {}).get("pages", [])
            if int(page.get("page_number") or 0) > 1
        ]
        results.append(
            {
                "job_id": job.get("job_id", ""),
                "source_id": job.get("source_id", ""),
                "selected_page_numbers": selected_page_numbers,
                "downloaded_page_numbers": downloaded_page_numbers,
                "downloaded_pages": downloaded_pages,
                "status": "downloaded",
            }
        )
    return results


def update_job_script(job_path: Path, approved_text: str, review_notes: str, approve: bool) -> None:
    job = read_json(job_path)
    job.setdefault("script", {})
    job["script"]["approved_text"] = approved_text.strip()
    job["script"]["review_notes"] = review_notes.strip()
    if approve:
        job["status"] = "approved"
        event_status = "approved"
        details = "Aprobado desde Streamlit."
    else:
        event_status = "edited"
        details = "Guion editado desde Streamlit."
    job.setdefault("audit", {})
    job["audit"].setdefault("events", [])
    timestamp = datetime.now().isoformat(timespec="seconds")
    job["audit"]["events"].append(
        {
            "stage": "review_ui",
            "status": event_status,
            "timestamp": timestamp,
            "details": details,
        }
    )
    job["audit"]["updated_at"] = timestamp
    write_json(job_path, job)


def run_action(label: str, action) -> None:
    try:
        action()
        st.success(label)
        st.rerun()
    except Exception as exc:
        st.error(str(exc))


def build_job_label(job: dict) -> str:
    return (
        f"{job.get('date', 'sin-fecha')} | "
        f"{job.get('source_id', 'sin-source')} | "
        f"{job.get('status', 'sin-status')} | "
        f"{job.get('job_id', 'sin-id')}"
    )


def filter_jobs(jobs: list[dict], *, selected_source: str, selected_status: str, text_query: str) -> list[dict]:
    filtered = jobs
    if selected_source != "Todos":
        filtered = [job for job in filtered if job.get("source_id") == selected_source]
    if selected_status != "Todos":
        filtered = [job for job in filtered if job.get("status") == selected_status]
    if text_query:
        needle = text_query.casefold()
        filtered = [
            job
            for job in filtered
            if needle in build_job_label(job).casefold()
            or needle in (job.get("script", {}).get("draft", "").casefold())
            or needle in " ".join(job.get("extraction", {}).get("headline_candidates", [])).casefold()
        ]
    return filtered


def render_dashboard(jobs: list[dict]) -> None:
    counts = Counter(job.get("status", "sin-status") for job in jobs)
    sources = Counter(job.get("source_id", "sin-source") for job in jobs)
    pending_review = counts.get("review_pending", 0)
    ready_preview = counts.get("composed", 0)
    queued_publish = counts.get("queued", 0) + counts.get("ready_for_review", 0)

    metric_cols = st.columns(4)
    metric_cols[0].metric("Jobs", len(jobs))
    metric_cols[1].metric("Review Pending", pending_review)
    metric_cols[2].metric("Preview Ready", ready_preview)
    metric_cols[3].metric("Publish Queue", queued_publish)

    with st.expander("Distribucion por Estado", expanded=False):
        st.json(dict(counts))

    with st.expander("Distribucion por Fuente", expanded=False):
        st.json(dict(sources))


def render_job_summary(job: dict) -> None:
    summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
    summary_col1.metric("Estado", job.get("status", "sin-status"))
    summary_col2.metric("Fuente", job.get("source_id", "sin-source"))
    summary_col3.metric("Prioridad", job.get("classification", {}).get("priority") or "n/a")
    summary_col4.metric("OCR", job.get("extraction", {}).get("confidence", 0))


def build_cover_batch_metadata(jobs: list[dict]) -> str:
    lines: list[str] = []
    portadas = [job for job in jobs if job.get("input_assets", {}).get("front_page_image")]
    for index, job in enumerate(portadas, start=1):
        manifest_path = job.get("_path")
        if not isinstance(manifest_path, Path):
            continue
        lines.extend(
            [
                f"- portada {index}",
                f"  newspaper_name: {job.get('source_id', 'sin-source')}",
                f"  job_id: {job.get('job_id', 'sin-id')}",
                f"  job_manifest_path: {rel(manifest_path)}",
                "",
            ]
        )
    return "\n".join(lines).strip()


def build_cover_batch_seed_payload(jobs: list[dict]) -> str:
    payload = {
        "notes": (
            "Base editable para seleccion manual desde ChatGPT. "
            "Completa `items` con la respuesta del analisis de portadas."
        ),
        "jobs": [],
    }
    for job in jobs:
        manifest_path = job.get("_path")
        front_page = job.get("input_assets", {}).get("front_page_image")
        if not isinstance(manifest_path, Path) or not front_page:
            continue
        payload["jobs"].append(
            {
                "job_manifest_path": rel(manifest_path),
                "job_id": job.get("job_id", ""),
                "newspaper_name": job.get("source_id", ""),
                "notes": "",
                "items": [],
            }
        )
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_cover_batch_prompt(jobs: list[dict]) -> str:
    prompt_template = ""
    if DEFAULT_COVER_BATCH_PROMPT.exists():
        prompt_template = DEFAULT_COVER_BATCH_PROMPT.read_text(encoding="utf-8")
    metadata_text = build_cover_batch_metadata(jobs)
    cover_count = len([job for job in jobs if job.get("input_assets", {}).get("front_page_image")])
    prefix = (
        f"Se adjuntan exactamente {cover_count} portadas, una por cada imagen enviada en este chat. "
        "La respuesta debe corresponder exactamente a esas portadas y en el mismo lote.\n\n"
    )
    body = prompt_template.replace("{{PORTADAS}}", metadata_text) if prompt_template else metadata_text
    return prefix + body


def build_detailed_news_metadata(jobs: list[dict]) -> str:
    lines: list[str] = []
    index = 1
    for job in jobs:
        source_id = str(job.get("source_id", "sin-source"))
        job_id = str(job.get("job_id", "sin-id"))
        headline_candidates = list(job.get("extraction", {}).get("headline_candidates", []))
        page_selection = job.get("page_selection", {})
        selection_notes = str(page_selection.get("notes") or "").strip()
        selected_candidates = list(page_selection.get("candidates", []))
        ocr_blocks = list(job.get("extraction", {}).get("ocr_blocks", []))
        pages = [
            page
            for page in job.get("input_assets", {}).get("pages", [])
            if int(page.get("page_number") or 0) > 1
        ]
        if not pages:
            continue
        lines.extend(
            [
                f"- diario {index}",
                f"  newspaper_name: {source_id}",
                f"  job_id: {job_id}",
            ]
        )
        if headline_candidates:
            lines.append("  headlines_detected:")
            for headline in headline_candidates[:5]:
                lines.append(f"  - {headline}")
        if selection_notes:
            lines.append(f"  selection_notes: {selection_notes}")
        if selected_candidates:
            lines.append("  page_hints_from_cover:")
            for candidate in selected_candidates[:8]:
                lines.append(
                    "  - "
                    f"story_type: {candidate.get('story_type') or 'actualidad'} | "
                    f"page_number: {int(candidate.get('page_number') or 0)} | "
                    f"headline_hint: {candidate.get('headline') or ''} | "
                    f"evidence_line: {candidate.get('evidence_line') or ''}"
                )
        if ocr_blocks:
            lines.append("  ocr_context:")
            for block in ocr_blocks[:5]:
                text = str(block.get("text") or "").strip()
                if text:
                    lines.append(f"  - {text}")
        for page in pages:
            lines.append(
                f"  - page_number: {int(page.get('page_number') or 0)} | local_path: {page.get('local_path')}"
            )
        lines.append("")
        index += 1
    return "\n".join(lines).strip()


def build_detailed_news_prompt(jobs: list[dict]) -> str:
    metadata_text = build_detailed_news_metadata(jobs)
    newspaper_count = 0
    page_count = 0
    for job in jobs:
        pages = [
            page
            for page in job.get("input_assets", {}).get("pages", [])
            if int(page.get("page_number") or 0) > 1
        ]
        if pages:
            newspaper_count += 1
            page_count += len(pages)

    lines = [
        f"Se adjuntan exactamente {page_count} paginas internas, agrupadas en {newspaper_count} periodico(s).",
        "Cada grupo de imagenes corresponde a un diario y a las paginas seleccionadas desde su portada.",
        "Debes usar solo la informacion visible en esas paginas adjuntas.",
        "",
        "Rol:",
        "Actua como analista editorial y redactor de resúmenes detallados de noticias de prensa escrita.",
        "",
        "Objetivo:",
        "Para cada periodico, identifica las noticias principales que fueron ampliadas en las paginas adjuntas y redacta un resumen breve y util para luego convertirlo en speech de TikTok.",
        "",
        "Reglas:",
        "- No inventes hechos, nombres, cifras o citas que no aparezcan en las imagenes.",
        "- Si una pagina no se lee bien, dilo brevemente en `notes` y resume solo lo que sea confiable.",
        "- Mantén separados los resultados por periodico.",
        "- Si un periodico trae varias noticias relevantes, devuelve varias entradas en `stories`.",
        "- Escribe en espanol claro y natural.",
        "- Cada `summary` debe ser breve: idealmente 2 oraciones cortas o un maximo de 320 caracteres.",
        "- `key_facts` debe tener entre 2 y 4 puntos cortos, no parrafos.",
        "- Usa los titulares detectados, hints de portada y OCR previo solo como contexto auxiliar; la fuente principal siguen siendo las paginas adjuntas.",
        "- Si el contexto previo y las paginas adjuntas se contradicen, prioriza lo que se vea claramente en las paginas.",
        "",
        "Contexto previo disponible del lote:",
        "```text",
        metadata_text or "- No hay paginas internas descargadas todavia.",
        "```",
        "",
        "Devuelve solo JSON valido con esta estructura:",
        "```json",
        "{",
        '  "notes": "Resumen editorial detallado desde paginas internas.",',
        '  "newspapers": [',
        "    {",
        '      "newspaper_name": "ojo",',
        '      "job_id": "2026-04-20-ojo-frontpage-001",',
        '      "stories": [',
        "        {",
        '          "story_type": "politica",',
        '          "headline": "Titular principal inferido desde las paginas",',
        '          "summary": "Resumen breve, claro y fiel de la noticia, util para speech.",',
        '          "page_numbers": [2, 5],',
        '          "key_facts": ["dato 1", "dato 2"],',
        '          "notes": ""',
        "        }",
        "      ]",
        "    }",
        "  ]",
        "}",
        "```",
        "",
        "Instruccion final:",
        "Analiza las paginas adjuntas agrupadas por periodico y devuelve el JSON completo, sin explicacion adicional.",
    ]
    return "\n".join(lines)


def chunk_jobs(jobs: list[dict], *, size: int) -> list[list[dict]]:
    if size <= 0:
        return [jobs]
    return [jobs[index : index + size] for index in range(0, len(jobs), size)]


def render_copy_button(*, label: str, text: str, key: str) -> None:
    payload = json.dumps(text)
    safe_label = json.dumps(label)
    components.html(
        f"""
        <button id="{key}" style="
            width: 100%;
            padding: 0.55rem 0.8rem;
            border-radius: 0.5rem;
            border: 1px solid #d0d7de;
            background: #f6f8fa;
            cursor: pointer;
            font: inherit;
        ">{label}</button>
        <script>
        const btn = document.getElementById({json.dumps(key)});
        const text = {payload};
        const original = {safe_label};
        btn.onclick = async () => {{
          try {{
            await navigator.clipboard.writeText(text);
            btn.innerText = "Copiado";
            setTimeout(() => btn.innerText = original, 1400);
          }} catch (err) {{
            btn.innerText = "No se pudo copiar";
            setTimeout(() => btn.innerText = original, 1800);
          }}
        }};
        </script>
        """,
        height=52,
    )


def render_status_card(*, title: str, body: str, tone: str = "neutral") -> None:
    palette = {
        "ready": {"bg": "#ecfdf3", "border": "#16a34a", "text": "#166534"},
        "pending": {"bg": "#fff7ed", "border": "#ea580c", "text": "#9a3412"},
        "downloaded": {"bg": "#eff6ff", "border": "#2563eb", "text": "#1d4ed8"},
        "neutral": {"bg": "#f8fafc", "border": "#94a3b8", "text": "#334155"},
    }
    colors = palette.get(tone, palette["neutral"])
    st.markdown(
        f"""
        <div style="
            border: 1px solid {colors['border']};
            background: {colors['bg']};
            color: {colors['text']};
            border-radius: 12px;
            padding: 0.8rem 0.95rem;
            margin-bottom: 0.55rem;
        ">
            <div style="font-weight: 700; margin-bottom: 0.18rem;">{title}</div>
            <div>{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_cover_bundle_dir(jobs: list[dict]) -> Path:
    review_dir = PROJECT_DIR / "data" / "review" / "cover-batches"
    review_dir.mkdir(parents=True, exist_ok=True)
    unique_dates = sorted({str(job.get("date") or "sin-fecha") for job in jobs})
    batch_name = unique_dates[0] if len(unique_dates) == 1 else "mixed-dates"
    target_dir = review_dir / batch_name
    target_dir.mkdir(parents=True, exist_ok=True)

    for existing in target_dir.iterdir():
        if existing.is_file():
            existing.unlink()

    for job in jobs:
        image_value = job.get("input_assets", {}).get("front_page_image")
        if not image_value:
            continue
        source_path = PROJECT_DIR / str(image_value)
        if not source_path.exists():
            continue
        suffix = source_path.suffix or ".jpg"
        file_name = f"{job.get('source_id', 'sin-source')}-{job.get('job_id', 'sin-id')}{suffix}"
        shutil.copy2(source_path, target_dir / file_name)

    return target_dir


def build_pages_bundle_dir(jobs: list[dict]) -> Path:
    review_dir = PROJECT_DIR / "data" / "review" / "page-batches"
    review_dir.mkdir(parents=True, exist_ok=True)
    unique_dates = sorted({str(job.get("date") or "sin-fecha") for job in jobs})
    batch_name = unique_dates[0] if len(unique_dates) == 1 else "mixed-dates"
    target_dir = review_dir / batch_name
    target_dir.mkdir(parents=True, exist_ok=True)

    for existing in target_dir.iterdir():
        if existing.is_file():
            existing.unlink()

    for job in jobs:
        source_id = str(job.get("source_id", "sin-source"))
        pages = [
            page
            for page in job.get("input_assets", {}).get("pages", [])
            if int(page.get("page_number") or 0) > 1
        ]
        for page in pages:
            local_path = page.get("local_path")
            if not local_path:
                continue
            source_path = PROJECT_DIR / str(local_path)
            if not source_path.exists():
                continue
            suffix = source_path.suffix or ".jpg"
            file_name = f"{source_id}-page-{int(page.get('page_number') or 0):02d}{suffix}"
            shutil.copy2(source_path, target_dir / file_name)

    return target_dir


def build_pages_bundle_dir_for_group(jobs: list[dict], *, group_index: int) -> Path:
    review_dir = PROJECT_DIR / "data" / "review" / "page-batches"
    review_dir.mkdir(parents=True, exist_ok=True)
    unique_dates = sorted({str(job.get("date") or "sin-fecha") for job in jobs})
    batch_name = unique_dates[0] if len(unique_dates) == 1 else "mixed-dates"
    target_dir = review_dir / f"{batch_name}-group-{group_index:02d}"
    target_dir.mkdir(parents=True, exist_ok=True)

    for existing in target_dir.iterdir():
        if existing.is_file():
            existing.unlink()

    for job in jobs:
        source_id = str(job.get("source_id", "sin-source"))
        pages = [
            page
            for page in job.get("input_assets", {}).get("pages", [])
            if int(page.get("page_number") or 0) > 1
        ]
        for page in pages:
            local_path = page.get("local_path")
            if not local_path:
                continue
            source_path = PROJECT_DIR / str(local_path)
            if not source_path.exists():
                continue
            suffix = source_path.suffix or ".jpg"
            file_name = f"{source_id}-page-{int(page.get('page_number') or 0):02d}{suffix}"
            shutil.copy2(source_path, target_dir / file_name)

    return target_dir


def open_local_path(path: Path) -> None:
    if os.name != "nt":
        raise RuntimeError("Abrir carpetas automaticamente desde la UI esta soportado por ahora en Windows.")
    os.startfile(str(path))  # type: ignore[attr-defined]


def render_event_timeline(job: dict) -> None:
    events = list(reversed(job.get("audit", {}).get("events", [])))
    if not events:
        st.caption("Sin eventos registrados.")
        return
    for event in events:
        st.markdown(
            f"**{event.get('stage', 'stage')}** · `{event.get('status', 'status')}` · "
            f"{event.get('timestamp', 'sin timestamp')}"
        )
        if event.get("details"):
            st.caption(event["details"])


def render_job_board(jobs: list[dict]) -> None:
    if not jobs:
        st.info("No hay jobs que coincidan con los filtros actuales.")
        return
    for job in jobs[:20]:
        with st.container(border=True):
            top_col1, top_col2, top_col3 = st.columns([2.2, 1.2, 1.2])
            top_col1.markdown(f"**{job.get('job_id', 'sin-id')}**")
            top_col2.markdown(f"Estado: `{job.get('status', 'sin-status')}`")
            top_col3.markdown(f"Fuente: `{job.get('source_id', 'sin-source')}`")
            headlines = job.get("extraction", {}).get("headline_candidates", [])
            if headlines:
                st.caption(headlines[0])
            else:
                st.caption("Sin titulares extraidos todavia.")


st.set_page_config(page_title="News Video MVP Review", layout="wide")
st.title("News Video MVP Review")
st.caption("Panel operativo para revisar jobs, ejecutar etapas y monitorear el pipeline declarativo.")

all_jobs = load_jobs()
available_source_configs = discover_source_configs()
available_source_ids = [path.stem for path in available_source_configs]
default_voice_profile_path = VOICE_PROFILES_DIR / "voicebox-local.json"

with st.expander("Scrapear Periodicos", expanded=not all_jobs):
    st.caption(
        "Crea un job por periodico e intenta descargar la portada desde la misma UI."
    )
    batch_col1, batch_col2 = st.columns(2)
    with batch_col1:
        batch_date = st.date_input("Fecha del lote", value=datetime.now().date(), format="YYYY-MM-DD")
    with batch_col2:
        voice_profile_options = [path.stem for path in sorted(VOICE_PROFILES_DIR.glob("*.json"))]
        default_voice_profile = "voicebox-local" if "voicebox-local" in voice_profile_options else (
            voice_profile_options[0] if voice_profile_options else ""
        )
        batch_voice_profile = st.selectbox(
            "Voice profile",
            voice_profile_options,
            index=voice_profile_options.index(default_voice_profile) if default_voice_profile in voice_profile_options else 0,
        )
    batch_approval_mode = "semi_auto"

    batch_sources = st.multiselect(
        "Periodicos",
        available_source_ids,
        default=available_source_ids,
        placeholder="Selecciona una o mas fuentes",
    )
    with st.expander("Opciones avanzadas", expanded=False):
        batch_opt_col1, batch_opt_col2 = st.columns(2)
        with batch_opt_col1:
            batch_scrape_front_pages = st.checkbox("Descargar portada al crear", value=True)
            batch_force_existing = st.checkbox("Re-scrapear jobs existentes", value=False)
        with batch_opt_col2:
            batch_max_supporting_pages = st.number_input(
                "Max supporting pages",
                min_value=0,
                max_value=10,
                value=3,
                step=1,
            )

    if st.button("Scrapear periodicos", use_container_width=True, type="primary"):
        if not batch_sources:
            st.error("Selecciona al menos un periodico para crear el lote.")
        else:
            try:
                results = create_daily_jobs_batch(
                    job_date=batch_date.isoformat(),
                    source_ids=batch_sources,
                    voice_profile_path=VOICE_PROFILES_DIR / f"{batch_voice_profile}.json",
                    approval_mode=batch_approval_mode,
                    scrape_front_pages=batch_scrape_front_pages,
                    max_supporting_pages=int(batch_max_supporting_pages),
                    force_scrape_existing=batch_force_existing,
                )
                st.session_state["daily_job_batch_results"] = results
                st.success("Lote diario procesado.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    daily_batch_results = st.session_state.get("daily_job_batch_results")
    if daily_batch_results:
        with st.expander("Ver resultado del scraping", expanded=False):
            st.json(daily_batch_results)

all_jobs = load_jobs()
source_options = ["Todos"] + sorted({job.get("source_id", "sin-source") for job in all_jobs}) if all_jobs else ["Todos"]
status_options = ["Todos"] + sorted({job.get("status", "sin-status") for job in all_jobs}) if all_jobs else ["Todos"]

st.sidebar.header("Filtros")
selected_source = st.sidebar.selectbox("Fuente", source_options)
selected_status = st.sidebar.selectbox("Estado", status_options)
text_query = st.sidebar.text_input("Buscar", placeholder="job id, titular o texto")

filtered_jobs = filter_jobs(
    all_jobs,
    selected_source=selected_source,
    selected_status=selected_status,
    text_query=text_query,
)

if all_jobs:
    render_dashboard(filtered_jobs)
else:
    st.info("No se encontraron jobs en `data/jobs/`. Usa el bloque superior para crear el lote diario.")

board_tab, detail_tab = st.tabs(["Jobs", "Detalle"])

with board_tab:
    st.subheader("Portadas y Prompt")
    cover_jobs = [job for job in filtered_jobs if job.get("input_assets", {}).get("front_page_image")]
    if not cover_jobs:
        st.info("Los jobs filtrados no tienen portada disponible para este flujo.")
    else:
        metadata_text = build_cover_batch_metadata(cover_jobs)
        prompt_text = build_cover_batch_prompt(cover_jobs)
        seed_payload = build_cover_batch_seed_payload(cover_jobs)
        st.caption(
            f"Se detectaron {len(cover_jobs)} portadas descargadas en el lote visible. "
            "1. Scrapear periodicos. 2. Revisar portadas. 3. Copiar bloque de portadas. "
            "4. Copiar prompt. 5. Pegar el JSON devuelto por ChatGPT."
        )

        gallery_cols = st.columns(min(4, len(cover_jobs)))
        for index, job in enumerate(cover_jobs[:4]):
            image_path = PROJECT_DIR / str(job.get("input_assets", {}).get("front_page_image"))
            with gallery_cols[index]:
                if image_path.exists():
                    st.image(str(image_path), caption=job.get("source_id", "sin-source"), use_container_width=True)

        copy_col1, copy_col2, copy_col3 = st.columns(3)
        with copy_col1:
            render_copy_button(
                label="Copiar bloque de portadas",
                text=metadata_text,
                key="copy_cover_metadata",
            )
        with copy_col2:
            render_copy_button(
                label="Copiar prompt",
                text=prompt_text,
                key="copy_cover_prompt",
            )
        with copy_col3:
            if st.button("Abrir carpeta de portadas", use_container_width=True):
                run_action(
                    "Carpeta de portadas abierta.",
                    lambda: open_local_path(build_cover_bundle_dir(cover_jobs)),
                )

        st.caption(
            "El prompt copiado se arma solo con las portadas descargadas visibles en este lote."
        )

        with st.expander("Ver texto a copiar", expanded=False):
            st.text_area(
                "Bloque de portadas",
                value=metadata_text,
                height=180,
                key="cover_batch_metadata",
            )
            st.text_area(
                "Prompt",
                value=prompt_text,
                height=320,
                key="cover_batch_prompt",
            )

        with st.expander("Pegar respuesta JSON de ChatGPT", expanded=False):
            batch_json_value = st.text_area(
                "Pega aqui el JSON devuelto por ChatGPT",
                value=seed_payload,
                height=260,
                key="cover_batch_import_payload",
            )
            if st.button("Importar Seleccion Batch", use_container_width=True, type="primary"):
                run_action(
                    "Seleccion batch importada.",
                    lambda: import_cover_page_selection_batch(
                        selection_text=batch_json_value,
                        provider="chatgpt_plus_manual",
                        force=True,
                    ),
                )

        selected_cover_jobs = []
        pending_cover_jobs = []
        unavailable_cover_jobs = []
        for job in cover_jobs:
            selected_page_numbers = [
                int(page_number)
                for page_number in job.get("page_selection", {}).get("selected_page_numbers", [])
                if int(page_number) > 1
            ]
            summary_item = {
                "newspaper_name": job.get("source_id", "sin-source"),
                "job_id": job.get("job_id", "sin-id"),
                "selected_page_numbers": selected_page_numbers,
            }
            if selected_page_numbers:
                selected_cover_jobs.append(summary_item)
            else:
                pending_cover_jobs.append(summary_item)

        for job in filtered_jobs:
            if job.get("input_assets", {}).get("front_page_image"):
                continue
            publication_status = str(job.get("source", {}).get("publication_status") or "")
            status = str(job.get("status") or "")
            if publication_status == "no_publication_for_date" or status in {"skipped", "skipped_no_publication"}:
                reason = "sin edicion publicada para la fecha"
            elif status == "discovered":
                reason = "portada no disponible o no descargable"
            else:
                reason = "sin portada descargada"
            unavailable_cover_jobs.append(
                {
                    "newspaper_name": job.get("source_id", "sin-source"),
                    "job_id": job.get("job_id", "sin-id"),
                    "reason": reason,
                }
            )

        if selected_cover_jobs or pending_cover_jobs or unavailable_cover_jobs:
            st.caption(
                f"{len(selected_cover_jobs)} periodico(s) listos para descargar y "
                f"{len(pending_cover_jobs)} pendiente(s) de seleccion en el lote. "
                f"{len(unavailable_cover_jobs)} sin portada disponible."
            )
            with st.expander("Estado del lote por periodico", expanded=True):
                if selected_cover_jobs:
                    for item in selected_cover_jobs:
                        page_numbers = ", ".join(str(page) for page in item["selected_page_numbers"])
                        render_status_card(
                            title=f"{item['newspaper_name']} · {item['job_id']}",
                            body=f"Listo para descargar. Paginas seleccionadas: {page_numbers}",
                            tone="ready",
                        )
                if pending_cover_jobs:
                    for item in pending_cover_jobs:
                        render_status_card(
                            title=f"{item['newspaper_name']} · {item['job_id']}",
                            body="Pendiente de JSON. Aun no hay paginas seleccionadas.",
                            tone="pending",
                        )
                if unavailable_cover_jobs:
                    for item in unavailable_cover_jobs:
                        render_status_card(
                            title=f"{item['newspaper_name']} · {item['job_id']}",
                            body=f"No disponible en este lote: {item['reason']}.",
                            tone="neutral",
                        )

        if selected_cover_jobs:
            reuse_existing_pages = st.checkbox(
                "Reutilizar paginas ya descargadas del dia actual si existen",
                value=True,
                key="reuse_existing_pages_batch",
            )
            st.caption(
                "Si esta opcion esta activa, el lote usara las paginas ya descargadas cuando coincidan con las seleccionadas."
            )
            if st.button("Descargar paginas del lote", use_container_width=True, type="primary"):
                progress_placeholder = st.empty()
                status_placeholder = st.empty()
                progress_bar = progress_placeholder.progress(0, text="Preparando descarga del lote...")
                status_placeholder.info("Iniciando descarga de paginas seleccionadas...")
                try:
                    total_jobs = len(selected_cover_jobs)
                    results = []
                    for index, item in enumerate(selected_cover_jobs, start=1):
                        matching_job = next(
                            (
                                job
                                for job in cover_jobs
                                if job.get("job_id") == item["job_id"] and job.get("source_id") == item["newspaper_name"]
                            ),
                            None,
                        )
                        if matching_job is None:
                            continue
                        status_placeholder.info(
                            f"Descargando {item['newspaper_name']} · paginas {', '.join(str(page) for page in item['selected_page_numbers'])}"
                        )
                        results.extend(
                            download_selected_pages_batch(
                                jobs=[matching_job],
                                force=not reuse_existing_pages,
                            )
                        )
                        progress_bar.progress(
                            int((index / total_jobs) * 100),
                            text=f"Descargando lote... {index}/{total_jobs}",
                        )
                    st.session_state["selected_pages_batch_results"] = results
                    progress_bar.progress(100, text="Descarga del lote completada.")
                    status_placeholder.success("Paginas seleccionadas descargadas para el lote.")
                    st.rerun()
                except Exception as exc:
                    status_placeholder.error(str(exc))
            selected_pages_batch_results = st.session_state.get("selected_pages_batch_results")
            if selected_pages_batch_results:
                downloaded_jobs_for_prompt = []
                for item in selected_pages_batch_results:
                    matching_job = next(
                        (
                            job
                            for job in load_jobs()
                            if job.get("job_id") == item.get("job_id") and job.get("source_id") == item.get("source_id")
                        ),
                        None,
                    )
                    if matching_job is not None:
                        downloaded_jobs_for_prompt.append(matching_job)

                with st.expander("Ver resultado de descarga de paginas", expanded=True):
                    for item in selected_pages_batch_results:
                        downloaded = ", ".join(str(page) for page in item.get("downloaded_page_numbers", [])) or "ninguna"
                        tone = "downloaded" if item.get("status") == "downloaded" else "neutral"
                        action_label = "Paginas descargadas" if item.get("status") == "downloaded" else "Paginas reutilizadas"
                        render_status_card(
                            title=f"{item.get('source_id', 'sin-source')} · {item.get('job_id', 'sin-id')}",
                            body=f"{action_label}: {downloaded}",
                            tone=tone,
                        )
                        downloaded_pages = item.get("downloaded_pages", [])
                        if downloaded_pages:
                            preview_cols = st.columns(min(3, len(downloaded_pages)))
                            for index, page in enumerate(downloaded_pages[:3]):
                                local_path = page.get("local_path")
                                image_path = PROJECT_DIR / str(local_path) if local_path else None
                                if image_path and image_path.exists():
                                    with preview_cols[index]:
                                        st.image(
                                            str(image_path),
                                            caption=f"Pagina {page.get('page_number')}",
                                            use_container_width=True,
                                        )
                            for page in downloaded_pages:
                                page_number = page.get("page_number")
                                local_path = page.get("local_path")
                                if local_path:
                                    st.markdown(
                                        f"- Pagina `{page_number}`: [{local_path}](/abs/path/{PROJECT_DIR / str(local_path)})"
                                    )
                        else:
                            st.caption("No se registraron paginas descargadas para este periodico.")

                if downloaded_jobs_for_prompt:
                    grouped_jobs = chunk_jobs(downloaded_jobs_for_prompt, size=2)
                    st.subheader("Resumen Detallado por Bloques de 2 Periodicos")
                    st.caption(
                        "Se generaron prompts separados, con maximo 2 periodicos por bloque, para ajustarse mejor "
                        "al limite de imagenes de ChatGPT."
                    )
                    for group_index, group_jobs in enumerate(grouped_jobs, start=1):
                        detailed_prompt = build_detailed_news_prompt(group_jobs)
                        detailed_metadata = build_detailed_news_metadata(group_jobs)
                        group_sources = ", ".join(str(job.get("source_id", "sin-source")) for job in group_jobs)
                        with st.expander(f"Bloque {group_index}: {group_sources}", expanded=(group_index == 1)):
                            detailed_col1, detailed_col2 = st.columns(2)
                            with detailed_col1:
                                render_copy_button(
                                    label=f"Copiar prompt bloque {group_index}",
                                    text=detailed_prompt,
                                    key=f"copy_detailed_news_prompt_{group_index}",
                                )
                            with detailed_col2:
                                if st.button(
                                    f"Abrir carpeta de paginas bloque {group_index}",
                                    use_container_width=True,
                                    key=f"open_pages_group_{group_index}",
                                ):
                                    run_action(
                                        f"Carpeta de paginas del bloque {group_index} abierta.",
                                        lambda group_jobs=group_jobs, group_index=group_index: open_local_path(
                                            build_pages_bundle_dir_for_group(group_jobs, group_index=group_index)
                                        ),
                                    )
                            st.caption(
                                f"Este bloque incluye {len(group_jobs)} periodico(s): {group_sources}."
                            )
                            st.text_area(
                                f"Metadatos de paginas bloque {group_index}",
                                value=detailed_metadata,
                                height=200,
                                key=f"detailed_news_metadata_{group_index}",
                            )
                            st.text_area(
                                f"Prompt de resumen detallado bloque {group_index}",
                                value=detailed_prompt,
                                height=360,
                                key=f"detailed_news_prompt_{group_index}",
                            )

    with st.expander("Ver lista de jobs", expanded=False):
        render_job_board(filtered_jobs)

with detail_tab:
    if not filtered_jobs:
        st.info("No hay jobs disponibles con los filtros actuales.")
        st.stop()

    job_map = {build_job_label(job): job for job in filtered_jobs}
    selected_label = st.sidebar.selectbox("Selecciona un job", list(job_map.keys()))
    job = job_map[selected_label]
    job_path = job["_path"]

    st.sidebar.markdown(f"Manifest: `{rel(job_path)}`")
    st.sidebar.markdown(f"Estado: `{job.get('status', 'sin-status')}`")

    render_job_summary(job)

    extraction = job.get("extraction", {})
    script = job.get("script", {})
    voice = job.get("voice", {})
    subtitles = job.get("subtitles", {})
    video = job.get("video", {})
    publication = job.get("publication", {})
    page_selection = job.get("page_selection", {})

    edited_text = script.get("approved_text", "") or script.get("draft", "")
    edited_notes = script.get("review_notes", "")
    ocr_text_default = ""
    ocr_text_path = extraction.get("ocr_text_path")
    if ocr_text_path:
        candidate = PROJECT_DIR / ocr_text_path
        if candidate.exists():
            ocr_text_default = candidate.read_text(encoding="utf-8")

    overview_tab, script_tab, media_tab, ops_tab, audit_tab = st.tabs(
        ["Overview", "Script", "Media", "Operations", "Audit"]
    )

    with overview_tab:
        left_col, right_col = st.columns([1.05, 1.25])
        with left_col:
            st.subheader("Resumen")
            st.json(
                {
                    "job_id": job.get("job_id"),
                    "source_id": job.get("source_id"),
                    "date": job.get("date"),
                    "status": job.get("status"),
                    "approval_mode": job.get("approval_mode"),
                    "classification": job.get("classification", {}),
                }
            )
            image_path_value = job.get("input_assets", {}).get("front_page_image")
            if image_path_value:
                image_path = PROJECT_DIR / image_path_value
                if image_path.exists():
                    st.subheader("Portada")
                    st.image(str(image_path), use_container_width=True)
        with right_col:
            st.subheader("OCR y Titulares")
            st.markdown(f"Confianza OCR: `{extraction.get('confidence', 0)}`")
            st.markdown("Titulares candidatos")
            headlines = extraction.get("headline_candidates", [])
            if headlines:
                for item in headlines:
                    st.write(f"- {item}")
            else:
                st.caption("Sin titulares detectados.")
            with st.expander("Bloques OCR", expanded=False):
                blocks = extraction.get("ocr_blocks", [])
                if blocks:
                    for block in blocks:
                        st.write(block.get("text", ""))
                else:
                    st.caption("Sin bloques OCR cargados.")
            st.subheader("Publicacion")
            st.markdown(f"Profile: `{publication.get('profile_id', 'sin-profile')}`")
            st.markdown(f"Status: `{publication.get('status', 'not_started')}`")
            if publication.get("title"):
                st.markdown(f"Titulo: `{publication.get('title')}`")
            if publication.get("post_url"):
                st.markdown(f"URL: `{publication.get('post_url')}`")
            st.subheader("Seleccion de Paginas")
            st.markdown(f"Provider: `{page_selection.get('provider') or 'pendiente'}`")
            st.markdown(f"Status: `{page_selection.get('status') or 'not_started'}`")
            st.markdown(
                f"Paginas: `{', '.join(str(item) for item in page_selection.get('selected_page_numbers', [])) or 'ninguna'}`"
            )
            if page_selection.get("notes"):
                st.caption(page_selection.get("notes"))
            with st.expander("Candidatas registradas", expanded=False):
                candidates = page_selection.get("candidates", [])
                if candidates:
                    st.json(candidates)
                else:
                    st.caption("Sin candidatas registradas.")

    with script_tab:
        st.subheader("Revision del Guion")
        st.markdown("Borrador actual")
        st.code(script.get("draft", "") or "(sin draft)", language="text")
        edited_text = st.text_area("Texto final aprobado", value=edited_text, height=180)
        edited_notes = st.text_area("Notas de revision", value=edited_notes, height=80)
        action_col1, action_col2 = st.columns(2)
        with action_col1:
            if st.button("Guardar Edicion", use_container_width=True):
                update_job_script(job_path, edited_text, edited_notes, approve=False)
                st.success("Cambios guardados en el job-manifest.")
                st.rerun()
        with action_col2:
            if st.button("Aprobar Guion", use_container_width=True, type="primary"):
                update_job_script(job_path, edited_text, edited_notes, approve=True)
                st.success("Guion aprobado y job actualizado.")
                st.rerun()

    with media_tab:
        st.subheader("Audio y Subtitulos")
        meta_col1, meta_col2 = st.columns(2)
        with meta_col1:
            st.markdown(f"Voice profile: `{voice.get('profile_id', 'sin-profile')}`")
            st.markdown(f"Audio: `{voice.get('audio_path') or 'pendiente'}`")
        with meta_col2:
            st.markdown(f"Subtitle policy: `{subtitles.get('policy_id', 'sin-policy')}`")
            st.markdown(f"Segments: `{subtitles.get('segments_path') or 'pendiente'}`")

        st.subheader("Preview Remotion")
        st.markdown(f"Story manifest: `{video.get('story_manifest_path') or 'pendiente'}`")
        st.markdown(f"Composition: `{video.get('preview_composition_id') or 'NewsVideo-generated'}`")

        segments_path_value = subtitles.get("segments_path")
        if segments_path_value:
            segments_path = PROJECT_DIR / segments_path_value
            if segments_path.exists():
                with st.expander("Ver segmentos de subtitulo", expanded=False):
                    st.json(read_json(segments_path))

    with ops_tab:
        st.subheader("Acciones del Pipeline")
        voice_profile_path = get_voice_profile_path(voice.get("profile_id"))

        with st.expander("Extract + Classify", expanded=False):
            ocr_text_value = st.text_area(
                "OCR manual",
                value=ocr_text_default,
                height=140,
                key=f"ocr_text_value_{job.get('job_id')}",
            )
            ocr_confidence_value = st.number_input(
                "OCR confidence",
                min_value=0.0,
                max_value=1.0,
                value=float(extraction.get("confidence", 0.82) or 0.82),
                step=0.01,
                key=f"ocr_confidence_{job.get('job_id')}",
            )
            if st.button("Ejecutar Extract Job", use_container_width=True):
                run_action(
                    "Extract-job completado.",
                    lambda: extract_and_classify_job(
                        job_manifest_path=job_path,
                        editorial_policy_path=DEFAULT_EDITORIAL_POLICY,
                        ocr_text=ocr_text_value,
                        ocr_confidence=ocr_confidence_value,
                    ),
                )

        with st.expander("Cover Pages", expanded=False):
            source_config_value = job.get("source", {}).get("source_config_path") or job.get("input_assets", {}).get(
                "source_config"
            )
            source_config_path = PROJECT_DIR / source_config_value if source_config_value else None
            manual_selection_default = json.dumps(
                {
                    "notes": "Seleccion manual desde Streamlit.",
                    "items": page_selection.get("candidates", []),
                },
                ensure_ascii=False,
                indent=2,
            )
            cover_col1, cover_col2 = st.columns(2)
            with cover_col1:
                if st.button("Analizar OCR de Portada", use_container_width=True):
                    run_action(
                        "Analisis de portada completado.",
                        lambda: analyze_cover_page_references_for_job(
                            job_manifest_path=job_path,
                            max_candidates=6,
                            force=True,
                        ),
                    )
            with cover_col2:
                if source_config_path is None or not source_config_path.exists():
                    st.warning("No se encontro `source_config` para descargar paginas seleccionadas.")
                elif st.button("Descargar Paginas Seleccionadas", use_container_width=True):
                    run_action(
                        "Paginas seleccionadas descargadas.",
                        lambda: scrape_selected_pages_for_job(
                            job_manifest_path=job_path,
                            source_config_path=source_config_path,
                            force=True,
                        ),
                    )
            manual_selection_value = st.text_area(
                "JSON manual de seleccion",
                value=manual_selection_default,
                height=220,
                key=f"manual_cover_selection_{job.get('job_id')}",
            )
            if st.button("Importar Seleccion Manual", use_container_width=True, type="primary"):
                run_action(
                    "Seleccion manual importada.",
                    lambda: import_cover_page_selection_for_job(
                        job_manifest_path=job_path,
                        selection_text=manual_selection_value,
                        provider="chatgpt_plus_manual",
                        force=True,
                    ),
                )

        with st.expander("Script", expanded=False):
            script_col1, script_col2 = st.columns(2)
            with script_col1:
                if st.button("Generar Draft", use_container_width=True):
                    run_action(
                        "Draft generado.",
                        lambda: generate_script_from_job(
                            job_manifest_path=job_path,
                            script_template_path=DEFAULT_SCRIPT_TEMPLATE,
                            force=True,
                        ),
                    )
            with script_col2:
                if st.button("Aprobar Draft Actual", use_container_width=True):
                    run_action(
                        "Draft aprobado.",
                        lambda: approve_script_for_job(
                            job_manifest_path=job_path,
                            approved_text=edited_text,
                            review_notes=edited_notes,
                        ),
                    )

        with st.expander("Voice + Subtitle", expanded=False):
            if voice_profile_path is None:
                st.warning("No se encontro el perfil de voz del job.")
            else:
                st.markdown(f"Voice profile usado: `{rel(voice_profile_path)}`")
                if st.button("Generar Voz y Subtitulos", use_container_width=True):
                    run_action(
                        "Audio y subtitulos generados.",
                        lambda: generate_voice_and_subtitles_for_job(
                            job_manifest_path=job_path,
                            voice_profile_path=voice_profile_path,
                            subtitle_policy_path=DEFAULT_SUBTITLE_POLICY,
                            force=True,
                        ),
                    )

        with st.expander("Compose Preview", expanded=False):
            if voice_profile_path is None:
                st.warning("No se encontro el perfil de voz del job.")
            else:
                compose_col1, compose_col2 = st.columns(2)
                with compose_col1:
                    if st.button("Build Story Manifest", use_container_width=True):
                        run_action(
                            "Story manifest generado.",
                            lambda: build_story_manifest_from_job(
                                job_manifest_path=job_path,
                                voice_profile_path=voice_profile_path,
                                video_template_path=DEFAULT_VIDEO_TEMPLATE,
                            ),
                        )
                with compose_col2:
                    if st.button("Compose Job para Preview", use_container_width=True):
                        run_action(
                            "Preview compuesto para Remotion.",
                            lambda: compose_job_for_preview(
                                job_manifest_path=job_path,
                                video_template_path=DEFAULT_VIDEO_TEMPLATE,
                            ),
                        )

        with st.expander("Publish", expanded=False):
            publish_col1, publish_col2 = st.columns(2)
            with publish_col1:
                if st.button("Preparar Publicacion", use_container_width=True):
                    run_action(
                        "Publicacion preparada.",
                        lambda: publish_job(
                            job_manifest_path=job_path,
                            publishing_profile_path=DEFAULT_PUBLISHING_PROFILE,
                            confirm=False,
                        ),
                    )
            with publish_col2:
                if st.button("Confirmar Cola de Publicacion", use_container_width=True):
                    run_action(
                        "Job marcado para publicacion.",
                        lambda: publish_job(
                            job_manifest_path=job_path,
                            publishing_profile_path=DEFAULT_PUBLISHING_PROFILE,
                            confirm=True,
                        ),
                    )

    with audit_tab:
        st.subheader("Audit Trail")
        render_event_timeline(job)
        with st.expander("Manifest Completo", expanded=False):
            st.json(job)
