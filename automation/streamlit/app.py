from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

import streamlit as st


PROJECT_DIR = Path(__file__).resolve().parents[2]
JOBS_DIR = PROJECT_DIR / "data" / "jobs"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def discover_jobs() -> list[Path]:
    if not JOBS_DIR.exists():
        return []
    return sorted(JOBS_DIR.glob("*/*/job-manifest.json"), reverse=True)


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_DIR).as_posix()


def load_job_options() -> dict[str, Path]:
    options: dict[str, Path] = {}
    for path in discover_jobs():
        job = read_json(path)
        label = f"{job.get('date', 'sin-fecha')} | {job.get('source_id', 'sin-source')} | {job.get('status', 'sin-status')} | {job.get('job_id', path.parent.name)}"
        options[label] = path
    return options


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


st.set_page_config(page_title="News Video MVP Review", layout="wide")
st.title("News Video MVP Review")
st.caption("Panel ligero para revisar jobs, OCR y guiones sobre los manifests del pipeline.")

job_options = load_job_options()
if not job_options:
    st.info("No se encontraron jobs en `data/jobs/`.")
    st.stop()

selected_label = st.sidebar.selectbox("Selecciona un job", list(job_options.keys()))
job_path = job_options[selected_label]
job = read_json(job_path)

st.sidebar.markdown(f"Manifest: `{rel(job_path)}`")
st.sidebar.markdown(f"Estado: `{job.get('status', 'sin-status')}`")

col1, col2 = st.columns([1.1, 1.4])

with col1:
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

with col2:
    st.subheader("OCR y Titulares")
    extraction = job.get("extraction", {})
    st.markdown(f"Confianza OCR: `{extraction.get('confidence', 0)}`")
    st.markdown("Titulares candidatos")
    for item in extraction.get("headline_candidates", []):
        st.write(f"- {item}")

    with st.expander("Bloques OCR", expanded=False):
        blocks = extraction.get("ocr_blocks", [])
        if blocks:
            for block in blocks:
                st.write(block.get("text", ""))
        else:
            st.caption("Sin bloques OCR cargados.")

st.subheader("Audio y Subtitulos")
voice = job.get("voice", {})
subtitles = job.get("subtitles", {})
meta_col1, meta_col2 = st.columns(2)
with meta_col1:
    st.markdown(f"Voice profile: `{voice.get('profile_id', 'sin-profile')}`")
    st.markdown(f"Audio: `{voice.get('audio_path') or 'pendiente'}`")
with meta_col2:
    st.markdown(f"Subtitle policy: `{subtitles.get('policy_id', 'sin-policy')}`")
    st.markdown(f"Segments: `{subtitles.get('segments_path') or 'pendiente'}`")

segments_path_value = subtitles.get("segments_path")
if segments_path_value:
    segments_path = PROJECT_DIR / segments_path_value
    if segments_path.exists():
        with st.expander("Ver segmentos de subtitulo", expanded=False):
            subtitle_payload = read_json(segments_path)
            st.json(subtitle_payload)

st.subheader("Revision del Guion")
script = job.get("script", {})
draft = script.get("draft", "")
approved = script.get("approved_text", "") or draft
notes = script.get("review_notes", "")

st.markdown("Borrador actual")
st.code(draft or "(sin draft)", language="text")

edited_text = st.text_area("Texto final aprobado", value=approved, height=180)
edited_notes = st.text_area("Notas de revision", value=notes, height=80)

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
