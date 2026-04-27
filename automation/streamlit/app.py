from __future__ import annotations

from collections import Counter
import copy
from datetime import datetime
import base64
import importlib
import json
import os
from pathlib import Path
import shutil
import sys

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image


PROJECT_DIR = Path(__file__).resolve().parents[2]
JOBS_DIR = PROJECT_DIR / "data" / "jobs"
SOURCES_DIR = PROJECT_DIR / "automation" / "sources" / "diarios"
SRC_DIR = PROJECT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from news_video_mvp import composer as composer_module  # noqa: E402
from news_video_mvp import automation_pipeline as pipeline_module  # noqa: E402
from news_video_mvp import subtitles as subtitles_module  # noqa: E402

importlib.invalidate_caches()
subtitles_module = importlib.reload(subtitles_module)
composer_module = importlib.reload(composer_module)
pipeline_module = importlib.reload(pipeline_module)
analyze_cover_page_references_for_job = pipeline_module.analyze_cover_page_references_for_job
approve_script_for_job = pipeline_module.approve_script_for_job
build_job_id = pipeline_module.build_job_id
build_daily_rundown_for_date = pipeline_module.build_daily_rundown_for_date
build_story_manifest_from_job = pipeline_module.build_story_manifest_from_job
compose_job_for_preview = pipeline_module.compose_job_for_preview
create_job_manifest = pipeline_module.create_job_manifest
extract_and_classify_job = pipeline_module.extract_and_classify_job
generate_script_from_job = pipeline_module.generate_script_from_job
generate_voice_and_subtitles_for_job = pipeline_module.generate_voice_and_subtitles_for_job
get_story_type_narrator_map_path = pipeline_module.get_story_type_narrator_map_path
import_cover_page_selection_batch = pipeline_module.import_cover_page_selection_batch
import_cover_page_selection_for_job = pipeline_module.import_cover_page_selection_for_job
import_story_narrative_batch = pipeline_module.import_story_narrative_batch
import_story_narrative_for_job = pipeline_module.import_story_narrative_for_job
publish_job = pipeline_module.publish_job
retry_daily_rundown_from_existing_audio = pipeline_module.retry_daily_rundown_from_existing_audio
scrape_source_into_job = pipeline_module.scrape_source_into_job
scrape_selected_pages_for_job = pipeline_module.scrape_selected_pages_for_job
normalize_cover_region = pipeline_module._normalize_cover_region


DEFAULT_EDITORIAL_POLICY = PROJECT_DIR / "automation" / "rules" / "editorial-policy.json"
DEFAULT_SCRIPT_TEMPLATE = PROJECT_DIR / "automation" / "templates" / "scripts" / "default-anchor.json"
DEFAULT_VIDEO_TEMPLATE = PROJECT_DIR / "automation" / "templates" / "video" / "vertical-news.json"
DEFAULT_SUBTITLE_POLICY = PROJECT_DIR / "automation" / "rules" / "subtitle-policy.json"
DEFAULT_PUBLISHING_PROFILE = PROJECT_DIR / "automation" / "templates" / "publishing" / "tiktok.json"
DEFAULT_COVER_BATCH_PROMPT = (
    PROJECT_DIR / "automation" / "templates" / "prompts" / "cover-page-selection-batch.md"
)
VOICE_PROFILES_DIR = PROJECT_DIR / "automation" / "templates" / "voices"
DEV_CACHE_DIR = PROJECT_DIR / "data" / "dev-cache"
CHATGPT_CACHE_PREFIX = "chatgpt-responses"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def image_to_data_url(path: Path, *, max_width: int = 720) -> str:
    with Image.open(path) as image:
        image = image.convert("RGB")
        if image.width > max_width:
            target_height = int(image.height * (max_width / image.width))
            image = image.resize((max_width, max(1, target_height)))
        from io import BytesIO

        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=88)
    payload = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{payload}"


def get_scaled_dimensions(path: Path, *, max_width: int) -> tuple[int, int]:
    dimensions = get_image_dimensions(path) or (max_width, max_width)
    width, height = dimensions
    if width <= 0 or height <= 0:
        return max_width, max_width
    if width <= max_width:
        return width, height
    scaled_height = int(height * (max_width / width))
    return max_width, max(1, scaled_height)


def get_chatgpt_response_cache_path(batch_date: str) -> Path:
    safe_date = "".join(char for char in str(batch_date) if char.isdigit() or char in {"-"}) or "unknown-date"
    return DEV_CACHE_DIR / f"{CHATGPT_CACHE_PREFIX}-{safe_date}.json"


def read_chatgpt_response_cache(batch_date: str) -> dict:
    cache_path = get_chatgpt_response_cache_path(batch_date)
    if not cache_path.exists():
        return {"batch_date": batch_date, "responses": {}}
    try:
        payload = read_json(cache_path)
    except Exception:
        return {"batch_date": batch_date, "responses": {}}
    if not isinstance(payload.get("responses"), dict):
        payload["responses"] = {}
    return payload


def write_chatgpt_response_cache(batch_date: str, payload: dict) -> Path:
    DEV_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = get_chatgpt_response_cache_path(batch_date)
    payload = {
        **payload,
        "batch_date": batch_date,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    write_json(cache_path, payload)
    return cache_path


def save_chatgpt_response_cache_value(batch_date: str, key: str, value: str) -> Path:
    payload = read_chatgpt_response_cache(batch_date)
    payload.setdefault("responses", {})
    payload["responses"][key] = value
    return write_chatgpt_response_cache(batch_date, payload)


def get_chatgpt_response_cache_value(batch_date: str, key: str, default: str) -> str:
    if key in st.session_state:
        return str(st.session_state[key])
    payload = read_chatgpt_response_cache(batch_date)
    responses = payload.get("responses", {})
    cached_value = responses.get(key)
    if cached_value is None:
        return default
    return str(cached_value)


def save_rendered_chatgpt_response(batch_date: str, key: str, value: str, default: str) -> None:
    existing = read_chatgpt_response_cache(batch_date).get("responses", {})
    if value != default or key in existing:
        save_chatgpt_response_cache_value(batch_date, key, value)


def cache_chatgpt_widget_value(batch_date: str, key: str) -> None:
    save_chatgpt_response_cache_value(batch_date, key, str(st.session_state.get(key, "")))


def load_chatgpt_response_cache_into_session(batch_date: str) -> int:
    payload = read_chatgpt_response_cache(batch_date)
    responses = payload.get("responses", {})
    for key, value in responses.items():
        st.session_state[str(key)] = str(value)
    return len(responses)


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_DIR).as_posix()


def get_image_dimensions(path: Path) -> tuple[int, int] | None:
    if not path.exists():
        return None
    try:
        with Image.open(path) as image:
            return image.size
    except Exception:
        return None


def load_story_type_narrator_map() -> dict:
    mapping_path = get_story_type_narrator_map_path(PROJECT_DIR)
    if not mapping_path.exists():
        return {"story_types": {}, "default_narrator_profile_id": ""}
    payload = read_json(mapping_path)
    if not isinstance(payload.get("story_types"), dict):
        payload["story_types"] = {}
    return payload


def get_default_narrator_for_story_type(story_type: str | None) -> str:
    mapping = load_story_type_narrator_map()
    story_types = mapping.get("story_types", {})
    normalized_story_type = str(story_type or "actualidad").strip().lower() or "actualidad"
    if isinstance(story_types, dict):
        configured = story_types.get(normalized_story_type, {})
        narrator = str(configured.get("narrator_profile_id") or "").strip()
        if narrator:
            return narrator
    return str(mapping.get("default_narrator_profile_id") or "").strip()


def discover_jobs() -> list[Path]:
    if not JOBS_DIR.exists():
        return []
    return sorted(JOBS_DIR.glob("*/*/job-manifest.json"), reverse=True)


def discover_source_configs() -> list[Path]:
    if not SOURCES_DIR.exists():
        return []
    return sorted(SOURCES_DIR.glob("*.json"))


def load_jobs() -> list[dict]:
    for path in discover_jobs():
        job = read_json(path)
        job["_path"] = path
        yield job


def list_jobs() -> list[dict]:
    return sorted(load_jobs(), key=_job_sort_key, reverse=True)


def get_default_batch_date(jobs: list[dict]) -> str:
    if "active_batch_date" in st.session_state:
        return str(st.session_state["active_batch_date"])
    if jobs:
        return str(jobs[0].get("date") or datetime.now().date().isoformat())
    return datetime.now().date().isoformat()


def filter_jobs_by_date(jobs: list[dict], *, selected_date: str) -> list[dict]:
    return [job for job in jobs if str(job.get("date") or "") == selected_date]


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
        error_message = None
        if scrape_front_pages:
            try:
                scrape_source_into_job(
                    job_manifest_path=manifest_path,
                    source_config_path=source_config_path,
                    max_supporting_pages=max_supporting_pages,
                    force=force_scrape_existing,
                )
                status = "scraped" if created_now else "existing_scraped"
            except Exception as exc:
                status = "scrape_failed"
                error_message = str(exc)

        payload: dict[str, object] = {
            "source_id": source_id,
            "job_id": job_id,
            "job_manifest_path": rel(manifest_path),
            "status": status,
        }
        if manifest_path.exists():
            job = read_json(manifest_path)
            payload["job_status"] = job.get("status")
            payload["publication_status"] = job.get("source", {}).get("publication_status")
            payload["front_page_image"] = job.get("input_assets", {}).get("front_page_image")
            payload["front_page_url"] = job.get("source", {}).get("front_page_url")
        if error_message:
            payload["error"] = error_message
        results.append(payload)

    return results


