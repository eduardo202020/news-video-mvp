from __future__ import annotations

from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import sys

import streamlit as st


PROJECT_DIR = Path(__file__).resolve().parents[2]
JOBS_DIR = PROJECT_DIR / "data" / "jobs"
SRC_DIR = PROJECT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from news_video_mvp.automation_pipeline import (  # noqa: E402
    approve_script_for_job,
    build_story_manifest_from_job,
    compose_job_for_preview,
    extract_and_classify_job,
    generate_script_from_job,
    generate_voice_and_subtitles_for_job,
    publish_job,
)


DEFAULT_EDITORIAL_POLICY = PROJECT_DIR / "automation" / "rules" / "editorial-policy.json"
DEFAULT_SCRIPT_TEMPLATE = PROJECT_DIR / "automation" / "templates" / "scripts" / "default-anchor.json"
DEFAULT_VIDEO_TEMPLATE = PROJECT_DIR / "automation" / "templates" / "video" / "vertical-news.json"
DEFAULT_SUBTITLE_POLICY = PROJECT_DIR / "automation" / "rules" / "subtitle-policy.json"
DEFAULT_PUBLISHING_PROFILE = PROJECT_DIR / "automation" / "templates" / "publishing" / "tiktok.json"
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


def load_jobs() -> list[dict]:
    jobs: list[dict] = []
    for path in discover_jobs():
        job = read_json(path)
        job["_path"] = path
        jobs.append(job)
    return jobs


def get_voice_profile_path(profile_id: str | None) -> Path | None:
    if not profile_id:
        return None
    candidate = VOICE_PROFILES_DIR / f"{profile_id}.json"
    return candidate if candidate.exists() else None


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
if not all_jobs:
    st.info("No se encontraron jobs en `data/jobs/`.")
    st.stop()

source_options = ["Todos"] + sorted({job.get("source_id", "sin-source") for job in all_jobs})
status_options = ["Todos"] + sorted({job.get("status", "sin-status") for job in all_jobs})

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

render_dashboard(filtered_jobs)

board_tab, detail_tab = st.tabs(["Jobs", "Detalle"])

with board_tab:
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