def render_daily_batch_results(results: list[dict[str, object]], *, selected_date: str) -> None:
    if not results:
        return

    successful = [
        item for item in results if item.get("front_page_image") and item.get("status") != "scrape_failed"
    ]
    missing_front_page = [
        item
        for item in results
        if not item.get("front_page_image")
        and item.get("publication_status") != "no_publication_for_date"
        and item.get("status") != "missing_source_config"
    ]
    no_publication = [
        item for item in results if item.get("publication_status") == "no_publication_for_date"
    ]
    config_errors = [item for item in results if item.get("status") == "missing_source_config"]

    summary_cols = st.columns(4)
    summary_cols[0].metric("Con portada", len(successful))
    summary_cols[1].metric("Sin portada", len(missing_front_page))
    summary_cols[2].metric("Sin edicion", len(no_publication))
    summary_cols[3].metric("Errores config", len(config_errors))

    if successful:
        st.success(
            f"Lote `{selected_date}`: {len(successful)} fuente(s) con portada descargada."
        )
    if missing_front_page:
        st.warning(
            "Algunas fuentes no terminaron con portada descargada. Revisa el detalle por periodico antes de continuar."
        )

    with st.expander("Estado del scraping por periodico", expanded=True):
        for item in results:
            source_id = str(item.get("source_id") or "sin-source")
            job_id = str(item.get("job_id") or "sin-id")
            publication_status = str(item.get("publication_status") or "")
            error_message = str(item.get("error") or "").strip()
            if item.get("status") == "missing_source_config":
                body = "No se encontro source config para esta fuente."
                tone = "neutral"
            elif publication_status == "no_publication_for_date":
                body = "La fuente no tiene edicion publicada para esta fecha."
                tone = "neutral"
            elif item.get("front_page_image"):
                body = f"Portada lista en `{item.get('front_page_image')}`."
                tone = "ready"
            else:
                body = "El job se creo pero no quedo una portada descargada."
                if error_message:
                    body += f" Error: {error_message}"
                tone = "pending"
            render_status_card(
                title=f"{source_id} · {job_id}",
                body=body,
                tone=tone,
            )


def download_selected_pages_batch(
    *,
    jobs: list[dict],
    force: bool = True,
    selected_page_numbers_override: dict[str, list[int]] | None = None,
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for job in jobs:
        page_selection = job.get("page_selection", {})
        job_id = str(job.get("job_id") or "")
        selected_page_numbers = [
            int(page_number)
            for page_number in (
                (selected_page_numbers_override or {}).get(job_id)
                or page_selection.get("selected_page_numbers", [])
            )
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

        if job_requires_web_research(job):
            results.append(
                {
                    "job_id": job.get("job_id", ""),
                    "source_id": job.get("source_id", ""),
                    "selected_page_numbers": selected_page_numbers,
                    "downloaded_page_numbers": [],
                    "downloaded_pages": [],
                    "status": "web_research_required",
                }
            )
            continue

        should_force_scrape = force or bool(current_pages)
        scrape_selected_pages_for_job(
            job_manifest_path=manifest_path,
            source_config_path=source_config_path,
            force=should_force_scrape,
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
                "status": "downloaded" if not current_pages else "refreshed",
            }
        )
    return results


def get_job_source_config_payload(job: dict) -> dict:
    source_config_value = job.get("source", {}).get("source_config_path") or job.get("input_assets", {}).get(
        "source_config"
    )
    if not source_config_value:
        return {}
    source_config_path = PROJECT_DIR / str(source_config_value)
    if not source_config_path.exists():
        return {}
    try:
        return read_json(source_config_path)
    except Exception:
        return {}


def get_job_discovery_type(job: dict) -> str:
    source_config = get_job_source_config_payload(job)
    discovery = source_config.get("discovery", {})
    if not isinstance(discovery, dict):
        return ""
    return str(discovery.get("type") or "").strip()


def job_requires_web_research(job: dict) -> bool:
    return get_job_discovery_type(job) == "direct_image_url"


def get_supporting_pages(job: dict) -> list[dict]:
    return [
        page
        for page in job.get("input_assets", {}).get("pages", [])
        if int(page.get("page_number") or 0) > 1
    ]


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


def update_job_story_cover_region(
    *,
    job_path: Path,
    story_index: int,
    cover_region: dict[str, float] | None,
) -> tuple[dict, list[str]]:
    job = read_json(job_path)
    stories = job.setdefault("story_narrative", {}).setdefault("stories", [])
    if story_index < 0 or story_index >= len(stories):
        raise ValueError("La historia seleccionada ya no existe en el job-manifest.")

    normalized_cover_region = normalize_cover_region(cover_region) if cover_region else None
    stories[story_index]["cover_region"] = normalized_cover_region

    headline = str(stories[story_index].get("headline") or "").strip()
    story_type = str(stories[story_index].get("story_type") or "").strip().lower()
    for cover_story in job.get("page_selection", {}).get("stories", []):
        if (
            str(cover_story.get("headline") or "").strip() == headline
            and str(cover_story.get("story_type") or "").strip().lower() == story_type
        ):
            cover_story["cover_region"] = normalized_cover_region

    job.setdefault("audit", {})
    job["audit"].setdefault("events", [])
    timestamp = datetime.now().isoformat(timespec="seconds")
    job["audit"]["events"].append(
        {
            "stage": "focus_review_ui",
            "status": "edited",
            "timestamp": timestamp,
            "details": (
                f"Enfoque manual actualizado para historia {story_index + 1}: "
                f"{headline or 'sin titular'}."
            ),
        }
    )
    job["audit"]["updated_at"] = timestamp
    write_json(job_path, job)

    notes: list[str] = []
    voice_profile_path = get_voice_profile_path(job.get("voice", {}).get("profile_id")) or (
        VOICE_PROFILES_DIR / "voicebox-local.json"
    )
    story_manifest_value = str(job.get("video", {}).get("story_manifest_path") or "").strip()
    resolved_story_manifest_path = PROJECT_DIR / story_manifest_value if story_manifest_value else None
    try:
        built_story_manifest = build_story_manifest_from_job(
            job_manifest_path=job_path,
            video_template_path=DEFAULT_VIDEO_TEMPLATE,
            voice_profile_path=voice_profile_path,
            output_path=resolved_story_manifest_path if resolved_story_manifest_path else None,
        )
        notes.append(f"Story manifest resincronizado: `{rel(built_story_manifest)}`.")
        if job.get("voice", {}).get("audio_path"):
            composed_path = compose_job_for_preview(
                job_manifest_path=job_path,
                story_manifest_path=built_story_manifest,
                video_template_path=DEFAULT_VIDEO_TEMPLATE,
            )
            notes.append(f"Preview Remotion actualizado: `{rel(composed_path)}`.")
    except Exception as exc:
        notes.append(f"El enfoque se guardo, pero no se pudo recomponer el preview: {exc}")

    return read_json(job_path), notes


def render_cover_focus_preview(
    *,
    image_path: Path,
    cover_region: dict[str, float] | None,
    title: str | None = None,
) -> None:
    preview_width = 540
    data_url = image_to_data_url(image_path, max_width=preview_width)
    rendered_width, rendered_height = get_scaled_dimensions(image_path, max_width=preview_width)
    normalized = normalize_cover_region(cover_region)
    if normalized:
        x = normalized["x"] * 100
        y = normalized["y"] * 100
        width = normalized["width"] * 100
        height = normalized["height"] * 100
        overlay_html = f"""
        <div style="position:absolute;left:{x:.3f}%;top:{y:.3f}%;width:{width:.3f}%;height:{height:.3f}%;
                    border:3px solid #ffca28;border-radius:12px;box-shadow:0 0 0 9999px rgba(8,8,10,.18) inset;">
          <div style="position:absolute;left:10px;top:10px;padding:6px 10px;border-radius:999px;
                      background:rgba(10,10,14,.82);color:#ffca28;font:700 14px/1 sans-serif;">
            focus
          </div>
        </div>
        """
        focus_center_x = (normalized["x"] + normalized["width"] / 2) * 100
        focus_center_y = (normalized["y"] + normalized["height"] / 2) * 100
        crop_html = f"""
        <div style="position:relative;overflow:hidden;border-radius:14px;background:#0f1014;height:240px;">
          <img src="{data_url}" style="position:absolute;left:{50 - focus_center_x:.3f}%;top:{50 - focus_center_y:.3f}%;
               width:100%;height:100%;object-fit:contain;transform:scale({max(1.0, min(3.2, 0.9 / max(normalized['width'], normalized['height'], 0.08))):.3f});
               transform-origin:center center;" />
        </div>
        """
    else:
        overlay_html = ""
        crop_html = """
        <div style="display:flex;align-items:center;justify-content:center;height:240px;border-radius:14px;
                    background:#101116;color:#d8d8de;font:600 15px/1.4 sans-serif;">
          Sin zoom. Se mostrara la portada completa.
        </div>
        """
    header_html = f"<div style='margin-bottom:10px;color:#f3f4f6;font:700 15px/1.3 sans-serif;'>{title}</div>" if title else ""
    html = f"""
    <div style="display:grid;grid-template-columns:minmax(0,1.35fr) minmax(220px,.8fr);gap:16px;align-items:start;">
      <div>
        {header_html}
        <div style="position:relative;width:{rendered_width}px;border-radius:16px;overflow:hidden;background:#0f1014;border:1px solid rgba(255,255,255,.08);">
          <img src="{data_url}" style="display:block;width:{rendered_width}px;height:{rendered_height}px;" />
          {overlay_html}
        </div>
      </div>
      <div>
        <div style="margin-bottom:10px;color:#f3f4f6;font:700 15px/1.3 sans-serif;">Vista aproximada del enfoque</div>
        {crop_html}
      </div>
    </div>
    """
    component_height = max(rendered_height + 120, 520)
    components.html(html, height=component_height, scrolling=False)


def render_focus_editor_for_job(
    *,
    job: dict,
    job_path: Path,
    ui_prefix: str,
) -> None:
    focus_entries = get_story_narrative_entries(job)
    if not focus_entries:
        st.caption("Todavia no hay historias importadas para corregir el enfoque.")
        return

    front_page_path_value = job.get("input_assets", {}).get("front_page_image")
    if not front_page_path_value:
        st.caption("Este job todavia no tiene portada para ajustar el enfoque.")
        return
    image_path = PROJECT_DIR / str(front_page_path_value)
    if not image_path.exists():
        st.caption("No se encontro la portada local para este job.")
        return

    story_options = [
        f"{index + 1}. {str(story.get('headline') or 'Sin titular')} · {str(story.get('story_type') or 'actualidad')}"
        for index, story in enumerate(focus_entries)
    ]
    selected_story_label = st.selectbox(
        "Historia a corregir",
        story_options,
        key=f"{ui_prefix}_story_selector",
    )
    story_index = story_options.index(selected_story_label)
    story_entry = focus_entries[story_index]
    headline = str(story_entry.get("headline") or f"Historia {story_index + 1}")
    story_type = str(story_entry.get("story_type") or "actualidad")
    narrator_id = str(story_entry.get("narrator_profile_id") or "sin-narrador")
    current_region = normalize_cover_region(story_entry.get("cover_region"))
    clear_focus = st.checkbox(
        "Sin zoom",
        value=current_region is None,
        key=f"{ui_prefix}_clear_{story_index}",
        help="Activa esto si prefieres mostrar la portada completa sin enfoque automatico para esta historia.",
    )
    editor_col1, editor_col2, editor_col3, editor_col4 = st.columns(4)
    x_value = editor_col1.number_input(
        "x",
        min_value=0.0,
        max_value=1.0,
        value=float((current_region or {}).get("x", 0.0)),
        step=0.01,
        key=f"{ui_prefix}_x_{story_index}",
        disabled=clear_focus,
    )
    y_value = editor_col2.number_input(
        "y",
        min_value=0.0,
        max_value=1.0,
        value=float((current_region or {}).get("y", 0.0)),
        step=0.01,
        key=f"{ui_prefix}_y_{story_index}",
        disabled=clear_focus,
    )
    width_value = editor_col3.number_input(
        "width",
        min_value=0.01,
        max_value=1.0,
        value=float((current_region or {}).get("width", 0.45)),
        step=0.01,
        key=f"{ui_prefix}_w_{story_index}",
        disabled=clear_focus,
    )
    height_value = editor_col4.number_input(
        "height",
        min_value=0.01,
        max_value=1.0,
        value=float((current_region or {}).get("height", 0.2)),
        step=0.01,
        key=f"{ui_prefix}_h_{story_index}",
        disabled=clear_focus,
    )
    preview_region = None if clear_focus else {
        "x": x_value,
        "y": y_value,
        "width": width_value,
        "height": height_value,
    }
    st.caption(
        f"{headline} · {story_type} · {narrator_id}. "
        "La caja amarilla y la vista de la derecha se actualizan mientras cambias los valores."
    )
    render_cover_focus_preview(
        image_path=image_path,
        cover_region=preview_region,
        title=str(job.get("source_id") or "sin-source"),
    )
    st.caption(
        "Valores normalizados sobre la portada: `x` y `y` son la esquina superior izquierda; "
        "`width` y `height` el tamano relativo del recorte."
    )
    if st.button("Guardar enfoque", key=f"{ui_prefix}_save_{story_index}", use_container_width=True):
        try:
            updated_job, sync_notes = update_job_story_cover_region(
                job_path=job_path,
                story_index=story_index,
                cover_region=preview_region,
            )
            st.session_state[f"{ui_prefix}_focus_notes_{story_index}"] = sync_notes
            st.success("Enfoque guardado.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
    saved_notes = st.session_state.get(f"{ui_prefix}_focus_notes_{story_index}", [])
    for note in saved_notes:
        st.caption(note)


def run_action(label: str, action) -> None:
    try:
        action()
        st.success(label)
        st.rerun()
    except Exception as exc:
        st.error(str(exc))


def import_cover_selection_with_dev_cache(*, batch_date: str, selection_text: str, dev_cache_enabled: bool) -> None:
    if dev_cache_enabled:
        save_chatgpt_response_cache_value(batch_date, "cover_batch_import_payload", selection_text)
    import_cover_page_selection_batch(
        selection_text=selection_text,
        provider="chatgpt_plus_manual",
        force=True,
    )


def import_story_narrative_with_dev_cache(
    *,
    batch_date: str,
    cache_key: str,
    narrative_text: str,
    dev_cache_enabled: bool,
) -> None:
    if dev_cache_enabled:
        save_chatgpt_response_cache_value(batch_date, cache_key, narrative_text)
    import_story_narrative_batch(
        narrative_text=narrative_text,
        provider="chatgpt_plus_manual",
        force=True,
    )


def run_daily_rundown_with_feedback(
    *,
    job_date: str,
    voice_profile_id: str,
    development_mode: bool = False,
    seed_rundown_dir: Path | None = None,
) -> None:
    events: list[dict[str, str]] = []
    with st.status("Construyendo programa diario...", expanded=True) as status:
        def on_progress(stage: str, details: str) -> None:
            events.append({"stage": stage, "details": details})
            status.write(f"**{stage}** · {details}")

        effective_seed_rundown_dir = seed_rundown_dir
        if not development_mode and effective_seed_rundown_dir is None:
            existing_rundowns = discover_rundown_dirs_for_date(job_date)
            if existing_rundowns:
                effective_seed_rundown_dir = existing_rundowns[0]

        try:
            manifest_path = build_daily_rundown_for_date(
                job_date=job_date,
                voice_profile_path=VOICE_PROFILES_DIR / f"{voice_profile_id}.json",
                subtitle_policy_path=DEFAULT_SUBTITLE_POLICY,
                video_template_path=DEFAULT_VIDEO_TEMPLATE,
                max_newspapers=2 if development_mode else None,
                seed_rundown_dir=effective_seed_rundown_dir,
                force=True,
                progress_callback=on_progress,
            )
        except Exception as exc:
            status.update(label="Programa diario detenido por error.", state="error", expanded=True)
            st.error(str(exc))
            if events:
                st.caption("Ultimas etapas completadas antes del error:")
                st.json(events[-8:])
            return

        status.update(label="Programa diario construido para preview.", state="complete", expanded=True)
        st.success(f"Manifest creado: `{rel(manifest_path)}`")
        st.caption("Abre Remotion y revisa `NewsVideo-generated`.")


def run_daily_rundown_retry_with_feedback(
    *,
    job_date: str,
    voice_profile_id: str,
    rundown_dir: Path,
) -> None:
    events: list[dict[str, str]] = []
    with st.status("Reintentando desde audios existentes...", expanded=True) as status:
        def on_progress(stage: str, details: str) -> None:
            events.append({"stage": stage, "details": details})
            status.write(f"**{stage}** · {details}")

        try:
            manifest_path = retry_daily_rundown_from_existing_audio(
                job_date=job_date,
                rundown_dir=rundown_dir,
                voice_profile_path=VOICE_PROFILES_DIR / f"{voice_profile_id}.json",
                subtitle_policy_path=DEFAULT_SUBTITLE_POLICY,
                video_template_path=DEFAULT_VIDEO_TEMPLATE,
                progress_callback=on_progress,
            )
        except Exception as exc:
            status.update(label="Reintento detenido por error.", state="error", expanded=True)
            st.error(str(exc))
            if events:
                st.caption("Ultimas etapas completadas antes del error:")
                st.json(events[-8:])
            return

        status.update(label="Programa diario reconstruido desde audios existentes.", state="complete", expanded=True)
        st.success(f"Manifest creado: `{rel(manifest_path)}`")
        st.caption("Abre Remotion y revisa `NewsVideo-generated`.")


def discover_rundown_dirs_for_date(job_date: str) -> list[Path]:
    rundown_root = PROJECT_DIR / "data" / "rundowns" / job_date
    if not rundown_root.exists():
        return []
    return sorted(
        [
            path
            for path in rundown_root.iterdir()
            if path.is_dir() and (path / "audio").exists() and list((path / "audio").glob("segment-*.wav"))
        ],
        reverse=True,
    )


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
        front_page_path = PROJECT_DIR / str(job.get("input_assets", {}).get("front_page_image"))
        dimensions = get_image_dimensions(front_page_path)
        lines.extend(
            [
                f"- portada {index}",
                f"  newspaper_name: {job.get('source_id', 'sin-source')}",
                f"  job_id: {job.get('job_id', 'sin-id')}",
                f"  date: {job.get('date', 'sin-fecha')}",
                f"  job_manifest_path: {rel(manifest_path)}",
                f"  cover_image_path: {job.get('input_assets', {}).get('front_page_image')}",
                f"  cover_dimensions: {dimensions[0]}x{dimensions[1]}" if dimensions else "  cover_dimensions: unknown",
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
        "rundown_intro": {
            "speech": "",
            "date_reference": "",
            "source_scope": "peru|world|none",
            "why_it_fits": "",
        },
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


def build_story_groups_from_candidates(candidates: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str, str], dict] = {}
    for candidate in candidates:
        headline = " ".join(str(candidate.get("headline") or "").split()).strip()
        if not headline:
            continue
        story_type = str(candidate.get("story_type") or "actualidad").strip() or "actualidad"
        cover_region = candidate.get("cover_region")
        region_key = json.dumps(cover_region, sort_keys=True, ensure_ascii=False) if cover_region else "null"
        key = (headline.casefold(), story_type, region_key)
        story = grouped.get(key)
        if story is None:
            story = {
                "headline": headline,
                "story_type": story_type,
                "cover_region": cover_region,
                "page_numbers": [],
                "evidence_lines": [],
                "confidence": 0.0,
            }
            grouped[key] = story

        page_number = int(candidate.get("page_number") or 0)
        if page_number > 1 and page_number not in story["page_numbers"]:
            story["page_numbers"].append(page_number)

        evidence_line = " ".join(str(candidate.get("evidence_line") or "").split()).strip()
        if evidence_line and evidence_line not in story["evidence_lines"]:
            story["evidence_lines"].append(evidence_line)

        try:
            confidence = float(candidate.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        story["confidence"] = round(max(float(story["confidence"]), confidence), 4)

    stories = list(grouped.values())
    stories.sort(
        key=lambda item: (
            min(item.get("page_numbers") or [999]),
            str(item.get("headline") or "").casefold(),
        )
    )
    return stories


def get_cover_stories(job: dict) -> list[dict]:
    page_selection = job.get("page_selection", {})
    stories = list(page_selection.get("stories", []))
    if stories:
        return stories
    return build_story_groups_from_candidates(list(page_selection.get("candidates", [])))


def get_story_narrative_entries(job: dict) -> list[dict]:
    story_narrative = job.get("story_narrative", {})
    return list(story_narrative.get("stories", []))


def story_matches_editorial_filters(
    story: dict,
    *,
    excluded_story_types: set[str],
    excluded_keywords: list[str],
    exclude_supplements: bool,
) -> bool:
    story_type = str(story.get("story_type") or "actualidad").strip().lower()
    if story_type in excluded_story_types:
        return False

    headline = str(story.get("headline") or "")
    evidence = str(story.get("evidence") or " ".join(story.get("evidence_lines", [])) or "")
    combined = f"{headline} {evidence}".casefold()

    if exclude_supplements:
        supplement_markers = ["luces", "dominical", "dt", "somos", "magazin", "magacín", "magacin"]
        if any(marker in combined for marker in supplement_markers):
            return False

    if excluded_keywords and any(keyword in combined for keyword in excluded_keywords):
        return False

    return True


def build_editorially_filtered_job(
    job: dict,
    *,
    excluded_story_types: set[str],
    excluded_keywords: list[str],
    exclude_supplements: bool,
) -> dict:
    filtered_job = copy.deepcopy(job)
    page_selection = dict(filtered_job.get("page_selection", {}))
    original_stories = get_cover_stories(job)
    filtered_stories = [
        story
        for story in original_stories
        if story_matches_editorial_filters(
            story,
            excluded_story_types=excluded_story_types,
            excluded_keywords=excluded_keywords,
            exclude_supplements=exclude_supplements,
        )
    ]

    allowed_pages = {
        int(page_number)
        for story in filtered_stories
        for page_number in story.get("page_numbers", [])
        if int(page_number) > 1
    }

    original_candidates = list(page_selection.get("candidates", []))
    filtered_candidates = [
        candidate
        for candidate in original_candidates
        if int(candidate.get("page_number") or 0) in allowed_pages
    ]

    page_selection["stories"] = filtered_stories
    page_selection["candidates"] = filtered_candidates
    page_selection["selected_page_numbers"] = sorted(allowed_pages)
    page_selection["editorial_filter"] = {
        "excluded_story_types": sorted(excluded_story_types),
        "excluded_keywords": excluded_keywords,
        "exclude_supplements": exclude_supplements,
    }
    filtered_job["page_selection"] = page_selection
    return filtered_job


def build_detailed_news_metadata(jobs: list[dict]) -> str:
    lines: list[str] = []
    index = 1
    for job in jobs:
        source_id = str(job.get("source_id", "sin-source"))
        job_id = str(job.get("job_id", "sin-id"))
        research_mode = "web_research_from_cover" if job_requires_web_research(job) else "internal_pages"
        headline_candidates = list(job.get("extraction", {}).get("headline_candidates", []))
        page_selection = job.get("page_selection", {})
        selection_notes = str(page_selection.get("notes") or "").strip()
        selected_candidates = list(page_selection.get("candidates", []))
        selected_stories = list(page_selection.get("stories", [])) or build_story_groups_from_candidates(selected_candidates)
        ocr_blocks = list(job.get("extraction", {}).get("ocr_blocks", []))
        pages = get_supporting_pages(job)
        if not pages and research_mode != "web_research_from_cover":
            continue
        lines.extend(
            [
                f"- diario {index}",
                f"  newspaper_name: {source_id}",
                f"  job_id: {job_id}",
                f"  source_research_mode: {research_mode}",
            ]
        )
        if research_mode == "web_research_from_cover":
            lines.append("  internal_pages_status: unavailable_for_source_use_web_research")
        if headline_candidates:
            lines.append("  headlines_detected:")
            for headline in headline_candidates[:5]:
                lines.append(f"  - {headline}")
        if selection_notes:
            lines.append(f"  selection_notes: {selection_notes}")
        if selected_stories:
            lines.append("  stories_detected_from_cover:")
            for story in selected_stories[:8]:
                lines.append(
                    "  - "
                    f"story_type: {story.get('story_type') or 'actualidad'} | "
                    f"page_numbers: {story.get('page_numbers') or []} | "
                    f"headline_hint: {story.get('headline') or ''} | "
                    f"evidence: {story.get('evidence') or ''} | "
                    f"cover_region: {story.get('cover_region') or ''}"
                )
        elif selected_candidates:
            lines.append("  page_hints_from_cover:")
            for candidate in selected_candidates[:8]:
                lines.append(
                    "  - "
                    f"story_type: {candidate.get('story_type') or 'actualidad'} | "
                    f"page_number: {int(candidate.get('page_number') or 0)} | "
                    f"headline_hint: {candidate.get('headline') or ''} | "
                    f"evidence_line: {candidate.get('evidence_line') or ''} | "
                    f"cover_region: {candidate.get('cover_region') or ''}"
                )
        if ocr_blocks:
            lines.append("  ocr_context:")
            for block in ocr_blocks[:5]:
                text = str(block.get("text") or "").strip()
                if text:
                    lines.append(f"  - {text}")
        if pages:
            lines.append("  supporting_pages:")
            for page in pages:
                lines.append(
                    f"  - page_number: {int(page.get('page_number') or 0)} | local_path: {page.get('local_path')}"
                )
        lines.append("")
        index += 1
    return "\n".join(lines).strip()


def build_detailed_news_prompt(jobs: list[dict]) -> str:
    metadata_text = build_detailed_news_metadata(jobs)
    narrator_map = load_story_type_narrator_map()
    story_type_lines = []
    for story_type, config in narrator_map.get("story_types", {}).items():
        narrator_id = str(config.get("narrator_profile_id") or "").strip()
        role = str(config.get("role") or "").strip()
        alternative_ids = [
            str(item).strip()
            for item in config.get("alternative_narrator_profile_ids", [])
            if str(item).strip()
        ] if isinstance(config.get("alternative_narrator_profile_ids"), list) else []
        if narrator_id:
            suffix = f" ({role})" if role else ""
            extra = f" | alternativas: {', '.join(f'`{item}`' for item in alternative_ids)}" if alternative_ids else ""
            story_type_lines.append(f"- `{story_type}` -> `{narrator_id}`{suffix}{extra}")
    voice_category_lines = []
    voice_categories = narrator_map.get("voice_categories", {})
    if isinstance(voice_categories, dict):
        for category, profile_ids in voice_categories.items():
            if not isinstance(profile_ids, list):
                continue
            normalized = [str(item).strip() for item in profile_ids if str(item).strip()]
            if normalized:
                voice_category_lines.append(
                    f"- `{category}`: " + ", ".join(f"`{item}`" for item in normalized)
                )
    presenter_ids = narrator_map.get("presenter_narrator_profile_ids", [])
    presenter_line = ""
    if isinstance(presenter_ids, list):
        normalized_presenters = [str(item).strip() for item in presenter_ids if str(item).strip()]
        if normalized_presenters:
            presenter_line = (
                "- Para intro, cambios de periodico y comentarios puente usa rotacion de voz en off entre: "
                + ", ".join(f"`{item}`" for item in normalized_presenters)
                + "."
            )
    page_backed_newspaper_count = 0
    research_only_newspaper_count = 0
    page_count = 0
    for job in jobs:
        pages = get_supporting_pages(job)
        if pages:
            page_backed_newspaper_count += 1
            page_count += len(pages)
        elif job_requires_web_research(job):
            research_only_newspaper_count += 1

    batch_context_line = (
        f"Este lote incluye {page_backed_newspaper_count} periodico(s) con {page_count} pagina(s) internas adjuntas "
        f"y {research_only_newspaper_count} periodico(s) sin acceso a paginas internas."
    )
    source_handling_lines = [
        "- Si `source_research_mode` es `internal_pages`, usa las paginas internas adjuntas como fuente principal de verificacion y ampliacion.",
        "- Si `source_research_mode` es `web_research_from_cover`, no hay paginas internas disponibles: investiga en la web solo las historias detectadas desde portada y devuelve el mismo contrato JSON.",
        "- Para investigacion web, usa fuentes periodisticas confiables y suficientemente claras para confirmar el hecho central de cada historia.",
        "- Si una historia de portada no se deja confirmar bien en la web, igual devuelvela con redaccion prudente y explica la limitacion en `safety_notes`.",
    ]

    lines = [
        batch_context_line,
        "Cuando existan imagenes adjuntas, cada grupo corresponde a un diario y a las paginas seleccionadas desde su portada.",
        "Estas paginas internas no se mostraran en el video final; se usan solo para entender mejor cada noticia de la portada.",
        "El resultado debe ser el speech final para narrar sobre la portada, listo para voz en off, subtitulos y audio.",
        "",
        "Contexto del proyecto de ChatGPT:",
        "- Este prompt debe pegarse en el proyecto de ChatGPT que ya tiene cargadas las fuentes derivadas de `proyect.md`.",
        "- Ese proyecto tambien debe usar las instrucciones de `instrucciones.md`.",
        "- Usa esas fuentes para asignar `narrator_profile_id` segun `story_type` y ajustar tono, ritmo, cautela y estilo.",
        "- No vuelvas a explicar las fuentes; aplicalas directamente.",
        "- Mapeo editorial actual `story_type -> narrator_profile_id`:",
        *(story_type_lines or ["- Usa el narrador por defecto si no hay mapa disponible."]),
        "- Cast real disponible hoy en Voicebox por categoria:",
        *(voice_category_lines or ["- No hay categorias de voz configuradas todavia."]),
        *( [presenter_line] if presenter_line else [] ),
        "",
        "Objetivo:",
        "Para cada periodico, toma las noticias ya detectadas desde portada, usa el mejor contexto disponible segun el modo de fuente, y devuelve un speech final por noticia.",
        "La lista `stories_detected_from_cover` funciona como contrato de entrada del lote: debes cubrir esas historias y no reemplazarlas por otras.",
        "",
        "Manejo por tipo de fuente:",
        *source_handling_lines,
        "",
        "Reglas:",
        "- No inventes hechos, nombres, cifras o citas.",
        "- Si una pagina no se lee bien, dilo brevemente en `safety_notes` y redacta solo con lo confiable.",
        "- Mantén separados los resultados por periodico.",
        "- Debes devolver una entrada en `stories` por cada historia listada en `stories_detected_from_cover` para ese periodico.",
        "- No omitas historias detectadas desde portada aunque una de ellas tenga menos contexto que otra.",
        "- No agregues historias nuevas que no esten en `stories_detected_from_cover`, salvo correccion evidente porque una referencia de portada en realidad era la misma historia ya listada.",
        "- Si un periodico trae cuatro historias detectadas desde portada, la salida de ese periodico tambien debe traer cuatro historias.",
        "- Escribe en espanol peruano neutro, claro y natural.",
        "- Cada `speech` debe tener 140 a 260 caracteres, idealmente 1 o 2 frases, con inicio fuerte y cierre claro.",
        "- El `speech` debe ajustarse a la categoria de noticia y al narrador asignado.",
        "- Prioriza brevedad y pegada: el video final debe sentirse agil, no recargado.",
        "- Evita contexto accesorio, repeticiones y cierres redundantes.",
        "- `key_facts_used` debe tener entre 1 y 3 puntos cortos, no parrafos.",
        "- Si una historia gana claridad con contexto numerico verificable, puedes agregar un `support_visual` opcional de tipo grafico.",
        "- Usa `support_visual` sobre todo en crecimiento, caidas, avances, encuestas, resultados, porcentajes, produccion, precios, inflacion, ranking, votos, goles, puntos o comparaciones temporales.",
        "- Si agregas `support_visual`, busca en la web datos numericos confiables y devuelve entre 2 y 6 puntos simples en `points`.",
        "- `support_visual.chart_type` debe ser `line`, `bar` o `area`.",
        "- Si no hay contexto numerico fuerte, omite `support_visual` o devuelvelo como `null`.",
        "- Usa `headline_hint` como base del `headline` final. Puedes limpiarlo o resumirlo levemente, pero no lo reemplaces por otra noticia distinta.",
        "- Respeta `story_type`, `headline` y `cover_region` ya detectados desde la portada; solo corrige si el contexto fuerte disponible muestra claramente que estaban mal.",
        "- Usa los titulares detectados, hints de portada y OCR previo como contexto fuerte.",
        "- Cuando existan paginas adjuntas, usalas como verificacion y ampliacion.",
        "- Cuando no existan paginas adjuntas y el diario este marcado para investigacion web, usa la web para verificar y ampliar sin salirte de las historias detectadas desde portada.",
        "- Aunque haya paginas internas, puedes complementar con la web si necesitas contexto numerico para un `support_visual`.",
        "- Si el contexto previo y las paginas adjuntas se contradicen, prioriza lo que se vea claramente en las paginas.",
        "- No conviertas una misma noticia en varias historias distintas solo porque ocupe varias paginas.",
        "- Si una historia de portada usa varias paginas, devuelve una sola entrada para esa historia, integrando el contexto de todas sus paginas.",
        "- Si una historia tiene poco contexto legible, igual devuelvela; resume solo lo verificable y explica la limitacion en `safety_notes`.",
        "- Antes de cerrar, verifica que cada `headline_hint` del contexto previo tenga una historia correspondiente en la salida.",
        "- Si aparece un tema fuerte en las paginas internas o en la investigacion web pero no estaba detectado desde portada, no lo promociones por encima de las historias ya listadas.",
        "- Devuelve solo JSON valido compatible con la salida esperada en `instrucciones.md`.",
        "",
        "Contexto previo disponible del lote:",
        "```text",
        metadata_text or "- No hay paginas internas descargadas todavia.",
        "```",
        "",
        "Devuelve solo JSON valido con esta estructura:",
        "```json",
        "{",
        '  "newspapers": [',
        "    {",
        '      "newspaper_name": "ojo",',
        '      "job_id": "2026-04-20-ojo-frontpage-001",',
        '      "stories": [',
        "        {",
        '          "headline": "Corvetto fuera de la ONPE por caos electoral",',
        '          "story_type": "politica",',
        '          "narrator_profile_id": "mavila_huertas",',
        '          "speech": "La salida de Corvetto deja una señal fuerte en plena resaca electoral. Si el caos ya golpeo la confianza en la ONPE, lo que viene exige explicaciones firmes y una reorganizacion sin margen para mas errores.",',
        '          "tone_notes": ["serio", "contextual", "prudente"],',
        '          "key_facts_used": ["salida de Corvetto", "caos electoral", "presion sobre la ONPE"],',
        '          "safety_notes": "Se evita afirmar delitos no probados.",',
        '          "support_visual": {',
        '            "type": "numeric_chart",',
        '            "chart_type": "bar",',
        '            "title": "Congresistas con mas votos",',
        '            "subtitle": "Referencia comparativa para reforzar la escala del resultado",',
        '            "unit": " mil",',
        '            "highlight_label": "Top votacion",',
        '            "data_source_note": "Datos de contexto numerico verificados en la web con fuentes periodisticas confiables.",',
        '            "points": [',
        '              {"label": "1°", "value": 145},',
        '              {"label": "2°", "value": 132},',
        '              {"label": "3°", "value": 118}',
        "            ]",
        "          }",
        "        },",
        "        {",
        '          "headline": "Mapa de puntos de robo en Lima",',
        '          "story_type": "policial",',
        '          "narrator_profile_id": "beto_ortiz",',
        '          "speech": "La inseguridad vuelve a marcar la agenda en Lima. El informe ubica zonas de robo reiterado y refuerza una idea simple: cuando el delito se vuelve rutina, la ausencia de control ya no se puede maquillar.",',
        '          "tone_notes": ["directo", "tenso", "cuidadoso"],',
        '          "key_facts_used": ["mapa de robos", "zonas de mayor riesgo", "alerta ciudadana"],',
        '          "safety_notes": "Se resume solo lo que se aprecia con claridad en la pagina.",',
        '          "support_visual": null',
        "        }",
        "      ]",
        "    }",
        "  ]",
        "}",
        "```",
        "",
        "Instruccion final:",
        "Analiza el contexto agrupado por periodico, usa paginas internas cuando existan o investigacion web cuando el diario lo requiera, y devuelve el JSON completo con speeches finales, sin explicacion adicional.",
    ]
    return "\n".join(lines)


def build_detailed_news_seed_payload(jobs: list[dict]) -> str:
    payload = {
        "newspapers": [],
    }
    for job in jobs:
        stories = []
        for story in get_cover_stories(job):
            stories.append(
                {
                    "headline": str(story.get("headline") or ""),
                    "story_type": str(story.get("story_type") or "actualidad"),
                    "narrator_profile_id": get_default_narrator_for_story_type(
                        str(story.get("story_type") or "actualidad")
                    ),
                    "speech": "",
                    "tone_notes": [],
                    "key_facts_used": [],
                    "safety_notes": "",
                    "support_visual": None,
                }
            )
        payload["newspapers"].append(
            {
                "newspaper_name": str(job.get("source_id") or "sin-source"),
                "job_id": str(job.get("job_id") or "sin-id"),
                "stories": stories,
            }
        )
    return json.dumps(payload, ensure_ascii=False, indent=2)


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


def group_requires_only_covers(jobs: list[dict]) -> bool:
    return bool(jobs) and all(job_requires_web_research(job) for job in jobs)


def group_requires_mixed_context(jobs: list[dict]) -> bool:
    return any(job_requires_web_research(job) for job in jobs) and any(
        get_supporting_pages(job) for job in jobs
    )


def get_group_context_button_label(jobs: list[dict], *, group_index: int) -> str:
    if group_requires_only_covers(jobs):
        return f"Abrir portadas bloque {group_index}"
    if group_requires_mixed_context(jobs):
        return f"Abrir contexto bloque {group_index}"
    return f"Abrir carpeta de paginas bloque {group_index}"


def build_context_bundle_dir_for_group(jobs: list[dict], *, group_index: int) -> Path:
    if group_requires_only_covers(jobs):
        review_dir = PROJECT_DIR / "data" / "review" / "cover-batches"
        review_dir.mkdir(parents=True, exist_ok=True)
        unique_dates = sorted({str(job.get("date") or "sin-fecha") for job in jobs})
        batch_name = unique_dates[0] if len(unique_dates) == 1 else "mixed-dates"
        target_dir = review_dir / f"{batch_name}-group-{group_index:02d}"
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
            file_name = f"{job.get('source_id', 'sin-source')}-cover{suffix}"
            shutil.copy2(source_path, target_dir / file_name)
        return target_dir

    if group_requires_mixed_context(jobs):
        review_dir = PROJECT_DIR / "data" / "review" / "context-batches"
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
            pages = get_supporting_pages(job)
            if pages:
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
            elif job_requires_web_research(job):
                image_value = job.get("input_assets", {}).get("front_page_image")
                if not image_value:
                    continue
                source_path = PROJECT_DIR / str(image_value)
                if not source_path.exists():
                    continue
                suffix = source_path.suffix or ".jpg"
                file_name = f"{source_id}-cover{suffix}"
                shutil.copy2(source_path, target_dir / file_name)
        return target_dir

    return build_pages_bundle_dir_for_group(jobs, group_index=group_index)


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

all_jobs = list_jobs()
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
                st.session_state["active_batch_date"] = batch_date.isoformat()
                st.success("Lote diario procesado.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    daily_batch_results = st.session_state.get("daily_job_batch_results")
    if daily_batch_results:
        render_daily_batch_results(daily_batch_results, selected_date=str(st.session_state.get("active_batch_date") or batch_date.isoformat()))
        with st.expander("Ver resultado del scraping", expanded=False):
            st.json(daily_batch_results)

all_jobs = list_jobs()
available_job_dates = sorted({str(job.get("date") or "") for job in all_jobs if job.get("date")}, reverse=True)
default_batch_date = get_default_batch_date(all_jobs)
if default_batch_date and default_batch_date not in available_job_dates:
    available_job_dates = [default_batch_date, *available_job_dates]
source_options = ["Todos"] + sorted({job.get("source_id", "sin-source") for job in all_jobs}) if all_jobs else ["Todos"]
status_options = ["Todos"] + sorted({job.get("status", "sin-status") for job in all_jobs}) if all_jobs else ["Todos"]

st.sidebar.header("Filtros")
selected_batch_date = st.sidebar.selectbox(
    "Fecha del lote",
    available_job_dates or [default_batch_date],
    index=(available_job_dates.index(default_batch_date) if default_batch_date in available_job_dates else 0),
)
st.session_state["active_batch_date"] = selected_batch_date
selected_source = st.sidebar.selectbox("Fuente", source_options)
selected_status = st.sidebar.selectbox("Estado", status_options)
text_query = st.sidebar.text_input("Buscar", placeholder="job id, titular o texto")

dev_mode_default = os.getenv("NEWS_VIDEO_DEV_MODE", "").strip().lower() in {"1", "true", "yes", "on"}
dev_mode_enabled = st.checkbox(
    "Modo desarrollo",
    value=bool(st.session_state.get("dev_mode_enabled", dev_mode_default)),
    help="Guarda y recupera respuestas pegadas de ChatGPT en data/dev-cache para no reescribirlas al reiniciar Streamlit.",
)
st.session_state["dev_mode_enabled"] = dev_mode_enabled
header_col1, header_col2 = st.columns([1, 2])
with header_col1:
    if st.button(
        "Cargar respuestas de prueba",
        use_container_width=True,
        help="Restaura en los campos de la UI las respuestas de ChatGPT guardadas para el lote activo.",
    ):
        restored_count = load_chatgpt_response_cache_into_session(selected_batch_date)
        if restored_count:
            st.success(f"Se cargaron {restored_count} respuesta(s) cacheadas para `{selected_batch_date}`.")
            st.rerun()
        else:
            st.info(f"No hay respuestas cacheadas para `{selected_batch_date}`.")
with header_col2:
    if dev_mode_enabled:
        st.caption(f"Cache dev activo: `{rel(get_chatgpt_response_cache_path(selected_batch_date))}`")
    else:
        st.caption("Activa modo desarrollo para guardar automaticamente las respuestas pegadas de ChatGPT.")

jobs_for_selected_date = filter_jobs_by_date(all_jobs, selected_date=selected_batch_date)
filtered_jobs = filter_jobs(
    jobs_for_selected_date,
    selected_source=selected_source,
    selected_status=selected_status,
    text_query=text_query,
)

if jobs_for_selected_date:
    render_dashboard(filtered_jobs)
else:
    st.info(
        f"No se encontraron jobs para `{selected_batch_date}`. Usa el bloque superior para crear o reintentar ese lote."
    )

board_tab, detail_tab = st.tabs(["Jobs", "Detalle"])

with board_tab:
    st.subheader("Portadas y Prompt")
    st.caption(f"Lote activo: `{selected_batch_date}`. Esta vista solo usa jobs de esa fecha.")
    batch_jobs = jobs_for_selected_date
    cover_jobs = [job for job in batch_jobs if job.get("input_assets", {}).get("front_page_image")]
    if not cover_jobs:
        st.info("El lote activo no tiene portadas disponibles para este flujo.")
    else:
        all_story_types = sorted(
            {
                str(story.get("story_type") or "actualidad")
                for job in cover_jobs
                for story in get_cover_stories(job)
            }
        )
        with st.expander("Filtro editorial del lote", expanded=False):
            editorial_col1, editorial_col2 = st.columns([1.2, 1.8])
            with editorial_col1:
                excluded_story_types = set(
                    st.multiselect(
                        "Excluir categorias",
                        all_story_types,
                        default=[],
                        key="editorial_excluded_story_types",
                    )
                )
                exclude_supplements = st.checkbox(
                    "Ocultar suplementos y anexos",
                    value=True,
                    key="editorial_exclude_supplements",
                )
            with editorial_col2:
                excluded_keywords_raw = st.text_input(
                    "Excluir historias si contienen estas palabras",
                    value="",
                    placeholder="luces, dominical, farandula",
                    key="editorial_excluded_keywords",
                )
                st.caption(
                    "Este filtro afecta las historias visibles, las paginas que se descargan y los prompts posteriores, "
                    "sin borrar el JSON original importado."
                )

        excluded_keywords = [
            keyword.strip().casefold()
            for keyword in excluded_keywords_raw.split(",")
            if keyword.strip()
        ]
        effective_cover_jobs = [
            build_editorially_filtered_job(
                job,
                excluded_story_types=excluded_story_types,
                excluded_keywords=excluded_keywords,
                exclude_supplements=exclude_supplements,
            )
            for job in cover_jobs
        ]
        metadata_text = build_cover_batch_metadata(cover_jobs)
        prompt_text = build_cover_batch_prompt(cover_jobs)
        seed_payload = build_cover_batch_seed_payload(cover_jobs)
        included_sources = ", ".join(str(job.get("source_id", "sin-source")) for job in cover_jobs)
        st.caption(
            f"Se detectaron {len(cover_jobs)} portadas descargadas en el lote activo. "
            "1. Scrapear periodicos. 2. Revisar portadas. 3. Copiar bloque de portadas. "
            "4. Copiar prompt. 5. Pegar el JSON devuelto por ChatGPT."
        )
        st.markdown(f"**Portadas incluidas en este prompt:** `{included_sources}`")

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
            "El prompt copiado se arma con todas las portadas descargadas del lote activo, sin depender de los filtros laterales."
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
            cover_import_key = "cover_batch_import_payload"
            batch_json_value = st.text_area(
                "Pega aqui el JSON devuelto por ChatGPT",
                value=get_chatgpt_response_cache_value(
                    selected_batch_date,
                    cover_import_key,
                    seed_payload,
                )
                if dev_mode_enabled
                else seed_payload,
                height=260,
                key=cover_import_key,
                on_change=cache_chatgpt_widget_value if dev_mode_enabled else None,
                args=(selected_batch_date, cover_import_key) if dev_mode_enabled else None,
            )
            if dev_mode_enabled:
                save_rendered_chatgpt_response(
                    selected_batch_date,
                    cover_import_key,
                    batch_json_value,
                    seed_payload,
                )
            if st.button("Importar Seleccion Batch", use_container_width=True, type="primary"):
                run_action(
                    "Seleccion batch importada.",
                    lambda batch_json_value=batch_json_value: import_cover_selection_with_dev_cache(
                        batch_date=selected_batch_date,
                        selection_text=batch_json_value,
                        dev_cache_enabled=dev_mode_enabled,
                    ),
                )

        selected_cover_jobs = []
        pending_cover_jobs = []
        unavailable_cover_jobs = []
        present_sources = {str(job.get("source_id") or "") for job in batch_jobs}
        editorial_filtered_story_count = 0
        editorial_kept_story_count = 0
        for original_job, job in zip(cover_jobs, effective_cover_jobs):
            original_story_count = len(get_cover_stories(original_job))
            filtered_story_count = len(get_cover_stories(job))
            editorial_filtered_story_count += max(0, original_story_count - filtered_story_count)
            editorial_kept_story_count += filtered_story_count
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

        st.caption(
            f"Filtro editorial activo sobre el lote visible: {editorial_kept_story_count} historia(s) util(es) y "
            f"{editorial_filtered_story_count} historia(s) ocultada(s)."
        )

        for job in batch_jobs:
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

        for source_id in available_source_ids:
            if source_id in present_sources:
                continue
            unavailable_cover_jobs.append(
                {
                    "newspaper_name": source_id,
                    "job_id": f"{selected_batch_date}-{source_id}-frontpage-001",
                    "reason": "no se creo job para esta fecha",
                }
            )

        if selected_cover_jobs or pending_cover_jobs or unavailable_cover_jobs:
            selected_cover_jobs_research_only = [
                item
                for item in selected_cover_jobs
                if job_requires_web_research(
                    next(
                        (
                            job
                            for job in effective_cover_jobs
                            if job.get("job_id") == item["job_id"] and job.get("source_id") == item["newspaper_name"]
                        ),
                        {},
                    )
                )
            ]
            selected_cover_jobs_downloadable = [
                item for item in selected_cover_jobs if item not in selected_cover_jobs_research_only
            ]
            st.caption(
                f"{len(selected_cover_jobs_downloadable)} periodico(s) listos para descargar, "
                f"{len(selected_cover_jobs_research_only)} periodico(s) listos para investigacion web y "
                f"{len(pending_cover_jobs)} pendiente(s) de seleccion en el lote. "
                f"{len(unavailable_cover_jobs)} sin portada disponible."
            )
            with st.expander("Estado del lote por periodico", expanded=True):
                if selected_cover_jobs:
                    for item in selected_cover_jobs:
                        page_numbers = ", ".join(str(page) for page in item["selected_page_numbers"])
                        matching_job = next(
                            (
                                job
                                for job in effective_cover_jobs
                                if job.get("job_id") == item["job_id"] and job.get("source_id") == item["newspaper_name"]
                            ),
                            None,
                        )
                        if matching_job is not None and job_requires_web_research(matching_job):
                            body = (
                                "Listo para prompt de investigacion web. "
                                f"Referencias de portada detectadas hacia paginas: {page_numbers}"
                            )
                            tone = "ready"
                        else:
                            body = f"Listo para descargar. Paginas seleccionadas: {page_numbers}"
                            tone = "ready"
                        render_status_card(
                            title=f"{item['newspaper_name']} · {item['job_id']}",
                            body=body,
                            tone=tone,
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
                "Si esta opcion esta activa, el lote usara las paginas ya descargadas cuando coincidan con las seleccionadas. "
                "Para `Libero` y `La Republica`, en vez de descargar paginas internas se preparara un prompt de investigacion web."
            )
            if st.button("Preparar contexto del lote", use_container_width=True, type="primary"):
                progress_placeholder = st.empty()
                status_placeholder = st.empty()
                progress_bar = progress_placeholder.progress(0, text="Preparando contexto del lote...")
                status_placeholder.info("Iniciando preparacion de paginas e investigacion web por fuente...")
                try:
                    total_jobs = len(selected_cover_jobs)
                    results = []
                    for index, item in enumerate(selected_cover_jobs, start=1):
                        matching_job = next(
                            (
                                job
                                for job in effective_cover_jobs
                                if job.get("job_id") == item["job_id"] and job.get("source_id") == item["newspaper_name"]
                            ),
                            None,
                        )
                        if matching_job is None:
                            continue
                        if job_requires_web_research(matching_job):
                            status_placeholder.info(
                                f"Preparando investigacion web para {item['newspaper_name']} segun historias detectadas en portada"
                            )
                        else:
                            status_placeholder.info(
                                f"Descargando {item['newspaper_name']} · paginas {', '.join(str(page) for page in item['selected_page_numbers'])}"
                            )
                        results.extend(
                            download_selected_pages_batch(
                                jobs=[matching_job],
                                force=not reuse_existing_pages,
                                selected_page_numbers_override={
                                    str(matching_job.get("job_id") or ""): list(item["selected_page_numbers"])
                                },
                            )
                        )
                        progress_bar.progress(
                            int((index / total_jobs) * 100),
                            text=f"Preparando lote... {index}/{total_jobs}",
                        )
                    st.session_state["selected_pages_batch_results"] = results
                    progress_bar.progress(100, text="Contexto del lote completado.")
                    status_placeholder.success("Contexto del lote preparado para construir el prompt.")
                    st.rerun()
                except Exception as exc:
                    status_placeholder.error(str(exc))
            selected_pages_batch_results = st.session_state.get("selected_pages_batch_results")
            if selected_pages_batch_results:
                context_ready_jobs_for_prompt = []
                for item in selected_pages_batch_results:
                    matching_job = next(
                            (
                                job
                                for job in list_jobs()
                                if job.get("job_id") == item.get("job_id") and job.get("source_id") == item.get("source_id")
                            ),
                        None,
                    )
                    if matching_job is not None:
                        context_ready_jobs_for_prompt.append(
                            build_editorially_filtered_job(
                                matching_job,
                                excluded_story_types=excluded_story_types,
                                excluded_keywords=excluded_keywords,
                                exclude_supplements=exclude_supplements,
                            )
                        )

                with st.expander("Ver resultado de descarga de paginas", expanded=True):
                    for item in selected_pages_batch_results:
                        downloaded = ", ".join(str(page) for page in item.get("downloaded_page_numbers", [])) or "ninguna"
                        status_value = str(item.get("status") or "")
                        tone = "downloaded" if status_value in {"downloaded", "refreshed"} else "neutral"
                        if status_value == "reused":
                            action_label = "Paginas reutilizadas"
                        elif status_value == "refreshed":
                            action_label = "Paginas actualizadas"
                        elif status_value == "web_research_required":
                            action_label = "Investigacion web requerida"
                        else:
                            action_label = "Paginas descargadas"
                        if status_value == "web_research_required":
                            body = (
                                "Sin descarga interna. Este periodico usara investigacion web a partir de las "
                                "historias detectadas en portada."
                            )
                        else:
                            body = f"{action_label}: {downloaded}"
                        render_status_card(
                            title=f"{item.get('source_id', 'sin-source')} · {item.get('job_id', 'sin-id')}",
                            body=body,
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
                            if status_value == "web_research_required":
                                st.caption(
                                    "Este periodico no tiene paginas internas descargables. El prompt pedira investigacion web."
                                )
                            else:
                                st.caption("No se registraron paginas descargadas para este periodico.")

                if context_ready_jobs_for_prompt:
                    grouped_jobs = chunk_jobs(context_ready_jobs_for_prompt, size=2)
                    st.subheader("Speeches por Bloques de 2 Periodicos")
                    st.caption(
                        "Se generaron prompts separados, con maximo 2 periodicos por bloque, para ajustarse mejor "
                        "al limite de imagenes de ChatGPT y mezclar, cuando haga falta, paginas internas con investigacion web."
                    )
                    for group_index, group_jobs in enumerate(grouped_jobs, start=1):
                        detailed_prompt = build_detailed_news_prompt(group_jobs)
                        detailed_metadata = build_detailed_news_metadata(group_jobs)
                        detailed_seed_payload = build_detailed_news_seed_payload(group_jobs)
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
                                context_button_label = get_group_context_button_label(
                                    group_jobs,
                                    group_index=group_index,
                                )
                                if st.button(
                                    context_button_label,
                                    use_container_width=True,
                                    key=f"open_pages_group_{group_index}",
                                ):
                                    run_action(
                                        f"Contexto visual del bloque {group_index} abierto.",
                                        lambda group_jobs=group_jobs, group_index=group_index: open_local_path(
                                            build_context_bundle_dir_for_group(group_jobs, group_index=group_index)
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
                                f"Prompt de speeches bloque {group_index}",
                                value=detailed_prompt,
                                height=360,
                                key=f"detailed_news_prompt_{group_index}",
                            )
                            detailed_import_key = f"detailed_news_import_payload_{group_index}"
                            narrative_batch_value = st.text_area(
                                f"JSON editorial bloque {group_index}",
                                value=get_chatgpt_response_cache_value(
                                    selected_batch_date,
                                    detailed_import_key,
                                    detailed_seed_payload,
                                )
                                if dev_mode_enabled
                                else detailed_seed_payload,
                                height=260,
                                key=detailed_import_key,
                                on_change=cache_chatgpt_widget_value if dev_mode_enabled else None,
                                args=(
                                    selected_batch_date,
                                    detailed_import_key,
                                )
                                if dev_mode_enabled
                                else None,
                            )
                            if dev_mode_enabled:
                                save_rendered_chatgpt_response(
                                    selected_batch_date,
                                    detailed_import_key,
                                    narrative_batch_value,
                                    detailed_seed_payload,
                                )
                            if st.button(
                                f"Importar Speeches Editoriales bloque {group_index}",
                                use_container_width=True,
                                type="primary",
                                key=f"import_detailed_news_payload_{group_index}",
                            ):
                                run_action(
                                    f"Speeches editoriales del bloque {group_index} importados.",
                                    lambda narrative_batch_value=narrative_batch_value, detailed_import_key=detailed_import_key: import_story_narrative_with_dev_cache(
                                        batch_date=selected_batch_date,
                                        cache_key=detailed_import_key,
                                        narrative_text=narrative_batch_value,
                                        dev_cache_enabled=dev_mode_enabled,
                                    ),
                                )

                st.subheader("Programa Diario")
                ready_rundown_jobs = [
                    job
                    for job in batch_jobs
                    if job.get("story_narrative", {}).get("stories")
                    and job.get("input_assets", {}).get("front_page_image")
                ]
                st.caption(
                    "Cuando los bloques de speeches ya estan importados, esto arma una sola secuencia: "
                    "intro de presentador, periodicos en orden y temas con narrador asignado."
                )
                st.markdown(
                    f"Jobs listos para programa: `{len(ready_rundown_jobs)}` de `{len(batch_jobs)}`."
                )
                rundown_dev_mode = st.checkbox(
                    "Modo desarrollo para preview",
                    value=False,
                    help="Genera audio solo para el primer bloque de 2 periodicos listos del lote y aun asi actualiza Remotion para iterar mas rapido.",
                    key="rundown_dev_mode",
                )
                if rundown_dev_mode:
                    preview_sources = ", ".join(
                        str(job.get("source_id") or "sin-source") for job in ready_rundown_jobs[:2]
                    )
                    st.caption(
                        f"Preview rapido activo: se construira intro + primer bloque listo (`{preview_sources}`)."
                    )
                if ready_rundown_jobs:
                    rundown_preview_rows = []
                    for rundown_job in ready_rundown_jobs:
                        stories = [
                            story
                            for story in rundown_job.get("story_narrative", {}).get("stories", [])
                            if str(story.get("speech") or story.get("summary") or "").strip()
                        ]
                        narrator_ids = sorted(
                            {
                                str(story.get("narrator_profile_id") or "sin-narrador")
                                for story in stories
                            }
                        )
                        rundown_preview_rows.append(
                            {
                                "periodico": rundown_job.get("source_id") or "sin-source",
                                "historias": len(stories),
                                "narradores": ", ".join(narrator_ids),
                                "portada": "ok" if rundown_job.get("input_assets", {}).get("front_page_image") else "falta",
                            }
                        )
                    st.dataframe(rundown_preview_rows, use_container_width=True, hide_index=True)
                    with st.expander("Ajuste Manual de Enfoque del Lote", expanded=False):
                        batch_focus_options = {
                            f"{job.get('source_id') or 'sin-source'} · {job.get('job_id') or 'sin-id'}": job
                            for job in ready_rundown_jobs
                        }
                        selected_focus_job_label = st.selectbox(
                            "Periodico a corregir",
                            list(batch_focus_options.keys()),
                            key="batch_focus_job_selector",
                        )
                        selected_focus_job = batch_focus_options[selected_focus_job_label]
                        selected_focus_job_path = selected_focus_job.get("_path")
                        if isinstance(selected_focus_job_path, Path):
                            render_focus_editor_for_job(
                                job=selected_focus_job,
                                job_path=selected_focus_job_path,
                                ui_prefix=f"batch_focus_{selected_focus_job.get('job_id')}",
                            )
                        else:
                            st.caption("No se encontro la ruta del job para editar el enfoque.")
                available_seed_rundowns = discover_rundown_dirs_for_date(selected_batch_date)
                suggested_seed_rundown = available_seed_rundowns[0] if available_seed_rundowns else None
                reuse_preview_audio = False
                selected_seed_rundown = None
                if not rundown_dev_mode and suggested_seed_rundown is not None:
                    reuse_preview_audio = st.checkbox(
                        "Reutilizar audios ya generados del preview si coinciden",
                        value=True,
                        help="Si la intro y el primer bloque son iguales a una corrida previa, copia esos WAV y solo genera el resto.",
                        key="reuse_preview_audio_for_full_rundown",
                    )
                    if reuse_preview_audio:
                        selected_seed_rundown = st.selectbox(
                            "Corrida base para reutilizar audio",
                            available_seed_rundowns,
                            index=0,
                            format_func=lambda path: (
                                f"{path.name} · {len(list((path / 'audio').glob('segment-*.wav')))} audios"
                            ),
                            key="seed_rundown_dir_for_full_build",
                        )
                        st.caption(
                            f"Si los primeros segmentos no cambiaron, se copiaran desde `{rel(selected_seed_rundown)}`."
                        )
                if st.button(
                    "Construir Programa Diario para Preview",
                    use_container_width=True,
                    type="primary",
                    disabled=not ready_rundown_jobs,
                ):
                    run_daily_rundown_with_feedback(
                        job_date=selected_batch_date,
                        voice_profile_id=batch_voice_profile,
                        development_mode=rundown_dev_mode,
                        seed_rundown_dir=selected_seed_rundown if reuse_preview_audio else None,
                    )

                retry_rundown_dirs = available_seed_rundowns
                if retry_rundown_dirs:
                    retry_options = {
                        f"{path.name} · {len(list((path / 'audio').glob('segment-*.wav')))} audios": path
                        for path in retry_rundown_dirs
                    }
                    retry_label = st.selectbox(
                        "Corrida para reintentar desde audios existentes",
                        list(retry_options.keys()),
                        key="retry_daily_rundown_dir",
                    )
                    if st.button(
                        "Reintentar desde audios existentes",
                        use_container_width=True,
                        disabled=not ready_rundown_jobs,
                    ):
                        run_daily_rundown_retry_with_feedback(
                            job_date=selected_batch_date,
                            voice_profile_id=batch_voice_profile,
                            rundown_dir=retry_options[retry_label],
                        )
                else:
                    st.caption("Todavia no hay corridas con audios existentes para reintentar.")

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
    story_narrative = job.get("story_narrative", {})

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
            st.subheader("Narrativa Editorial")
            st.markdown(f"Provider: `{story_narrative.get('provider') or 'pendiente'}`")
            st.markdown(f"Status: `{story_narrative.get('status') or 'not_started'}`")
            story_narrative_entries = get_story_narrative_entries(job)
            st.markdown(f"Historias: `{len(story_narrative_entries)}`")
            if story_narrative.get("notes"):
                st.caption(story_narrative.get("notes"))
            with st.expander("Historias narrativas registradas", expanded=False):
                if story_narrative_entries:
                    st.json(story_narrative_entries)
                else:
                    st.caption("Sin historias editoriales importadas.")

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

        st.subheader("Ajuste Manual de Enfoque")
        render_focus_editor_for_job(
            job=job,
            job_path=job_path,
            ui_prefix=f"detail_focus_{job.get('job_id')}",
        )
        st.caption(
            "Para validar visualmente la caja sobre el video final, abre en Remotion la composicion `NewsVideo-generated-debug`."
        )

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

        with st.expander("Narrativa Editorial", expanded=False):
            cover_stories = get_cover_stories(job)
            story_narrative_default = json.dumps(
                {
                    "stories": [
                        {
                            "headline": story.get("headline") or "",
                            "story_type": story.get("story_type") or "actualidad",
                            "narrator_profile_id": get_default_narrator_for_story_type(
                                str(story.get("story_type") or "actualidad")
                            ),
                            "speech": "",
                            "tone_notes": [],
                            "key_facts_used": [],
                            "safety_notes": "",
                            "support_visual": None,
                        }
                        for story in cover_stories
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            story_narrative_value = st.text_area(
                "JSON editorial por historia",
                value=story_narrative_default,
                height=260,
                key=f"manual_story_narrative_{job.get('job_id')}",
            )
            if st.button("Importar Narrativa Editorial", use_container_width=True, type="primary"):
                run_action(
                    "Narrativa editorial importada.",
                    lambda: import_story_narrative_for_job(
                        job_manifest_path=job_path,
                        narrative_text=story_narrative_value,
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
