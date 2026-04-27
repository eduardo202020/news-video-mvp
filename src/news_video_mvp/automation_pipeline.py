from __future__ import annotations

from datetime import datetime
import inspect
import json
from pathlib import Path
import re
import shutil
import wave

from .automation_models import SourceConfig, VideoTemplate, VoiceProfile, read_json, write_json
from .composer import VideoSegment, VideoSpec, compose_video_props, concatenate_wav_files
from .ocr import PaddleOCRError, extract_text_with_paddleocr
from .project import get_project_dir
from .scraping import (
    archive_all_sources,
    archive_source_scrape,
    build_input_assets,
    build_source_url,
    discover_source_assets,
    ingest_supporting_pages,
    probe_prcdn_page_count,
    prune_source_storage,
    resolve_publication_date,
    resolve_prcdn_pages,
    resolve_source_storage_dir,
    stage_front_page_asset,
    stage_supporting_page_asset,
)
from .script_generation import import_generated_script, prepare_chatgpt_script_package
from .subtitles import build_subtitle_segments
from .voice_generation import generate_voice_track, list_voicebox_profiles, transcribe_with_voicebox


NARRATOR_PROFILE_TO_VOICE_PROFILE = {
    "rene_gastelumendi": "rene_gastelumendi",
    "mavila_huertas": "mavila_huertas",
    "beto_ortiz": "beto_ortiz",
    "magaly_medina": "magaly_medina",
    "rodrigo_gonzalez": "rodrigo_gonzalez",
    "gonzalo_nunez": "gonzalo_nunez",
    "eddie_fleischman": "eddie_fleischman",
    "julio_velarde": "julio_velarde",
}
DEFAULT_STORY_TYPE_NARRATOR_MAP_PATH = Path("automation/templates/narrators/story-type-map.json")


def get_automation_dir(project_dir: Path | None = None) -> Path:
    return (project_dir or get_project_dir()) / "automation"


def get_story_type_narrator_map_path(project_dir: Path | None = None) -> Path:
    return (project_dir or get_project_dir()) / DEFAULT_STORY_TYPE_NARRATOR_MAP_PATH


def _slug_identifier(value: object) -> str:
    replacements = str.maketrans(
        {
            "á": "a",
            "é": "e",
            "í": "i",
            "ó": "o",
            "ú": "u",
            "Á": "a",
            "É": "e",
            "Í": "i",
            "Ó": "o",
            "Ú": "u",
            "ñ": "n",
            "Ñ": "n",
        }
    )
    slug = str(value or "").translate(replacements).strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug).strip("_")
    return slug


def _load_story_type_narrator_map(*, project_dir: Path) -> dict[str, object]:
    mapping_path = get_story_type_narrator_map_path(project_dir)
    if not mapping_path.exists():
        return {
            "map_id": "missing-story-type-map",
            "default_narrator_profile_id": "rene_gastelumendi",
            "presenter_narrator_profile_id": "mavila_huertas",
            "story_types": {},
        }
    payload = read_json(mapping_path)
    if not isinstance(payload.get("story_types"), dict):
        payload["story_types"] = {}
    return payload


def _resolve_story_narrator_config(
    *,
    story_type: object,
    narrator_profile_id: object = None,
    project_dir: Path,
) -> dict[str, object]:
    mapping = _load_story_type_narrator_map(project_dir=project_dir)
    normalized_story_type = _normalize_story_type(story_type)
    story_types = mapping.get("story_types", {})
    configured = story_types.get(normalized_story_type, {}) if isinstance(story_types, dict) else {}
    configured_narrator = str(configured.get("narrator_profile_id") or "").strip()
    resolved_narrator = (
        _slug_identifier(narrator_profile_id)
        if str(narrator_profile_id or "").strip()
        else _slug_identifier(
            configured_narrator or mapping.get("default_narrator_profile_id") or "rene_gastelumendi"
        )
    )
    tone_notes = _normalize_key_facts(configured.get("tone_notes"))
    return {
        "map_id": str(mapping.get("map_id") or "default-story-type-narrators"),
        "story_type": normalized_story_type,
        "narrator_profile_id": resolved_narrator or "rene_gastelumendi",
        "role": str(configured.get("role") or "reportero_general"),
        "tone_notes": tone_notes,
    }


def _get_presenter_narrator_profile_id(*, project_dir: Path) -> str:
    mapping = _load_story_type_narrator_map(project_dir=project_dir)
    return _slug_identifier(mapping.get("presenter_narrator_profile_id") or "mavila_huertas")


def _resolve_voice_profile_for_narrator(
    *,
    narrator_profile_id: object,
    fallback_voice_profile_path: Path,
    project_dir: Path,
) -> VoiceProfile:
    narrator_slug = _slug_identifier(narrator_profile_id)
    profile_id = NARRATOR_PROFILE_TO_VOICE_PROFILE.get(narrator_slug)
    if not profile_id:
        return VoiceProfile.load(fallback_voice_profile_path)
    candidate = project_dir / "automation" / "templates" / "voices" / f"{profile_id}.json"
    if not candidate.exists():
        return VoiceProfile.load(fallback_voice_profile_path)
    return VoiceProfile.load(candidate)


def _resolve_tts_profile_for_narrator(
    *,
    narrator_profile_id: object,
    fallback_voice_profile_path: Path,
    project_dir: Path,
) -> VoiceProfile:
    return _resolve_voice_profile_for_narrator(
        narrator_profile_id=narrator_profile_id,
        fallback_voice_profile_path=fallback_voice_profile_path,
        project_dir=project_dir,
    )


def get_jobs_root(project_dir: Path | None = None) -> Path:
    return (project_dir or get_project_dir()) / "data" / "jobs"


SOURCE_RUNDOWN_ORDER = ["correo", "elcomercio", "gestion", "ojo", "trome", "libero"]


def build_job_id(*, job_date: str, source_id: str, suffix: str = "frontpage-001") -> str:
    return f"{job_date}-{source_id}-{suffix}"


def ensure_job_scaffold(job_dir: Path) -> None:
    for name in ("input", "work", "output", "review"):
        (job_dir / name).mkdir(parents=True, exist_ok=True)


def _build_source_state(
    *,
    source: SourceConfig,
    requested_date: str,
    issue_date: str | None,
    publication_status: str,
    discovery_type: str | None = None,
    front_page_url: str | None = None,
    discovered_pages_count: int = 0,
    summary_path: str | None = None,
    probe_path: str | None = None,
) -> dict[str, object]:
    return {
        "source_id": source.source_id,
        "source_config_path": source.path.resolve().relative_to(get_project_dir()).as_posix(),
        "requested_date": requested_date,
        "issue_date": issue_date,
        "publication_status": publication_status,
        "discovery_type": discovery_type,
        "front_page_url": front_page_url,
        "discovered_pages_count": discovered_pages_count,
        "archive_summary_path": summary_path,
        "page_count_probe_path": probe_path,
    }


def _default_page_selection() -> dict[str, object]:
    return {
        "strategy": "cover_first",
        "provider": None,
        "status": "not_started",
        "selected_page_numbers": [],
        "candidates": [],
        "stories": [],
        "notes": "",
    }


def _default_story_narrative() -> dict[str, object]:
    return {
        "provider": None,
        "status": "not_started",
        "source": "supporting_pages_manual",
        "stories": [],
        "manifest_path": None,
        "notes": "",
    }


def _resolve_source_artifact_paths(
    *,
    source: SourceConfig,
    requested_date: str,
    project_dir: Path,
) -> dict[str, str | None]:
    storage_dir = resolve_source_storage_dir(
        source=source,
        job_date=requested_date,
        project_dir=project_dir,
    )
    probe_path = storage_dir / "page-count-probe.json"
    summary_path = project_dir / "data" / "raw" / "archive-summary" / f"{requested_date}.json"
    return {
        "probe_path": probe_path.resolve().relative_to(project_dir).as_posix()
        if probe_path.exists()
        else None,
        "summary_path": summary_path.resolve().relative_to(project_dir).as_posix()
        if summary_path.exists()
        else None,
    }


def create_job_manifest(
    *,
    source_config_path: Path,
    job_date: str,
    approval_mode: str,
    voice_profile_path: Path,
    video_template_path: Path,
    script_template_id: str,
    publish_profile_id: str,
    subtitle_policy_id: str,
    front_page_image: Path | None = None,
    front_page_url: str | None = None,
    download_front_page: bool = False,
    supporting_page_urls: list[str] | None = None,
    supporting_page_images: list[Path] | None = None,
    job_id: str | None = None,
) -> Path:
    project_dir = get_project_dir()
    source = SourceConfig.load(source_config_path)
    voice = VoiceProfile.load(voice_profile_path)
    video_template = VideoTemplate.load(video_template_path)
    resolved_job_id = job_id or build_job_id(job_date=job_date, source_id=source.source_id)
    job_dir = get_jobs_root(project_dir) / job_date / resolved_job_id
    ensure_job_scaffold(job_dir)
    artifact_paths = _resolve_source_artifact_paths(
        source=source,
        requested_date=job_date,
        project_dir=project_dir,
    )

    issue_date = resolve_publication_date(source=source, job_date=job_date)
    publication_status = "available" if issue_date is not None else "no_publication_for_date"
    resolved_front_page_url = front_page_url or (
        build_source_url(source, job_date=job_date) if issue_date is not None else None
    )
    staged_front_page = stage_front_page_asset(
        job_dir=job_dir,
        front_page_image=front_page_image,
        front_page_url=resolved_front_page_url,
        download_front_page=download_front_page,
    )
    supporting_pages: list[dict[str, str | int | None]] = []

    timestamp = datetime.now().isoformat(timespec="seconds")
    manifest = {
        "job_id": resolved_job_id,
        "source_id": source.source_id,
        "date": job_date,
        "source": _build_source_state(
            source=source,
            requested_date=job_date,
            issue_date=issue_date,
            publication_status=publication_status,
            front_page_url=resolved_front_page_url,
            summary_path=artifact_paths["summary_path"],
            probe_path=artifact_paths["probe_path"],
        ),
        "approval_mode": approval_mode,
        "status": (
            "scraped"
            if staged_front_page
            else "skipped_no_publication"
            if publication_status == "no_publication_for_date"
            else "discovered"
        ),
        "input_assets": build_input_assets(
            project_dir=project_dir,
            source_config_path=source_config_path,
            source_url=resolved_front_page_url or source.base_url,
            front_page_url=resolved_front_page_url,
            front_page_asset=staged_front_page,
            supporting_pages=supporting_pages,
        ),
        "extraction": {
            "ocr_blocks": [],
            "headline_candidates": [],
            "ad_blocks": [],
            "confidence": 0.0,
        },
        "classification": {
            "is_news": None,
            "priority": None,
            "reason": None,
        },
        "page_selection": _default_page_selection(),
        "story_narrative": _default_story_narrative(),
        "script": {
            "template_id": script_template_id,
            "provider": "manual_or_external_ai",
            "model": None,
            "draft": "",
            "approved_text": "",
            "review_notes": "",
        },
        "voice": {
            "profile_id": voice.profile_id,
            "provider": voice.tts_provider,
            "tts_voice": voice.tts_voice,
            "external_provider": None,
            "audio_path": None,
            "timestamps_path": None,
        },
        "subtitles": {
            "policy_id": subtitle_policy_id,
            "segments_path": None,
        },
        "transcription": {
            "provider": None,
            "text": "",
            "duration_seconds": None,
            "source_audio_path": None,
            "output_path": None,
        },
        "video": {
            "template_id": video_template.template_id,
            "story_manifest_path": None,
            "output_path": None,
        },
        "publication": {
            "profile_id": publish_profile_id,
            "status": "not_started",
            "post_url": None,
            "platform_post_id": None,
        },
        "audit": {
            "created_at": timestamp,
            "updated_at": timestamp,
            "events": [
                {
                    "stage": "discover",
                    "status": "skipped" if publication_status == "no_publication_for_date" else "completed",
                    "timestamp": timestamp,
                    "details": (
                        "Job creado sin edicion publicada para la fecha solicitada."
                        if publication_status == "no_publication_for_date"
                        else "Job creado desde source config declarativo."
                    ),
                }
            ],
        },
    }
    manifest_path = write_json(job_dir / "job-manifest.json", manifest)
    if supporting_page_urls or supporting_page_images:
        return ingest_supporting_pages(
            job_manifest_path=manifest_path,
            page_urls=supporting_page_urls,
            page_images=supporting_page_images,
        )
    return manifest_path


def scrape_pages_for_job(
    *,
    job_manifest_path: Path,
    page_urls: list[str] | None = None,
    page_images: list[Path] | None = None,
) -> Path:
    return ingest_supporting_pages(
        job_manifest_path=job_manifest_path,
        page_urls=page_urls,
        page_images=page_images,
    )


def discover_source_for_date(
    *,
    source_config_path: Path,
    job_date: str,
    source_url: str | None = None,
    max_supporting_pages: int = 3,
) -> dict[str, object]:
    source = SourceConfig.load(source_config_path)
    return discover_source_assets(
        source=source,
        job_date=job_date,
        source_url=source_url,
        max_supporting_pages=max_supporting_pages,
    )


def probe_source_page_count_for_date(
    *,
    source_config_path: Path,
    job_date: str,
    max_probe_pages: int | None = None,
) -> dict[str, object]:
    project_dir = get_project_dir()
    source = SourceConfig.load(source_config_path)
    if str(source.discovery.get("type", "")).strip() != "prcdn_image_sequence":
        raise ValueError(
            "El conteo de paginas automatico solo esta soportado por ahora para fuentes `prcdn_image_sequence`."
        )

    probe = probe_prcdn_page_count(
        source=source,
        job_date=job_date,
        max_probe_pages=max_probe_pages,
    )
    storage_dir = resolve_source_storage_dir(source=source, job_date=job_date, project_dir=project_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)
    probe_path = storage_dir / "page-count-probe.json"
    payload = {
        **probe,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    }
    write_json(probe_path, payload)

    scrape_manifest_path = storage_dir / "scrape-manifest.json"
    if scrape_manifest_path.exists():
        scrape_manifest = read_json(scrape_manifest_path)
        scrape_manifest["page_count_probe"] = {
            "page_count": probe["page_count"],
            "first_page": probe["first_page"],
            "last_page": probe["last_page"],
            "max_probe_pages": probe["max_probe_pages"],
            "probe_path": probe_path.resolve().relative_to(project_dir).as_posix(),
        }
        write_json(scrape_manifest_path, scrape_manifest)

    return {
        **payload,
        "probe_path": probe_path.resolve().relative_to(project_dir).as_posix(),
    }


def scrape_source_into_job(
    *,
    job_manifest_path: Path,
    source_config_path: Path,
    source_url: str | None = None,
    max_supporting_pages: int = 3,
    force: bool = False,
) -> Path:
    project_dir = get_project_dir()
    job = read_json(job_manifest_path)
    source = SourceConfig.load(source_config_path)
    artifact_paths = _resolve_source_artifact_paths(
        source=source,
        requested_date=str(job.get("date")),
        project_dir=project_dir,
    )
    current_front_page = job.get("input_assets", {}).get("front_page_image")
    current_pages = job.get("input_assets", {}).get("pages", [])
    if (current_front_page or current_pages) and not force:
        raise ValueError(
            "El job ya tiene assets de entrada. Usa `--force` si quieres re-scrapear la fuente."
        )

    discovery = discover_source_assets(
        source=source,
        job_date=str(job.get("date")),
        source_url=source_url,
        max_supporting_pages=max_supporting_pages,
    )
    discovered_pages = list(discovery.get("pages", []))
    issue_date = discovery.get("issue_date")
    discovery_type = str(discovery.get("discovery_type") or source.discovery.get("type") or "unknown")
    if discovery.get("status") == "no_publication_for_date":
        timestamp = datetime.now().isoformat(timespec="seconds")
        job["status"] = "skipped"
        job["source"] = _build_source_state(
            source=source,
            requested_date=str(job.get("date")),
            issue_date=None,
            publication_status="no_publication_for_date",
            discovery_type=discovery_type,
            front_page_url=None,
            discovered_pages_count=0,
            summary_path=artifact_paths["summary_path"],
            probe_path=artifact_paths["probe_path"],
        )
        job["audit"]["updated_at"] = timestamp
        job["audit"].setdefault("events", []).append(
            {
                "stage": "scrape_source",
                "status": "skipped",
                "timestamp": timestamp,
                "details": "La fuente no tiene edicion publicada para la fecha solicitada.",
            }
        )
        return write_json(job_manifest_path, job)

    job_dir = job_manifest_path.parent
    ensure_job_scaffold(job_dir)
    front_page_asset = stage_front_page_asset(
        job_dir=job_dir,
        front_page_image=None,
        front_page_url=str(discovery.get("front_page_url") or ""),
        download_front_page=True,
    )
    if front_page_asset is None:
        raise ValueError("No se pudo descubrir una portada descargable para la fuente.")

    page_urls = [
        str(page.get("source_url"))
        for page in discovery.get("supporting_pages", [])
        if page.get("source_url")
    ]
    input_assets = build_input_assets(
        project_dir=project_dir,
        source_config_path=source_config_path,
        source_url=str(discovery.get("source_url") or source.base_url),
        front_page_url=str(discovery.get("front_page_url") or discovery.get("source_url") or source.base_url),
        front_page_asset=front_page_asset,
        supporting_pages=[],
    )
    job["input_assets"] = input_assets
    job["source"] = _build_source_state(
        source=source,
        requested_date=str(job.get("date")),
        issue_date=str(issue_date) if issue_date else None,
        publication_status="available",
        discovery_type=discovery_type,
        front_page_url=str(discovery.get("front_page_url") or ""),
        discovered_pages_count=len(discovered_pages),
        summary_path=artifact_paths["summary_path"],
        probe_path=artifact_paths["probe_path"],
    )
    timestamp = datetime.now().isoformat(timespec="seconds")
    job["status"] = "scraped"
    job["audit"]["updated_at"] = timestamp
    job["audit"].setdefault("events", []).append(
        {
            "stage": "scrape_source",
            "status": "completed",
            "timestamp": timestamp,
            "details": (
                "Fuente analizada desde HTML; portada descubierta y "
                f"{len(page_urls)} paginas de apoyo detectadas."
            ),
        }
    )
    write_json(job_manifest_path, job)

    if page_urls:
        return ingest_supporting_pages(
            job_manifest_path=job_manifest_path,
            page_urls=page_urls,
            page_images=[],
        )
    return write_json(job_manifest_path, job)


def archive_source_for_date(
    *,
    source_config_path: Path,
    job_date: str,
    source_url: str | None = None,
    max_supporting_pages: int = 3,
    retention_days: int = 7,
) -> dict[str, object]:
    manifest_path = archive_source_scrape(
        source_config_path=source_config_path,
        job_date=job_date,
        source_url=source_url,
        max_supporting_pages=max_supporting_pages,
    )
    deleted = prune_source_storage(
        source_config_path=source_config_path,
        retention_days=retention_days,
    )
    manifest = read_json(manifest_path)
    result_status = "archived"
    if manifest.get("status") == "no_publication_for_date":
        result_status = "skipped_no_publication"
    return {
        "status": result_status,
        "manifest_path": manifest_path.resolve().relative_to(get_project_dir()).as_posix(),
        "reason": manifest.get("status"),
        "deleted_folders": [path.name for path in deleted],
    }


def archive_all_sources_for_date(
    *,
    sources_dir: Path,
    job_date: str,
    max_supporting_pages: int = 3,
    retention_days: int = 7,
) -> list[dict[str, object]]:
    return archive_all_sources(
        sources_dir=sources_dir,
        job_date=job_date,
        max_supporting_pages=max_supporting_pages,
        retention_days=retention_days,
    )


def prepare_script_package_for_job(
    *,
    job_manifest_path: Path,
    script_template_path: Path,
    output_dir: Path | None = None,
    force: bool = False,
) -> Path:
    return prepare_chatgpt_script_package(
        job_manifest_path=job_manifest_path,
        script_template_path=script_template_path,
        output_dir=output_dir,
        force=force,
    )


def import_script_for_job(
    *,
    job_manifest_path: Path,
    generated_text: str | None = None,
    generated_text_file: Path | None = None,
    provider: str = "chatgpt_plus_manual",
    model: str | None = None,
    approve: bool = False,
) -> Path:
    return import_generated_script(
        job_manifest_path=job_manifest_path,
        generated_text=generated_text,
        generated_text_file=generated_text_file,
        provider=provider,
        model=model,
        approve=approve,
    )


def list_available_voicebox_profiles(*, voice_profile_path: Path | None = None) -> list[dict[str, object]]:
    provider_settings: dict[str, object] | None = None
    if voice_profile_path is not None:
        provider_settings = VoiceProfile.load(voice_profile_path).provider_settings
    return list_voicebox_profiles(provider_settings)


def _resolve_audio_for_transcription(*, job: dict, audio_file: Path | None) -> Path:
    if audio_file is not None:
        if not audio_file.exists():
            raise FileNotFoundError(f"No existe el archivo de audio: {audio_file}")
        return audio_file

    audio_path_value = job.get("voice", {}).get("audio_path")
    if not audio_path_value:
        raise ValueError(
            "El job no tiene `voice.audio_path`. Ejecuta `voice-job` antes o pasa `--audio-file`."
        )

    resolved = get_project_dir() / audio_path_value
    if not resolved.exists():
        raise FileNotFoundError(f"No existe el audio referenciado en el job: {resolved}")
    return resolved


def transcribe_job_audio(
    *,
    job_manifest_path: Path,
    voice_profile_path: Path,
    audio_file: Path | None = None,
    force: bool = False,
) -> Path:
    project_dir = get_project_dir()
    job = read_json(job_manifest_path)
    voice = VoiceProfile.load(voice_profile_path)
    current_text = job.get("transcription", {}).get("text", "").strip()
    if current_text and not force:
        raise ValueError(
            "El job ya tiene una transcripcion guardada. Usa `--force` si quieres regenerarla."
        )

    resolved_audio = _resolve_audio_for_transcription(job=job, audio_file=audio_file)
    transcription = transcribe_with_voicebox(
        audio_path=resolved_audio,
        provider_settings=voice.provider_settings,
    )
    transcription_text = str(transcription.get("text", "")).strip()
    if not transcription_text:
        raise ValueError("Voicebox no devolvio texto en la transcripcion.")

    duration = transcription.get("duration")
    output_path = job_manifest_path.parent / "output" / "transcription.json"
    write_json(
        output_path,
        {
            "provider": "voicebox_local",
            "text": transcription_text,
            "duration_seconds": duration,
            "source_audio_path": resolved_audio.resolve().relative_to(project_dir).as_posix()
            if resolved_audio.is_relative_to(project_dir.resolve())
            else str(resolved_audio.resolve()),
        },
    )

    timestamp = datetime.now().isoformat(timespec="seconds")
    job["transcription"] = {
        "provider": "voicebox_local",
        "text": transcription_text,
        "duration_seconds": duration,
        "source_audio_path": resolved_audio.resolve().relative_to(project_dir).as_posix()
        if resolved_audio.is_relative_to(project_dir.resolve())
        else str(resolved_audio.resolve()),
        "output_path": output_path.resolve().relative_to(project_dir).as_posix(),
    }
    job["audit"]["updated_at"] = timestamp
    job["audit"].setdefault("events", []).append(
        {
            "stage": "transcribe",
            "status": "completed",
            "timestamp": timestamp,
            "details": "Audio transcrito con Voicebox.",
        }
    )
    return write_json(job_manifest_path, job)


def _resolve_repo_path(path_value: str | None) -> Path | None:
    if not path_value:
        return None
    return get_project_dir() / Path(path_value)


def _normalize_text_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _to_project_relative(path: Path, *, project_dir: Path) -> str:
    return path.resolve().relative_to(project_dir).as_posix()


def _build_ocr_source_entry(
    *,
    source_kind: str,
    text: str,
    project_dir: Path,
    ocr_text_path: Path | None = None,
    asset_path: Path | None = None,
    role: str | None = None,
    label: str | None = None,
    page_number: int | None = None,
) -> dict[str, object]:
    return {
        "source_kind": source_kind,
        "role": role,
        "label": label,
        "page_number": page_number,
        "asset_path": _to_project_relative(asset_path, project_dir=project_dir) if asset_path else None,
        "ocr_text_path": _to_project_relative(ocr_text_path, project_dir=project_dir)
        if ocr_text_path and ocr_text_path.exists()
        else None,
        "character_count": len(text),
        "line_count": len(_normalize_text_lines(text)),
    }


def _build_job_asset_ocr_candidates(*, job: dict) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    front_page_value = job.get("input_assets", {}).get("front_page_image")
    front_page = _resolve_repo_path(front_page_value)
    if front_page is not None and front_page.exists():
        candidates.append(
            {
                "role": "front_page",
                "label": "Portada",
                "page_number": 1,
                "asset_path": front_page,
            }
        )

    for page in job.get("input_assets", {}).get("pages", []):
        local_path_value = page.get("local_path")
        if not local_path_value:
            continue
        asset_path = _resolve_repo_path(str(local_path_value))
        if asset_path is None or not asset_path.exists():
            continue
        role = str(page.get("role") or "supporting_page")
        if role == "front_page" and any(item.get("role") == "front_page" for item in candidates):
            continue
        candidates.append(
            {
                "role": role,
                "label": str(page.get("label") or "Pagina"),
                "page_number": int(page["page_number"]) if page.get("page_number") is not None else None,
                "asset_path": asset_path,
            }
        )
    return candidates


def _load_ocr_sources_with_paddleocr(
    *,
    job: dict,
    project_dir: Path,
    ocr_scope: str,
) -> list[dict[str, object]]:
    ocr_sources: list[dict[str, object]] = []
    for candidate in _build_job_asset_ocr_candidates(job=job):
        if ocr_scope == "front_page" and str(candidate.get("role")) != "front_page":
            continue
        asset_path = Path(candidate["asset_path"])
        ocr_result = extract_text_with_paddleocr(image_path=asset_path, lang="es")
        text = str(ocr_result.get("text") or "").strip()
        if not text:
            continue
        ocr_sources.append(
            {
                **_build_ocr_source_entry(
                    source_kind="paddleocr",
                    text=text,
                    project_dir=project_dir,
                    ocr_text_path=None,
                    asset_path=asset_path,
                    role=str(candidate.get("role") or "ocr"),
                    label=str(candidate.get("label") or "OCR"),
                    page_number=int(candidate["page_number"]) if candidate.get("page_number") is not None else None,
                ),
                "ocr_engine": "paddleocr",
                "ocr_lines": list(ocr_result.get("lines") or []),
                "ocr_item_count": len(ocr_result.get("items") or []),
            }
        )
    return ocr_sources


def _load_ocr_sources_from_directory(
    *,
    ocr_dir: Path,
    job: dict,
    project_dir: Path,
) -> list[dict[str, object]]:
    if not ocr_dir.exists():
        raise FileNotFoundError(f"No existe el directorio OCR: {ocr_dir}")
    if not ocr_dir.is_dir():
        raise ValueError(f"`--ocr-dir` debe ser una carpeta: {ocr_dir}")

    ocr_sources: list[dict[str, object]] = []
    for candidate in _build_job_asset_ocr_candidates(job=job):
        asset_path = candidate["asset_path"]
        stem = Path(asset_path).stem
        ocr_text_path = ocr_dir / f"{stem}.txt"
        if not ocr_text_path.exists():
            continue
        text = ocr_text_path.read_text(encoding="utf-8")
        ocr_sources.append(
            _build_ocr_source_entry(
                source_kind="ocr_dir_file",
                text=text,
                project_dir=project_dir,
                ocr_text_path=ocr_text_path,
                asset_path=asset_path,
                role=str(candidate.get("role") or "ocr"),
                label=str(candidate.get("label") or "OCR"),
                page_number=int(candidate["page_number"]) if candidate.get("page_number") is not None else None,
            )
        )
    return ocr_sources


def _load_ocr_text(
    *,
    job_manifest_path: Path,
    ocr_engine: str,
    ocr_scope: str,
    ocr_dir: Path | None,
    ocr_text: str | None,
    ocr_text_file: Path | None,
) -> tuple[str, Path | None, list[dict[str, object]]]:
    project_dir = get_project_dir()
    work_dir = job_manifest_path.parent / "work" / "ocr"
    work_dir.mkdir(parents=True, exist_ok=True)
    job = read_json(job_manifest_path)

    if ocr_engine == "paddleocr":
        ocr_sources = _load_ocr_sources_with_paddleocr(
            job=job,
            project_dir=project_dir,
            ocr_scope=ocr_scope,
        )
        if not ocr_sources:
            raise ValueError("PaddleOCR no devolvio texto util para los assets seleccionados.")
        combined_parts = []
        for source in ocr_sources:
            label = source.get("label") or source.get("role") or "OCR"
            ocr_lines = list(source.get("ocr_lines") or [])
            text = "\n".join(ocr_lines).strip()
            if text:
                combined_parts.append(f"[{label}]\n{text}")
        combined_text = "\n\n".join(part for part in combined_parts if part.strip()).strip()
        combined_file = work_dir / "combined-paddleocr.txt"
        combined_file.write_text(combined_text, encoding="utf-8")
        return combined_text, combined_file, ocr_sources

    if ocr_text_file is not None:
        if not ocr_text_file.exists():
            raise FileNotFoundError(f"No existe el archivo OCR: {ocr_text_file}")
        text = ocr_text_file.read_text(encoding="utf-8")
        return text, ocr_text_file, [
            _build_ocr_source_entry(
                source_kind="external_file",
                text=text,
                project_dir=project_dir,
                ocr_text_path=ocr_text_file,
            )
        ]

    if ocr_text is not None:
        work_file = work_dir / "inline-ocr.txt"
        work_file.write_text(ocr_text, encoding="utf-8")
        return ocr_text, work_file, [
            _build_ocr_source_entry(
                source_kind="inline_text",
                text=ocr_text,
                project_dir=project_dir,
                ocr_text_path=work_file,
            )
        ]

    if ocr_dir is not None:
        ocr_sources = _load_ocr_sources_from_directory(
            ocr_dir=ocr_dir,
            job=job,
            project_dir=project_dir,
        )
        if not ocr_sources:
            raise ValueError(
                "No se encontraron archivos OCR en `--ocr-dir` que coincidan con los assets del job."
            )
        combined_parts: list[str] = []
        for source in ocr_sources:
            label = source.get("label") or source.get("role") or "OCR"
            text_path = source.get("ocr_text_path")
            text = ""
            if text_path:
                resolved_text_path = _resolve_repo_path(str(text_path))
                if resolved_text_path and resolved_text_path.exists():
                    text = resolved_text_path.read_text(encoding="utf-8")
            if text:
                combined_parts.append(f"[{label}]\n{text.strip()}")
        combined_text = "\n\n".join(part for part in combined_parts if part.strip()).strip()
        combined_file = work_dir / "combined-ocr.txt"
        combined_file.write_text(combined_text, encoding="utf-8")
        return combined_text, combined_file, ocr_sources

    ocr_sources: list[dict[str, object]] = []

    for candidate in _build_job_asset_ocr_candidates(job=job):
        asset_path = candidate["asset_path"]
        sidecar = Path(asset_path).with_suffix(".txt")
        if not sidecar.exists():
            continue
        page_text = sidecar.read_text(encoding="utf-8")
        ocr_sources.append(
            _build_ocr_source_entry(
                source_kind="sidecar_file",
                text=page_text,
                project_dir=project_dir,
                ocr_text_path=sidecar,
                asset_path=asset_path,
                role=str(candidate.get("role") or "ocr"),
                label=str(candidate.get("label") or "OCR"),
                page_number=int(candidate["page_number"]) if candidate.get("page_number") is not None else None,
            )
        )

    if ocr_sources:
        combined_parts: list[str] = []
        for source in ocr_sources:
            label = source.get("label") or source.get("role") or "OCR"
            text_path = source.get("ocr_text_path")
            text = ""
            if text_path:
                resolved_text_path = _resolve_repo_path(str(text_path))
                if resolved_text_path and resolved_text_path.exists():
                    text = resolved_text_path.read_text(encoding="utf-8")
            if text:
                combined_parts.append(f"[{label}]\n{text.strip()}")
        combined_text = "\n\n".join(part for part in combined_parts if part.strip()).strip()
        if len(ocr_sources) == 1:
            only_source = ocr_sources[0]
            only_path = _resolve_repo_path(str(only_source.get("ocr_text_path")))
            return combined_text, only_path, ocr_sources

        combined_file = work_dir / "combined-ocr.txt"
        combined_file.write_text(combined_text, encoding="utf-8")
        return combined_text, combined_file, ocr_sources

    raise ValueError(
        "No se encontro texto OCR. Pasa `--ocr-text`, `--ocr-text-file` o crea sidecars `.txt` junto a la portada o paginas de apoyo."
    )


def _split_ocr_blocks(text: str) -> list[dict[str, str]]:
    lines = _normalize_text_lines(text)
    return [{"text": line} for line in lines]


def _select_headline_candidates(lines: list[str], *, max_items: int = 3) -> list[str]:
    candidates: list[str] = []
    for line in lines:
        if len(line) < 18:
            continue
        if re.search(r"\b\d{3,}\b", line):
            continue
        candidates.append(line)
        if len(candidates) >= max_items:
            break
    return candidates


def _contains_any(text: str, keywords: list[str]) -> bool:
    lowered = text.casefold()
    return any(keyword.casefold() in lowered for keyword in keywords)


def _count_matches(text: str, keywords: list[str]) -> int:
    lowered = text.casefold()
    return sum(1 for keyword in keywords if keyword.casefold() in lowered)


_PAGE_REF_PATTERN = re.compile(
    r"(?i)\b(?:p[aá]g(?:ina)?s?\.?|pp?\.?)\s*(\d{1,3})(?:\s*[-/]\s*(\d{1,3}))?"
)
_INLINE_PAGE_SUFFIX_PATTERN = re.compile(r"(?i)^(.*?)(?:[\s:;-]+)(\d{1,3})\s*$")


def _clean_cover_headline(text: str) -> str:
    cleaned = " ".join(text.replace("|", " ").split()).strip(" -:;,.")
    return cleaned


def _is_probable_headline(text: str) -> bool:
    cleaned = _clean_cover_headline(text)
    if len(cleaned) < 12:
        return False
    if re.fullmatch(r"\d+", cleaned):
        return False
    return True


def _extract_page_candidates_from_cover(lines: list[str]) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []

    for index, raw_line in enumerate(lines):
        line = " ".join(raw_line.split()).strip()
        if not line:
            continue

        explicit_matches = list(_PAGE_REF_PATTERN.finditer(line))
        if explicit_matches:
            for match in explicit_matches:
                page_texts = [group for group in match.groups() if group]
                for page_text in page_texts:
                    page_number = int(page_text)
                    if page_number <= 1:
                        continue
                    headline_text = _clean_cover_headline(line[: match.start()] or line)
                    if not _is_probable_headline(headline_text):
                        previous_line = lines[index - 1] if index > 0 else ""
                        next_line = lines[index + 1] if index + 1 < len(lines) else ""
                        for alternative in (previous_line, next_line):
                            if _is_probable_headline(alternative):
                                headline_text = _clean_cover_headline(alternative)
                                break
                    if not _is_probable_headline(headline_text):
                        headline_text = f"Referencia de portada a pagina {page_number}"
                    candidates.append(
                        {
                            "headline": headline_text,
                            "page_number": page_number,
                            "evidence_line": line,
                            "line_index": index,
                            "method": "local_regex_explicit",
                            "confidence": 0.9,
                        }
                    )
            continue

        inline_match = _INLINE_PAGE_SUFFIX_PATTERN.match(line)
        if not inline_match:
            continue
        headline_text = _clean_cover_headline(inline_match.group(1))
        if not _is_probable_headline(headline_text):
            continue
        page_number = int(inline_match.group(2))
        if page_number <= 1:
            continue
        candidates.append(
            {
                "headline": headline_text,
                "page_number": page_number,
                "evidence_line": line,
                "line_index": index,
                "method": "local_regex_inline",
                "confidence": 0.6,
            }
        )

    deduped: list[dict[str, object]] = []
    seen_pairs: set[tuple[str, int]] = set()
    for candidate in candidates:
        key = (str(candidate["headline"]).casefold(), int(candidate["page_number"]))
        if key in seen_pairs:
            continue
        seen_pairs.add(key)
        deduped.append(candidate)
    return deduped


def _parse_manual_page_selection_payload(text: str) -> tuple[list[dict[str, object]], str]:
    stripped = text.strip()
    if not stripped:
        raise ValueError("La seleccion manual de paginas esta vacia.")

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        payload = None

    candidates: list[dict[str, object]] = []
    if isinstance(payload, dict):
        if isinstance(payload.get("notes"), str):
            notes = payload["notes"].strip()
        else:
            notes = ""
        raw_items = payload.get("items") or payload.get("candidates") or payload.get("pages") or []
        if not isinstance(raw_items, list):
            raise ValueError("El JSON manual debe incluir una lista en `items`, `candidates` o `pages`.")
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            page_number = int(item.get("page_number"))
            if page_number <= 1:
                continue
            headline = _clean_cover_headline(str(item.get("headline") or f"Pagina {page_number}"))
            story_type = _normalize_story_type(
                item.get("story_type") or item.get("category") or item.get("section")
            )
            cover_region = _normalize_cover_region(
                item.get("cover_region") or item.get("cover_focus") or item.get("cover_bbox")
            )
            candidates.append(
                {
                    "headline": headline,
                    "story_type": story_type,
                    "cover_region": cover_region,
                    "page_number": page_number,
                    "evidence_line": str(item.get("evidence_line") or headline),
                    "line_index": None,
                    "method": "manual_import",
                    "confidence": float(item.get("confidence", 1.0)),
                }
            )
        return candidates, notes

    notes = ""
    for raw_line in stripped.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = _PAGE_REF_PATTERN.search(line)
        if not match:
            continue
        page_number = int(match.group(1))
        if page_number <= 1:
            continue
        headline = _clean_cover_headline(line[: match.start()] or line)
        if not _is_probable_headline(headline):
            headline = f"Pagina {page_number}"
        candidates.append(
            {
                "headline": headline,
                "story_type": "actualidad",
                "cover_region": None,
                "page_number": page_number,
                "evidence_line": line,
                "line_index": None,
                "method": "manual_import",
                "confidence": 1.0,
            }
        )
    if not candidates:
        raise ValueError("No se encontraron referencias de pagina en la seleccion manual.")
    return candidates, notes


def _normalize_story_type(value: object) -> str:
    raw = " ".join(str(value or "").strip().lower().split())
    if not raw:
        return "actualidad"
    mapping = {
        "actualidad": "actualidad",
        "politica": "politica",
        "política": "politica",
        "policial": "policial",
        "deportes": "deportes",
        "deporte": "deportes",
        "mundo": "mundo",
        "economia": "economia",
        "economía": "economia",
        "espectaculos": "espectaculos",
        "espectáculos": "espectaculos",
    }
    return mapping.get(raw, raw)


def _clamp_normalized(value: object, *, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(0.0, min(1.0, parsed))


def _normalize_cover_region(value: object) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None

    x = _clamp_normalized(value.get("x", value.get("left")), default=0.0)
    y = _clamp_normalized(value.get("y", value.get("top")), default=0.0)
    width = _clamp_normalized(value.get("width", value.get("w")), default=0.0)
    height = _clamp_normalized(value.get("height", value.get("h")), default=0.0)

    if width <= 0 or height <= 0:
        return None

    if x + width > 1.0:
        width = max(0.01, 1.0 - x)
    if y + height > 1.0:
        height = max(0.01, 1.0 - y)

    return {
        "x": round(x, 4),
        "y": round(y, 4),
        "width": round(width, 4),
        "height": round(height, 4),
    }


def _normalize_story_page_numbers(value: object) -> list[int]:
    if not isinstance(value, list):
        return []
    page_numbers: list[int] = []
    for item in value:
        try:
            page_number = int(item)
        except (TypeError, ValueError):
            continue
        if page_number > 1 and page_number not in page_numbers:
            page_numbers.append(page_number)
    return sorted(page_numbers)


def _normalize_key_facts(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    key_facts: list[str] = []
    for item in value:
        fact = " ".join(str(item or "").split()).strip()
        if fact and fact not in key_facts:
            key_facts.append(fact)
    return key_facts[:3]


def _build_cover_story_groups(candidates: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str], dict[str, object]] = {}

    for candidate in candidates:
        headline = _clean_cover_headline(str(candidate.get("headline") or "")).strip()
        if not headline:
            continue
        story_type = _normalize_story_type(candidate.get("story_type"))
        cover_region = _normalize_cover_region(candidate.get("cover_region"))
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
                "max_confidence": 0.0,
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
        story["max_confidence"] = round(max(float(story["max_confidence"]), confidence), 4)

    stories: list[dict[str, object]] = []
    for story in grouped.values():
        page_numbers = sorted(int(page) for page in story["page_numbers"])
        stories.append(
            {
                "headline": story["headline"],
                "story_type": story["story_type"],
                "cover_region": story["cover_region"],
                "page_numbers": page_numbers,
                "evidence": " | ".join(story["evidence_lines"][:3]),
                "evidence_lines": story["evidence_lines"],
                "confidence": story["max_confidence"],
            }
        )

    stories.sort(
        key=lambda item: (
            min(item.get("page_numbers") or [999]),
            str(item.get("headline") or "").casefold(),
        )
    )
    return stories


def _parse_story_narrative_payload(text: str) -> tuple[list[dict[str, object]], str]:
    stripped = text.strip()
    if not stripped:
        raise ValueError("La importacion editorial por historia esta vacia.")

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError("La importacion editorial debe ser JSON valido.") from exc

    notes = ""
    raw_stories: object
    if isinstance(payload, dict):
        notes = str(payload.get("notes") or "").strip()
        raw_stories = payload.get("stories") or payload.get("items") or []
    else:
        raw_stories = payload

    if not isinstance(raw_stories, list):
        raise ValueError("La importacion editorial debe incluir una lista en `stories` o `items`.")

    stories: list[dict[str, object]] = []
    for item in raw_stories:
        if not isinstance(item, dict):
            continue
        headline = _clean_cover_headline(str(item.get("headline") or ""))
        speech = " ".join(str(item.get("speech") or item.get("summary") or "").split()).strip()
        if not headline or not speech:
            continue
        key_facts = item.get("key_facts_used")
        if key_facts in (None, ""):
            key_facts = item.get("key_facts")
        stories.append(
            {
                "headline": headline,
                "story_type": (
                    _normalize_story_type(item.get("story_type"))
                    if item.get("story_type") not in (None, "")
                    else None
                ),
                "summary": speech,
                "speech": speech,
                "narrator_profile_id": " ".join(str(item.get("narrator_profile_id") or "").split()).strip(),
                "tone_notes": _normalize_key_facts(item.get("tone_notes")),
                "page_numbers": _normalize_story_page_numbers(item.get("page_numbers")),
                "cover_region": _normalize_cover_region(item.get("cover_region")),
                "key_facts": _normalize_key_facts(key_facts),
                "safety_notes": " ".join(
                    str(item.get("safety_notes") or item.get("notes") or "").split()
                ).strip(),
                "notes": " ".join(str(item.get("notes") or item.get("safety_notes") or "").split()).strip(),
            }
        )

    if not stories:
        raise ValueError("La importacion editorial no contiene historias validas con `headline` y `speech`.")
    return stories, notes


def _parse_batch_story_narrative_payload(text: str) -> tuple[list[dict[str, object]], str]:
    stripped = text.strip()
    if not stripped:
        raise ValueError("La importacion batch editorial esta vacia.")

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError("La importacion batch editorial debe ser JSON valido.") from exc

    batch_notes = ""
    raw_entries: object
    if isinstance(payload, dict):
        batch_notes = str(payload.get("notes") or "").strip()
        raw_entries = payload.get("newspapers") or payload.get("jobs") or payload.get("items") or []
    else:
        raw_entries = payload

    if not isinstance(raw_entries, list):
        raise ValueError("La importacion batch editorial debe incluir una lista en `newspapers`, `jobs` o `items`.")

    entries: list[dict[str, object]] = []
    for entry in raw_entries:
        if not isinstance(entry, dict):
            continue
        job_id = str(entry.get("job_id") or "").strip()
        if not job_id:
            continue
        stories, entry_notes = _parse_story_narrative_payload(
            json.dumps(
                {
                    "notes": entry.get("notes") or "",
                    "stories": entry.get("stories") or entry.get("items") or [],
                },
                ensure_ascii=False,
            )
        )
        entries.append(
            {
                "job_id": job_id,
                "newspaper_name": str(entry.get("newspaper_name") or "").strip(),
                "provider": str(entry.get("provider") or "").strip(),
                "stories": stories,
                "notes": entry_notes,
            }
        )

    if not entries:
        raise ValueError("La importacion batch editorial no contiene entradas validas con `job_id`.")
    return entries, batch_notes


def _merge_story_narrative_with_cover_context(
    *,
    cover_stories: list[dict[str, object]],
    imported_stories: list[dict[str, object]],
    project_dir: Path,
) -> list[dict[str, object]]:
    cover_story_map = {
        _clean_cover_headline(str(story.get("headline") or "")).casefold(): story
        for story in cover_stories
        if str(story.get("headline") or "").strip()
    }
    used_cover_indexes: set[int] = set()
    merged: list[dict[str, object]] = []
    for item in imported_stories:
        headline = str(item.get("headline") or "").strip()
        if not headline:
            continue
        cover_story = cover_story_map.get(_clean_cover_headline(headline).casefold(), {})
        if not cover_story:
            cover_story = _find_best_cover_story_match(
                imported_story=item,
                cover_stories=cover_stories,
                used_indexes=used_cover_indexes,
            )
        page_numbers = item.get("page_numbers") or cover_story.get("page_numbers") or []
        cover_region = item.get("cover_region") or cover_story.get("cover_region")
        story_type = item.get("story_type") or cover_story.get("story_type") or "actualidad"
        narrator_config = _resolve_story_narrator_config(
            story_type=story_type,
            narrator_profile_id=item.get("narrator_profile_id"),
            project_dir=project_dir,
        )
        imported_tone_notes = _normalize_key_facts(item.get("tone_notes"))
        merged.append(
            {
                "headline": headline,
                "story_type": narrator_config["story_type"],
                "summary": str(item.get("summary") or "").strip(),
                "speech": str(item.get("speech") or item.get("summary") or "").strip(),
                "narrator_profile_id": narrator_config["narrator_profile_id"],
                "narrator_role": narrator_config["role"],
                "tone_notes": imported_tone_notes or narrator_config["tone_notes"],
                "page_numbers": _normalize_story_page_numbers(page_numbers),
                "cover_region": _normalize_cover_region(cover_region),
                "key_facts": _normalize_key_facts(item.get("key_facts")),
                "key_facts_used": _normalize_key_facts(item.get("key_facts")),
                "narrator_map_id": narrator_config["map_id"],
                "safety_notes": " ".join(str(item.get("safety_notes") or item.get("notes") or "").split()).strip(),
                "notes": " ".join(str(item.get("notes") or "").split()).strip(),
            }
        )
    return merged


def _build_script_from_story_speeches(stories: list[dict[str, object]]) -> str:
    speeches: list[str] = []
    for story in stories:
        speech = " ".join(str(story.get("speech") or story.get("summary") or "").split()).strip()
        if speech:
            speeches.append(speech)
    return "\n\n".join(speeches)


def _enrich_job_story_narrative_with_cover_context(job: dict[str, object]) -> list[dict[str, object]]:
    project_dir = get_project_dir()
    story_items = [
        story
        for story in job.get("story_narrative", {}).get("stories", [])
        if str(story.get("speech") or story.get("summary") or "").strip()
    ]
    cover_stories = list(job.get("page_selection", {}).get("stories", []))
    if not cover_stories:
        return story_items

    used_cover_indexes: set[int] = set()
    enriched: list[dict[str, object]] = []
    for story in story_items:
        cover_story = {}
        if not story.get("cover_region"):
            cover_story = _find_best_cover_story_match(
                imported_story=story,
                cover_stories=cover_stories,
                used_indexes=used_cover_indexes,
            )
        narrator_config = _resolve_story_narrator_config(
            story_type=story.get("story_type") or cover_story.get("story_type") or "actualidad",
            narrator_profile_id=story.get("narrator_profile_id"),
            project_dir=project_dir,
        )
        tone_notes = _normalize_key_facts(story.get("tone_notes")) or narrator_config["tone_notes"]
        enriched.append(
            {
                **story,
                "cover_region": _normalize_cover_region(story.get("cover_region") or cover_story.get("cover_region")),
                "page_numbers": _normalize_story_page_numbers(
                    story.get("page_numbers") or cover_story.get("page_numbers")
                ),
                "story_type": narrator_config["story_type"],
                "narrator_profile_id": narrator_config["narrator_profile_id"],
                "narrator_role": narrator_config["role"],
                "tone_notes": tone_notes,
                "narrator_map_id": narrator_config["map_id"],
            }
        )
    return enriched


def _format_spanish_date(value: str) -> str:
    months = {
        1: "enero",
        2: "febrero",
        3: "marzo",
        4: "abril",
        5: "mayo",
        6: "junio",
        7: "julio",
        8: "agosto",
        9: "septiembre",
        10: "octubre",
        11: "noviembre",
        12: "diciembre",
    }
    try:
        parsed = datetime.fromisoformat(value).date()
    except ValueError:
        return value
    return f"{parsed.day} de {months[parsed.month]} de {parsed.year}"


def _build_rundown_intro(*, job_date: str, source_names: list[str], story_count: int) -> str:
    date_text = _format_spanish_date(job_date)
    source_text = ", ".join(source_names[:-1]) + f" y {source_names[-1]}" if len(source_names) > 1 else source_names[0]
    return (
        f"Hola, hoy {date_text} revisamos las portadas de {source_text}. "
        f"Hay {story_count} temas clave para entender la agenda del dia: politica, actualidad, economia, deportes y policiales. "
        "Vamos diario por diario, con lo central y sin rodeos."
    )


def _build_newspaper_connector_text(source_name: str, *, story_count: int | None = None) -> str:
    if story_count and story_count > 1:
        return (
            f"Ahora entramos a {source_name}. Primero miramos la portada completa y despues vamos con "
            f"sus {story_count} historias mas fuertes."
        )
    return f"Ahora entramos a {source_name}. Miramos la portada completa y vamos con su noticia clave."


def _select_imported_rundown_intro(jobs: list[dict[str, object]]) -> str:
    for job in jobs:
        intro = job.get("rundown_intro")
        if not isinstance(intro, dict):
            continue
        speech = " ".join(str(intro.get("speech") or "").split()).strip()
        if speech:
            return speech
    return ""


def _build_story_narrative_manifest_payload(
    *,
    job: dict[str, object],
    voice_profile_path: Path | None = None,
    include_audio_segments: bool = True,
) -> dict[str, object]:
    project_dir = get_project_dir()
    source_name = _format_source_name(str(job.get("source_id") or ""))
    front_page_image = job.get("input_assets", {}).get("front_page_image")
    enriched_stories = _enrich_job_story_narrative_with_cover_context(job)
    voice_segments = list(job.get("voice", {}).get("segments", [])) if include_audio_segments else []
    fallback_voice_path = voice_profile_path
    if fallback_voice_path is None:
        fallback_id = str(job.get("voice", {}).get("profile_id") or "").strip()
        fallback_candidate = project_dir / "automation" / "templates" / "voices" / f"{fallback_id}.json"
        if fallback_candidate.exists():
            fallback_voice_path = fallback_candidate

    stories_payload: list[dict[str, object]] = []
    for index, story in enumerate(enriched_stories, start=1):
        story_voice_segment = voice_segments[index - 1] if index - 1 < len(voice_segments) else {}
        narrator_config = _resolve_story_narrator_config(
            story_type=story.get("story_type") or "actualidad",
            narrator_profile_id=story.get("narrator_profile_id"),
            project_dir=project_dir,
        )
        segment_voice = None
        if fallback_voice_path is not None:
            segment_voice = _resolve_voice_profile_for_narrator(
                narrator_profile_id=narrator_config["narrator_profile_id"],
                fallback_voice_profile_path=fallback_voice_path,
                project_dir=project_dir,
            )
        stories_payload.append(
            {
                "story_index": index,
                "segment_type": "story",
                "headline": story.get("headline") or "",
                "story_type": narrator_config["story_type"],
                "summary": str(story.get("summary") or "").strip(),
                "speech": str(story.get("speech") or story.get("summary") or "").strip(),
                "page_numbers": _normalize_story_page_numbers(story.get("page_numbers")),
                "cover_region": _normalize_cover_region(story.get("cover_region")),
                "key_facts": _normalize_key_facts(story.get("key_facts") or story.get("key_facts_used")),
                "tone_notes": _normalize_key_facts(story.get("tone_notes")) or narrator_config["tone_notes"],
                "safety_notes": " ".join(str(story.get("safety_notes") or "").split()).strip(),
                "notes": " ".join(str(story.get("notes") or "").split()).strip(),
                "narrator_profile_id": narrator_config["narrator_profile_id"],
                "narrator_role": narrator_config["role"],
                "narrator_map_id": narrator_config["map_id"],
                "voice_profile_id": (
                    str(story_voice_segment.get("voice_profile_id") or "")
                    or (segment_voice.profile_id if segment_voice is not None else "")
                ),
                "narrator_name": (
                    str(story_voice_segment.get("narrator_name") or "")
                    or (segment_voice.narrator_name if segment_voice is not None else "")
                ),
                "segment_audio_file": str(story_voice_segment.get("audio_path") or "").strip() or None,
            }
        )

    return {
        "manifest_type": "story_narrative_manifest",
        "manifest_version": 1,
        "job_id": job.get("job_id"),
        "source_id": job.get("source_id"),
        "source_name": source_name,
        "date": job.get("date"),
        "front_page_image": front_page_image,
        "story_type_map_path": (
            get_story_type_narrator_map_path(project_dir).resolve().relative_to(project_dir).as_posix()
        ),
        "story_type_map_id": _load_story_type_narrator_map(project_dir=project_dir).get("map_id"),
        "stories": stories_payload,
    }


def _sync_story_narrative_manifest(
    *,
    job: dict[str, object],
    job_manifest_path: Path,
    voice_profile_path: Path | None = None,
) -> str | None:
    stories = [
        story
        for story in job.get("story_narrative", {}).get("stories", [])
        if str(story.get("speech") or story.get("summary") or "").strip()
    ]
    if not stories:
        job.setdefault("story_narrative", {})["manifest_path"] = None
        return None

    project_dir = get_project_dir()
    manifest_path = job_manifest_path.parent / "review" / "story-narrative-manifest.json"
    payload = _build_story_narrative_manifest_payload(
        job=job,
        voice_profile_path=voice_profile_path,
        include_audio_segments=True,
    )
    write_json(manifest_path, payload)
    relative_path = manifest_path.resolve().relative_to(project_dir).as_posix()
    job.setdefault("story_narrative", {})["manifest_path"] = relative_path
    return relative_path


def _sort_jobs_for_rundown(jobs: list[dict[str, object]]) -> list[dict[str, object]]:
    order = {source_id: index for index, source_id in enumerate(SOURCE_RUNDOWN_ORDER)}
    return sorted(
        jobs,
        key=lambda job: (
            order.get(str(job.get("source_id") or ""), len(order)),
            str(job.get("source_id") or ""),
        ),
    )


def _parse_batch_manual_page_selection_payload(text: str) -> tuple[list[dict[str, object]], str, dict[str, object]]:
    stripped = text.strip()
    if not stripped:
        raise ValueError("La seleccion batch de paginas esta vacia.")

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError("La seleccion batch debe ser JSON valido.") from exc

    batch_notes = ""
    rundown_intro: dict[str, object] = {}
    raw_entries: object
    if isinstance(payload, dict):
        if isinstance(payload.get("notes"), str):
            batch_notes = payload["notes"].strip()
        if isinstance(payload.get("rundown_intro"), dict):
            raw_intro = payload["rundown_intro"]
            rundown_intro = {
                "speech": " ".join(str(raw_intro.get("speech") or "").split()).strip(),
                "date_reference": " ".join(str(raw_intro.get("date_reference") or "").split()).strip(),
                "source_scope": " ".join(str(raw_intro.get("source_scope") or "").split()).strip(),
                "why_it_fits": " ".join(str(raw_intro.get("why_it_fits") or "").split()).strip(),
            }
        raw_entries = (
            payload.get("jobs")
            or payload.get("selections")
            or payload.get("entries")
            or payload.get("items")
            or []
        )
    elif isinstance(payload, list):
        raw_entries = payload
    else:
        raise ValueError("La seleccion batch debe ser una lista JSON o un objeto con `jobs`.")

    if not isinstance(raw_entries, list) or not raw_entries:
        raise ValueError("La seleccion batch debe incluir una lista no vacia en `jobs` o similar.")

    entries: list[dict[str, object]] = []
    for raw_entry in raw_entries:
        if not isinstance(raw_entry, dict):
            continue
        job_manifest_path = str(
            raw_entry.get("job_manifest_path")
            or raw_entry.get("job_manifest")
            or raw_entry.get("manifest_path")
            or ""
        ).strip()
        if not job_manifest_path:
            raise ValueError(
                "Cada entrada batch debe incluir `job_manifest_path`, `job_manifest` o `manifest_path`."
            )
        items_payload = {
            "notes": str(raw_entry.get("notes") or "").strip(),
            "items": raw_entry.get("items") or raw_entry.get("candidates") or raw_entry.get("pages") or [],
        }
        entries.append(
            {
                "job_manifest_path": job_manifest_path,
                "job_id": str(raw_entry.get("job_id") or "").strip(),
                "newspaper_name": str(raw_entry.get("newspaper_name") or "").strip(),
                "provider": str(raw_entry.get("provider") or "").strip(),
                "selection_payload": json.dumps(items_payload, ensure_ascii=False),
            }
        )

    if not entries:
        raise ValueError("No se encontraron entradas validas en la seleccion batch.")
    return entries, batch_notes, rundown_intro


def extract_and_classify_job(
    *,
    job_manifest_path: Path,
    editorial_policy_path: Path,
    ocr_engine: str = "manual",
    ocr_scope: str = "front_page",
    ocr_dir: Path | None = None,
    ocr_text: str | None = None,
    ocr_text_file: Path | None = None,
    ocr_confidence: float | None = None,
) -> Path:
    project_dir = get_project_dir()
    job = read_json(job_manifest_path)
    policy = read_json(editorial_policy_path)
    raw_text, ocr_file_path, ocr_sources = _load_ocr_text(
        job_manifest_path=job_manifest_path,
        ocr_engine=ocr_engine,
        ocr_scope=ocr_scope,
        ocr_dir=ocr_dir,
        ocr_text=ocr_text,
        ocr_text_file=ocr_text_file,
    )
    lines = _normalize_text_lines(raw_text)
    blocks = _split_ocr_blocks(raw_text)
    headline_candidates = _select_headline_candidates(lines)
    heuristics = policy.get("heuristics", {})
    ad_keywords = heuristics.get("ad_keywords", [])
    news_keywords = heuristics.get("news_keywords", [])
    priority_keywords = heuristics.get("priority_keywords", {})

    ad_blocks = [line for line in lines if _contains_any(line, ad_keywords)]
    inferred_confidence = (
        ocr_confidence
        if ocr_confidence is not None
        else min(0.98, 0.45 + (0.08 * len(headline_candidates)) + (0.02 * min(len(lines), 10)))
    )

    combined_text = " ".join(lines)
    ad_score = _count_matches(combined_text, ad_keywords)
    news_score = _count_matches(combined_text, news_keywords) + len(headline_candidates)
    min_requirements = policy.get("minimum_requirements", {})
    min_confidence = float(min_requirements.get("min_ocr_confidence", 0.65))
    min_headlines = int(min_requirements.get("min_headline_candidates", 1))

    if inferred_confidence < min_confidence:
        is_news = False
        reason = "ocr_confidence_below_threshold"
    elif len(headline_candidates) < min_headlines:
        is_news = False
        reason = "headline_area_missing"
    elif ad_score > news_score:
        is_news = False
        reason = "image_is_mostly_advertising"
    else:
        is_news = True
        reason = "main_headline_detected"

    priority = "low"
    if _contains_any(combined_text, priority_keywords.get("high", [])):
        priority = "high"
    elif _contains_any(combined_text, priority_keywords.get("medium", [])):
        priority = "medium"
    elif is_news:
        priority = "medium"

    ocr_roles_used = [str(source.get("role") or source.get("source_kind") or "ocr") for source in ocr_sources]
    unique_ocr_roles_used = list(dict.fromkeys(ocr_roles_used))

    job["extraction"] = {
        "ocr_blocks": blocks,
        "headline_candidates": headline_candidates,
        "ad_blocks": ad_blocks,
        "confidence": round(inferred_confidence, 3),
        "ocr_text_path": (
            ocr_file_path.resolve().relative_to(project_dir).as_posix()
            if ocr_file_path and ocr_file_path.exists()
            else None
        ),
        "ocr_sources": ocr_sources,
        "ocr_source_roles": unique_ocr_roles_used,
        "ocr_engine": ocr_engine,
        "ocr_scope": ocr_scope,
    }
    job["classification"] = {
        "is_news": is_news,
        "priority": priority,
        "reason": reason,
    }
    job["status"] = "classified" if is_news else "failed"
    timestamp = datetime.now().isoformat(timespec="seconds")
    job["audit"]["updated_at"] = timestamp
    job["audit"].setdefault("events", []).append(
        {
            "stage": "extract_classify",
            "status": "completed",
            "timestamp": timestamp,
            "details": (
                f"Extraidos {len(blocks)} bloques OCR, {len(headline_candidates)} titulares candidatos "
                f"y {len(ocr_sources)} fuente(s) OCR."
            ),
        }
    )
    return write_json(job_manifest_path, job)


def analyze_cover_page_references_for_job(
    *,
    job_manifest_path: Path,
    max_candidates: int = 6,
    force: bool = False,
) -> Path:
    project_dir = get_project_dir()
    job = read_json(job_manifest_path)
    extraction = job.get("extraction", {})
    current_candidates = list(job.get("page_selection", {}).get("candidates", []))
    if current_candidates and not force:
        raise ValueError(
            "El job ya tiene `page_selection.candidates`. Usa `--force` si quieres recalcularlas."
        )

    ocr_blocks = extraction.get("ocr_blocks", [])
    lines = [str(block.get("text") or "").strip() for block in ocr_blocks if str(block.get("text") or "").strip()]
    if not lines:
        raise ValueError(
            "El job no tiene `extraction.ocr_blocks`. Ejecuta `extract-job` antes de analizar referencias de portada."
        )

    candidates = _extract_page_candidates_from_cover(lines)[:max_candidates]
    page_numbers = sorted(dict.fromkeys(int(candidate["page_number"]) for candidate in candidates))
    status = "suggested" if candidates else "needs_manual_review"
    notes = (
        "Referencias detectadas automaticamente desde OCR de portada."
        if candidates
        else "El OCR local no encontro referencias claras de pagina. Usa importacion manual."
    )

    timestamp = datetime.now().isoformat(timespec="seconds")
    job["page_selection"] = {
        "strategy": "cover_first",
        "provider": "local_ocr_regex",
        "status": status,
        "selected_page_numbers": page_numbers,
        "candidates": candidates,
        "stories": _build_cover_story_groups(candidates),
        "notes": notes,
    }
    job["audit"]["updated_at"] = timestamp
    job["audit"].setdefault("events", []).append(
        {
            "stage": "cover_page_selection",
            "status": "completed" if candidates else "needs_manual_review",
            "timestamp": timestamp,
            "details": f"Se detectaron {len(page_numbers)} pagina(s) candidata(s) desde la portada.",
        }
    )
    return write_json(job_manifest_path, job)


def import_cover_page_selection_for_job(
    *,
    job_manifest_path: Path,
    selection_text: str | None = None,
    selection_file: Path | None = None,
    provider: str = "chatgpt_plus_manual",
    force: bool = False,
) -> Path:
    job = read_json(job_manifest_path)
    current_candidates = list(job.get("page_selection", {}).get("candidates", []))
    if current_candidates and not force:
        raise ValueError(
            "El job ya tiene una seleccion de paginas. Usa `--force` si quieres reemplazarla."
        )

    if selection_file is not None:
        if not selection_file.exists():
            raise FileNotFoundError(f"No existe el archivo de seleccion: {selection_file}")
        raw_selection = selection_file.read_text(encoding="utf-8")
    elif selection_text is not None:
        raw_selection = selection_text
    else:
        raise ValueError("Debes proporcionar `--selection-text` o `--selection-file`.")

    candidates, notes = _parse_manual_page_selection_payload(raw_selection)
    page_numbers = sorted(dict.fromkeys(int(candidate["page_number"]) for candidate in candidates))
    timestamp = datetime.now().isoformat(timespec="seconds")
    job["page_selection"] = {
        "strategy": "cover_first",
        "provider": provider,
        "status": "approved_manual",
        "selected_page_numbers": page_numbers,
        "candidates": candidates,
        "stories": _build_cover_story_groups(candidates),
        "notes": notes or "Selección importada manualmente.",
    }
    job["audit"]["updated_at"] = timestamp
    job["audit"].setdefault("events", []).append(
        {
            "stage": "cover_page_selection_import",
            "status": "completed",
            "timestamp": timestamp,
            "details": f"Se importaron {len(page_numbers)} pagina(s) desde seleccion manual.",
        }
    )
    return write_json(job_manifest_path, job)


def import_cover_page_selection_batch(
    *,
    selection_text: str | None = None,
    selection_file: Path | None = None,
    provider: str = "chatgpt_plus_manual",
    force: bool = False,
) -> list[dict[str, object]]:
    project_dir = get_project_dir()
    if selection_file is not None:
        if not selection_file.exists():
            raise FileNotFoundError(f"No existe el archivo de seleccion batch: {selection_file}")
        raw_selection = selection_file.read_text(encoding="utf-8")
    elif selection_text is not None:
        raw_selection = selection_text
    else:
        raise ValueError("Debes proporcionar `--selection-text` o `--selection-file`.")

    entries, batch_notes, rundown_intro = _parse_batch_manual_page_selection_payload(raw_selection)
    results: list[dict[str, object]] = []
    for entry in entries:
        manifest_value = Path(str(entry["job_manifest_path"]))
        manifest_path = (
            manifest_value
            if manifest_value.is_absolute()
            else (project_dir / manifest_value).resolve()
        )
        resolved_provider = str(entry.get("provider") or provider)
        import_cover_page_selection_for_job(
            job_manifest_path=manifest_path,
            selection_text=str(entry["selection_payload"]),
            provider=resolved_provider,
            force=force,
        )
        if str(rundown_intro.get("speech") or "").strip():
            job = read_json(manifest_path)
            timestamp = datetime.now().isoformat(timespec="seconds")
            job["rundown_intro"] = {
                **rundown_intro,
                "provider": resolved_provider,
                "source": "cover_batch_prompt",
                "imported_at": timestamp,
            }
            job.setdefault("audit", {}).setdefault("events", []).append(
                {
                    "stage": "rundown_intro_import",
                    "status": "completed",
                    "timestamp": timestamp,
                    "details": "Intro dinamica importada desde el prompt de portadas.",
                }
            )
            job.setdefault("audit", {})["updated_at"] = timestamp
            write_json(manifest_path, job)
        results.append(
            {
                "job_manifest_path": manifest_path.resolve().relative_to(project_dir).as_posix(),
                "job_id": entry.get("job_id") or "",
                "newspaper_name": entry.get("newspaper_name") or "",
                "provider": resolved_provider,
                "status": "imported",
                "batch_notes": batch_notes,
                "rundown_intro": bool(str(rundown_intro.get("speech") or "").strip()),
            }
        )
    return results


def import_story_narrative_for_job(
    *,
    job_manifest_path: Path,
    narrative_text: str | None = None,
    narrative_file: Path | None = None,
    provider: str = "chatgpt_plus_manual",
    force: bool = False,
) -> Path:
    project_dir = get_project_dir()
    job = read_json(job_manifest_path)
    current_stories = list(job.get("story_narrative", {}).get("stories", []))
    if current_stories and not force:
        raise ValueError(
            "El job ya tiene historias editoriales importadas. Usa `--force` si quieres reemplazarlas."
        )

    if narrative_file is not None:
        if not narrative_file.exists():
            raise FileNotFoundError(f"No existe el archivo editorial: {narrative_file}")
        raw_narrative = narrative_file.read_text(encoding="utf-8")
    elif narrative_text is not None:
        raw_narrative = narrative_text
    else:
        raise ValueError("Debes proporcionar `--narrative-text` o `--narrative-file`.")

    imported_stories, notes = _parse_story_narrative_payload(raw_narrative)
    cover_stories = list(job.get("page_selection", {}).get("stories", []))
    merged_stories = _merge_story_narrative_with_cover_context(
        cover_stories=cover_stories,
        imported_stories=imported_stories,
        project_dir=project_dir,
    )
    speech_script = _build_script_from_story_speeches(merged_stories)
    timestamp = datetime.now().isoformat(timespec="seconds")
    job["story_narrative"] = {
        "provider": provider,
        "status": "approved_manual",
        "source": "supporting_pages_manual",
        "stories": merged_stories,
        "notes": notes or "Speeches editoriales importados manualmente.",
    }
    if speech_script:
        job["script"] = {
            **job.get("script", {}),
            "draft": speech_script,
            "approved_text": speech_script,
            "review_notes": "Speeches importados desde ChatGPT y aprobados para voz/subtitulos.",
            "inputs": {
                **job.get("script", {}).get("inputs", {}),
                "story_narrative_source": "story_narrative.stories",
                "story_count": len(merged_stories),
            },
        }
        job["status"] = "scripted"
    _sync_story_narrative_manifest(job=job, job_manifest_path=job_manifest_path)
    job["audit"]["updated_at"] = timestamp
    job["audit"].setdefault("events", []).append(
        {
            "stage": "story_narrative_import",
            "status": "completed",
            "timestamp": timestamp,
            "details": f"Se importaron {len(merged_stories)} speech(es) editoriales.",
        }
    )
    return write_json(job_manifest_path, job)


def import_story_narrative_batch(
    *,
    narrative_text: str | None = None,
    narrative_file: Path | None = None,
    provider: str = "chatgpt_plus_manual",
    force: bool = False,
) -> list[dict[str, object]]:
    project_dir = get_project_dir()
    if narrative_file is not None:
        if not narrative_file.exists():
            raise FileNotFoundError(f"No existe el archivo editorial batch: {narrative_file}")
        raw_narrative = narrative_file.read_text(encoding="utf-8")
    elif narrative_text is not None:
        raw_narrative = narrative_text
    else:
        raise ValueError("Debes proporcionar `--narrative-text` o `--narrative-file`.")

    entries, batch_notes = _parse_batch_story_narrative_payload(raw_narrative)
    results: list[dict[str, object]] = []
    job_manifest_paths = list(get_jobs_root(project_dir).glob("*/*/job-manifest.json"))
    manifest_by_job_id = {
        read_json(path).get("job_id"): path
        for path in job_manifest_paths
    }

    for entry in entries:
        job_id = str(entry.get("job_id") or "")
        manifest_path = manifest_by_job_id.get(job_id)
        if manifest_path is None:
            raise FileNotFoundError(f"No se encontro job-manifest para `job_id={job_id}`.")
        resolved_provider = str(entry.get("provider") or provider)
        import_story_narrative_for_job(
            job_manifest_path=manifest_path,
            narrative_text=json.dumps(
                {
                    "notes": entry.get("notes") or "",
                    "stories": entry.get("stories") or [],
                },
                ensure_ascii=False,
            ),
            provider=resolved_provider,
            force=force,
        )
        results.append(
            {
                "job_manifest_path": manifest_path.resolve().relative_to(project_dir).as_posix(),
                "job_id": job_id,
                "newspaper_name": entry.get("newspaper_name") or "",
                "provider": resolved_provider,
                "status": "imported",
                "batch_notes": batch_notes,
            }
        )
    return results


def scrape_selected_pages_for_job(
    *,
    job_manifest_path: Path,
    source_config_path: Path,
    force: bool = False,
) -> Path:
    project_dir = get_project_dir()
    job = read_json(job_manifest_path)
    source = SourceConfig.load(source_config_path)
    page_selection = job.get("page_selection", {})
    selected_page_numbers = [
        int(page_number)
        for page_number in page_selection.get("selected_page_numbers", [])
        if int(page_number) > 1
    ]
    if not selected_page_numbers:
        raise ValueError(
            "El job no tiene `page_selection.selected_page_numbers`. Analiza o importa primero las referencias de portada."
        )

    existing_pages = [
        page
        for page in job.get("input_assets", {}).get("pages", [])
        if int(page.get("page_number") or 0) > 1
    ]
    if existing_pages and not force:
        raise ValueError(
            "El job ya tiene paginas de apoyo descargadas. Usa `--force` si quieres reemplazarlas."
        )

    if existing_pages and force:
        for page in existing_pages:
            local_path_value = page.get("local_path")
            local_path = _resolve_repo_path(str(local_path_value)) if local_path_value else None
            if local_path and local_path.exists():
                local_path.unlink()

    if str(source.discovery.get("type", "")).strip() != "prcdn_image_sequence":
        raise ValueError(
            "La descarga selectiva de paginas esta soportada por ahora solo para fuentes `prcdn_image_sequence`."
        )

    resolved = resolve_prcdn_pages(
        source=source,
        job_date=str(job.get("date")),
        page_numbers=selected_page_numbers,
    )
    if resolved.get("status") == "no_publication_for_date":
        raise ValueError("La fuente no tiene edicion publicada para la fecha solicitada.")

    job_dir = job_manifest_path.parent
    selected_pages = []
    for page in resolved.get("pages", []):
        page_number = int(page.get("page_number") or 0)
        if page_number <= 1:
            continue
        page_url = str(page.get("source_url") or "")
        if not page_url:
            continue
        staged = stage_supporting_page_asset(
            job_dir=job_dir,
            page_number=page_number,
            page_image=None,
            page_url=page_url,
            download_page=True,
        )
        if staged is None:
            continue
        selected_pages.append(
            {
                "role": "supporting_page",
                "label": str(page.get("label") or f"Pagina {page_number}"),
                "page_number": page_number,
                "source_url": page_url,
                "local_path": staged.resolve().relative_to(project_dir).as_posix(),
            }
        )

    input_assets = dict(job.get("input_assets", {}))
    front_page_entry = next(
        (
            page
            for page in input_assets.get("pages", [])
            if int(page.get("page_number") or 0) == 1
        ),
        None,
    )
    pages = [front_page_entry] if front_page_entry else []
    pages.extend(selected_pages)
    input_assets["pages"] = pages
    job["input_assets"] = input_assets

    page_selection["downloaded_page_numbers"] = [page["page_number"] for page in selected_pages]
    page_selection["status"] = "downloaded" if selected_pages else page_selection.get("status", "suggested")
    job["page_selection"] = page_selection

    timestamp = datetime.now().isoformat(timespec="seconds")
    job["status"] = "scraped"
    job["audit"]["updated_at"] = timestamp
    job["audit"].setdefault("events", []).append(
        {
            "stage": "scrape_selected_pages",
            "status": "completed",
            "timestamp": timestamp,
            "details": f"Se descargaron {len(selected_pages)} pagina(s) seleccionadas desde la portada.",
        }
    )
    return write_json(job_manifest_path, job)


def _format_source_name(source_id: str) -> str:
    return source_id.replace("-", " ").title()


def _normalize_sentence(text: str) -> str:
    clean = " ".join(text.split()).strip(" .")
    if not clean:
        return ""
    return clean[0].upper() + clean[1:]


def _trim_sentence(text: str, max_chars: int = 150) -> str:
    normalized = _normalize_sentence(text)
    if len(normalized) <= max_chars:
        return normalized


def _headline_similarity_score(left: str, right: str) -> float:
    left_clean = _clean_cover_headline(left).casefold()
    right_clean = _clean_cover_headline(right).casefold()
    if not left_clean or not right_clean:
        return 0.0
    if left_clean == right_clean:
        return 1.0

    left_tokens = {token for token in re.split(r"[^a-z0-9áéíóúñ]+", left_clean) if len(token) >= 3}
    right_tokens = {token for token in re.split(r"[^a-z0-9áéíóúñ]+", right_clean) if len(token) >= 3}
    if not left_tokens or not right_tokens:
        return 0.0

    overlap = len(left_tokens & right_tokens)
    if overlap == 0:
        return 0.0
    return overlap / max(len(left_tokens), len(right_tokens))


def _find_best_cover_story_match(
    *,
    imported_story: dict[str, object],
    cover_stories: list[dict[str, object]],
    used_indexes: set[int] | None = None,
) -> dict[str, object]:
    used_indexes = used_indexes or set()
    headline = str(imported_story.get("headline") or "").strip()
    imported_pages = set(_normalize_story_page_numbers(imported_story.get("page_numbers")))
    best_index = -1
    best_score = -1.0

    for index, cover_story in enumerate(cover_stories):
        if index in used_indexes:
            continue
        score = _headline_similarity_score(headline, str(cover_story.get("headline") or ""))
        cover_pages = set(_normalize_story_page_numbers(cover_story.get("page_numbers")))
        if imported_pages and cover_pages:
            page_overlap = len(imported_pages & cover_pages)
            if page_overlap:
                score += 1.5 + page_overlap * 0.1
        elif imported_pages and not cover_pages:
            score += 0.0
        if score > best_score:
            best_score = score
            best_index = index

    if best_index >= 0 and best_score > 0:
        used_indexes.add(best_index)
        return cover_stories[best_index]

    for index, cover_story in enumerate(cover_stories):
        if index in used_indexes:
            continue
        used_indexes.add(index)
        return cover_story

    return {}
    trimmed = normalized[: max_chars - 1].rstrip(" ,;:")
    last_space = trimmed.rfind(" ")
    if last_space > 50:
        trimmed = trimmed[:last_space]
    return trimmed.rstrip(" ,;:") + "..."


def _choose_supporting_line(candidates: list[str]) -> str:
    if len(candidates) < 2:
        return ""
    return _trim_sentence(candidates[1], max_chars=120)


def _build_anchor_script(*, source_name: str, headline: str, supporting_line: str) -> str:
    opening = f"Abrimos con la portada de {source_name}."
    main_sentence = _trim_sentence(headline, max_chars=155)
    if supporting_line:
        closing = f"El foco de esta portada apunta a {supporting_line[:1].lower() + supporting_line[1:]}."
    else:
        closing = "Enseguida revisamos el desarrollo de esta portada con un resumen breve y claro."
    script = " ".join(
        part for part in [opening, main_sentence + ".", closing] if part
    )
    return script.replace("..", ".")


def generate_script_from_job(
    *,
    job_manifest_path: Path,
    script_template_path: Path,
    force: bool = False,
) -> Path:
    job = read_json(job_manifest_path)
    if job.get("classification", {}).get("is_news") is not True:
        raise ValueError(
            "El job no esta clasificado como noticia. Ejecuta `extract-job` y valida la clasificacion antes de generar guion."
        )

    current_draft = job.get("script", {}).get("draft", "")
    if current_draft and not force:
        raise ValueError(
            "El job ya tiene `script.draft`. Usa `--force` si quieres regenerarlo."
        )

    template = read_json(script_template_path)
    headline_candidates = job.get("extraction", {}).get("headline_candidates", [])
    if not headline_candidates:
        raise ValueError(
            "El job no tiene `extraction.headline_candidates`; no se puede construir el guion."
        )

    source_name = _format_source_name(job["source_id"])
    primary_headline = headline_candidates[0]
    supporting_line = _choose_supporting_line(headline_candidates)
    draft = _build_anchor_script(
        source_name=source_name,
        headline=primary_headline,
        supporting_line=supporting_line,
    )

    timestamp = datetime.now().isoformat(timespec="seconds")
    job["script"] = {
        **job.get("script", {}),
        "template_id": template["template_id"],
        "draft": draft,
        "approved_text": job.get("script", {}).get("approved_text", ""),
        "review_notes": job.get("script", {}).get("review_notes", ""),
        "inputs": {
            "source_name": source_name,
            "headline_candidates": headline_candidates,
            "structure": template.get("structure", []),
        },
    }
    job["status"] = "review_pending" if job.get("approval_mode") != "full_auto" else "scripted"
    job["audit"]["updated_at"] = timestamp
    job["audit"].setdefault("events", []).append(
        {
            "stage": "script",
            "status": "completed",
            "timestamp": timestamp,
            "details": "Draft de narracion generado desde titulares extraidos.",
        }
    )
    return write_json(job_manifest_path, job)


def approve_script_for_job(
    *,
    job_manifest_path: Path,
    approved_text: str | None = None,
    review_notes: str | None = None,
) -> Path:
    job = read_json(job_manifest_path)
    draft = job.get("script", {}).get("draft", "").strip()
    final_text = (approved_text or draft).strip()
    if not final_text:
        raise ValueError(
            "No hay texto para aprobar. Genera primero `script.draft` o pasa `--approved-text`."
        )

    timestamp = datetime.now().isoformat(timespec="seconds")
    existing_notes = job.get("script", {}).get("review_notes", "")
    merged_notes = review_notes if review_notes is not None else existing_notes
    job["script"] = {
        **job.get("script", {}),
        "approved_text": final_text,
        "review_notes": merged_notes,
    }
    job["status"] = "approved"
    job["audit"]["updated_at"] = timestamp
    job["audit"].setdefault("events", []).append(
        {
            "stage": "review",
            "status": "approved",
            "timestamp": timestamp,
            "details": "Guion aprobado para continuar con voice/subtitle/compose.",
        }
    )
    return write_json(job_manifest_path, job)


def _get_wav_duration_seconds(audio_path: Path) -> float:
    with wave.open(str(audio_path), "rb") as wav_file:
        frame_count = wav_file.getnframes()
        frame_rate = wav_file.getframerate()
        if frame_rate <= 0:
            raise ValueError(f"No se pudo calcular la duracion WAV de {audio_path}")
        return frame_count / frame_rate


def _select_subtitle_source_text(*, job: dict, subtitle_policy: dict) -> tuple[str, str]:
    strategy = str(subtitle_policy.get("timing_strategy", "text_weighted_fallback"))
    transcription_text = str(job.get("transcription", {}).get("text", "")).strip()
    approved_text = str(job.get("script", {}).get("approved_text", "")).strip()

    if "aligned_preferred" in strategy and transcription_text:
        return transcription_text, "transcription"
    if approved_text:
        return approved_text, "approved_script"
    if transcription_text:
        return transcription_text, "transcription"
    return "", "missing"


def _safe_build_subtitle_segments(
    text: str,
    *,
    total_duration: float,
    max_chars: int,
    max_lines: int,
    min_seconds: float,
):
    params = inspect.signature(build_subtitle_segments).parameters
    kwargs = {
        "total_duration": total_duration,
        "max_chars": max_chars,
        "min_seconds": min_seconds,
    }
    if "max_lines" in params:
        kwargs["max_lines"] = max_lines
    return build_subtitle_segments(text, **kwargs)


def _build_rundown_subtitle_segments(
    *,
    segment_specs: list[dict[str, object]],
    subtitle_policy: dict,
    project_dir: Path,
) -> tuple[str, list[dict[str, object]], float]:
    full_text = "\n\n".join(str(segment.get("text") or "").strip() for segment in segment_specs if str(segment.get("text") or "").strip())
    subtitle_segments: list[dict[str, object]] = []
    cursor = 0.0

    for segment in segment_specs:
        segment_text = str(segment.get("text") or "").strip()
        segment_audio_file = str(segment.get("segment_audio_file") or "").strip()
        if not segment_text or not segment_audio_file:
            continue

        segment_audio_path = project_dir / segment_audio_file
        segment_duration = _get_wav_duration_seconds(segment_audio_path)
        segment_subtitles = _safe_build_subtitle_segments(
            segment_text,
            total_duration=segment_duration,
            max_chars=int(subtitle_policy.get("max_chars_per_block", 72)),
            max_lines=int(subtitle_policy.get("max_lines", 2)),
            min_seconds=float(subtitle_policy.get("min_segment_seconds", 1.4)),
        )
        for subtitle in segment_subtitles:
            subtitle_segments.append(
                {
                    "text": subtitle.text,
                    "start": round(cursor + subtitle.start, 3),
                    "end": round(cursor + subtitle.end, 3),
                }
            )
        cursor += segment_duration

    return full_text, subtitle_segments, round(cursor, 3)


def _build_daily_rundown_segment_specs(
    *,
    jobs: list[dict[str, object]],
    voice_profile_path: Path,
    project_dir: Path,
) -> list[dict[str, object]]:
    fallback_voice = VoiceProfile.load(voice_profile_path)
    presenter_visual = _resolve_voice_profile_for_narrator(
        narrator_profile_id=_get_presenter_narrator_profile_id(project_dir=project_dir),
        fallback_voice_profile_path=voice_profile_path,
        project_dir=project_dir,
    )
    first_cover = str(jobs[0]["input_assets"]["front_page_image"])
    source_names = [_format_source_name(str(job.get("source_id") or "")) for job in jobs]
    story_count = sum(
        1
        for job in jobs
        for story in job.get("story_narrative", {}).get("stories", [])
        if str(story.get("speech") or story.get("summary") or "").strip()
    )
    intro_text = _select_imported_rundown_intro(jobs)
    if not intro_text:
        intro_text = _build_rundown_intro(
            job_date=str(jobs[0].get("date") or ""),
            source_names=source_names,
            story_count=story_count,
        )
    segment_specs: list[dict[str, object]] = [
        {
            "newspaper_name": "Resumen de Portadas",
            "cover": first_cover,
            "headline": _format_spanish_date(str(jobs[0].get("date") or "")),
            "story_type": "intro",
            "segment_type": "intro",
            "narrator_profile_id": "presentador",
            "voice_profile_id": presenter_visual.profile_id,
            "narrator_name": presenter_visual.narrator_name,
            "gestures_dir": presenter_visual.gestures_dir,
            "text": intro_text,
            "cover_region": None,
        }
    ]
    for job in jobs:
        source_name = _format_source_name(str(job.get("source_id") or ""))
        cover = str(job["input_assets"]["front_page_image"])
        story_items = _enrich_job_story_narrative_with_cover_context(job)
        segment_specs.append(
            {
                "newspaper_name": source_name,
                "cover": cover,
                "headline": f"Paso a {source_name}",
                "story_type": "connector",
                "segment_type": "connector",
                "narrator_profile_id": "presentador",
                "voice_profile_id": presenter_visual.profile_id,
                "narrator_name": presenter_visual.narrator_name,
                "gestures_dir": presenter_visual.gestures_dir,
                "text": _build_newspaper_connector_text(source_name, story_count=len(story_items)),
                "cover_region": None,
            }
        )
        for story in story_items:
            speech = " ".join(str(story.get("speech") or story.get("summary") or "").split()).strip()
            visual_voice = _resolve_voice_profile_for_narrator(
                narrator_profile_id=story.get("narrator_profile_id"),
                fallback_voice_profile_path=voice_profile_path,
                project_dir=project_dir,
            )
            segment_specs.append(
                {
                    "newspaper_name": source_name,
                    "cover": cover,
                    "headline": story.get("headline") or "",
                    "story_type": story.get("story_type") or "actualidad",
                    "segment_type": "story",
                    "narrator_profile_id": story.get("narrator_profile_id") or "",
                    "voice_profile_id": visual_voice.profile_id,
                    "narrator_name": visual_voice.narrator_name,
                    "gestures_dir": visual_voice.gestures_dir,
                    "text": speech,
                    "cover_region": story.get("cover_region"),
                }
            )
    _ = fallback_voice
    return segment_specs


def _rundown_segment_reuse_key(segment: dict[str, object]) -> tuple[str, ...]:
    return (
        str(segment.get("segment_type") or ""),
        str(segment.get("newspaper_name") or ""),
        str(segment.get("headline") or ""),
        str(segment.get("story_type") or ""),
        str(segment.get("narrator_profile_id") or ""),
        " ".join(str(segment.get("text") or "").split()).strip(),
    )


def _copy_reusable_seed_audio_segments(
    *,
    segment_specs: list[dict[str, object]],
    audio_dir: Path,
    seed_rundown_dir: Path | None,
    project_dir: Path,
    emit,
) -> dict[int, Path]:
    if seed_rundown_dir is None:
        return {}
    seed_dir = seed_rundown_dir if seed_rundown_dir.is_absolute() else (project_dir / seed_rundown_dir).resolve()
    story_manifest_path = seed_dir / "story-manifest.json"
    if not story_manifest_path.exists():
        emit("reuse", f"No se encontro story-manifest en la corrida semilla: {seed_dir.relative_to(project_dir).as_posix()}.")
        return {}
    existing_manifest = read_json(story_manifest_path)
    existing_segments = [segment for segment in existing_manifest.get("segments", []) if isinstance(segment, dict)]
    reusable: dict[int, Path] = {}
    for index, segment in enumerate(segment_specs, start=1):
        if index > len(existing_segments):
            break
        existing_segment = existing_segments[index - 1]
        if _rundown_segment_reuse_key(existing_segment) != _rundown_segment_reuse_key(segment):
            break
        existing_audio_value = str(existing_segment.get("segment_audio_file") or "").strip()
        if not existing_audio_value:
            break
        existing_audio_path = project_dir / existing_audio_value
        if not existing_audio_path.exists():
            break
        target_audio_path = audio_dir / f"segment-{index:02d}.wav"
        shutil.copy2(existing_audio_path, target_audio_path)
        reusable[index] = target_audio_path
    if reusable:
        emit(
            "reuse",
            f"Se reutilizaran {len(reusable)} audio(s) desde {seed_dir.relative_to(project_dir).as_posix()}.",
        )
    else:
        emit("reuse", "No hubo segmentos iniciales coincidentes para reutilizar audio.")
    return reusable


def generate_voice_and_subtitles_for_job(
    *,
    job_manifest_path: Path,
    voice_profile_path: Path,
    subtitle_policy_path: Path,
    audio_file: Path | None = None,
    force: bool = False,
) -> Path:
    project_dir = get_project_dir()
    job = read_json(job_manifest_path)
    fallback_voice = VoiceProfile.load(voice_profile_path)
    subtitle_policy = read_json(subtitle_policy_path)
    narrative_stories = _enrich_job_story_narrative_with_cover_context(job)
    approved_text = job.get("script", {}).get("approved_text", "").strip()
    if narrative_stories:
        approved_text = _build_script_from_story_speeches(narrative_stories)
    if not approved_text:
        raise ValueError(
            "El job no tiene `script.approved_text`. Aprueba primero el guion antes de generar voz y subtitulos."
        )

    current_audio = job.get("voice", {}).get("audio_path")
    current_segments = job.get("subtitles", {}).get("segments_path")
    if (current_audio or current_segments) and not force:
        raise ValueError(
            "El job ya tiene audio o subtitulos generados. Usa `--force` si quieres regenerarlos."
        )

    job_dir = job_manifest_path.parent
    output_dir = job_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_path = output_dir / "narration.wav"
    subtitle_segments_path = output_dir / "subtitle-segments.json"

    generated_segments: list[dict[str, object]] = []
    if narrative_stories:
        segment_audio_paths: list[Path] = []
        for index, story in enumerate(narrative_stories, start=1):
            speech = " ".join(str(story.get("speech") or story.get("summary") or "").split()).strip()
            if not speech:
                continue
            segment_voice = _resolve_tts_profile_for_narrator(
                narrator_profile_id=story.get("narrator_profile_id"),
                fallback_voice_profile_path=voice_profile_path,
                project_dir=project_dir,
            )
            segment_audio_path = output_dir / f"narration-segment-{index:02d}.wav"
            generate_voice_track(
                text=speech,
                provider=segment_voice.tts_provider,
                output_path=segment_audio_path,
                audio_file=None,
                voice=segment_voice.tts_voice,
                language=segment_voice.language,
                provider_settings=segment_voice.provider_settings,
            )
            segment_audio_paths.append(segment_audio_path)
            generated_segments.append(
                {
                    "index": index,
                    "headline": story.get("headline") or "",
                    "story_type": story.get("story_type") or "actualidad",
                    "narrator_profile_id": story.get("narrator_profile_id") or "",
                    "voice_profile_id": segment_voice.profile_id,
                    "narrator_name": segment_voice.narrator_name,
                    "audio_path": segment_audio_path.resolve().relative_to(project_dir).as_posix(),
                    "text": speech,
                }
            )
        concatenate_wav_files(segment_audio_paths, audio_path)
    else:
        generate_voice_track(
            text=approved_text,
            provider=fallback_voice.tts_provider,
            output_path=audio_path,
            audio_file=audio_file,
            voice=fallback_voice.tts_voice,
            language=fallback_voice.language,
            provider_settings=fallback_voice.provider_settings,
        )
    total_duration = _get_wav_duration_seconds(audio_path)
    subtitle_text, subtitle_text_source = _select_subtitle_source_text(
        job=job,
        subtitle_policy=subtitle_policy,
    )
    if not subtitle_text:
        raise ValueError(
            "No se encontro texto para subtitulos. Genera o importa un guion, o ejecuta `transcribe-job`."
        )
    segments = _safe_build_subtitle_segments(
        subtitle_text,
        total_duration=total_duration,
        max_chars=int(subtitle_policy.get("max_chars_per_block", 72)),
        max_lines=int(subtitle_policy.get("max_lines", 2)),
        min_seconds=float(subtitle_policy.get("min_segment_seconds", 1.4)),
    )
    subtitle_payload = {
        "policy_id": subtitle_policy["policy_id"],
        "text_source": subtitle_text_source,
        "text": subtitle_text,
        "audio_duration_seconds": round(total_duration, 3),
        "segments": [
            {
                "text": segment.text,
                "start": round(segment.start, 3),
                "end": round(segment.end, 3),
            }
            for segment in segments
        ],
    }
    write_json(subtitle_segments_path, subtitle_payload)

    timestamp = datetime.now().isoformat(timespec="seconds")
    job["voice"] = {
        **job.get("voice", {}),
        "profile_id": fallback_voice.profile_id,
        "provider": fallback_voice.tts_provider,
        "tts_voice": fallback_voice.tts_voice,
        "language": fallback_voice.language,
        "provider_settings": fallback_voice.provider_settings,
        "audio_path": audio_path.resolve().relative_to(project_dir).as_posix(),
        "segments": generated_segments,
        "timestamps_path": None,
    }
    job["subtitles"] = {
        **job.get("subtitles", {}),
        "policy_id": subtitle_policy["policy_id"],
        "segments_path": subtitle_segments_path.resolve().relative_to(project_dir).as_posix(),
    }
    job["status"] = "subtitled"
    _sync_story_narrative_manifest(
        job=job,
        job_manifest_path=job_manifest_path,
        voice_profile_path=voice_profile_path,
    )
    job["audit"]["updated_at"] = timestamp
    job["audit"].setdefault("events", []).append(
        {
            "stage": "voice_subtitle",
            "status": "completed",
            "timestamp": timestamp,
            "details": f"Audio y {len(segments)} segmentos de subtitulo generados.",
        }
    )
    return write_json(job_manifest_path, job)


def build_story_manifest_from_job(
    *,
    job_manifest_path: Path,
    video_template_path: Path,
    voice_profile_path: Path,
    output_path: Path | None = None,
) -> Path:
    project_dir = get_project_dir()
    job = read_json(job_manifest_path)
    voice = VoiceProfile.load(voice_profile_path)
    video_template = VideoTemplate.load(video_template_path)
    story_id = job["job_id"]
    render_output = f"output/{story_id}.mp4"
    narrative_manifest = _build_story_narrative_manifest_payload(
        job=job,
        voice_profile_path=voice_profile_path,
        include_audio_segments=True,
    )
    narrative_stories = list(narrative_manifest.get("stories", []))
    approved_text = (
        _build_script_from_story_speeches(narrative_stories)
        if narrative_stories
        else job["script"].get("approved_text") or job["script"].get("draft")
    )
    if not approved_text:
        raise ValueError(
            "El job-manifest no tiene `script.approved_text` ni `script.draft`; no se puede construir el story-manifest."
        )

    front_page_image = job["input_assets"].get("front_page_image")
    if not front_page_image:
        raise ValueError(
            "El job-manifest no tiene `input_assets.front_page_image`; primero debes asociar o descargar la portada."
        )

    source_name = job["source_id"].replace("-", " ").title()
    if narrative_stories:
        manifest_segments = []
        for story in narrative_stories:
            segment_voice = _resolve_voice_profile_for_narrator(
                narrator_profile_id=story.get("narrator_profile_id"),
                fallback_voice_profile_path=voice_profile_path,
                project_dir=project_dir,
            )
            manifest_segments.append(
                {
                    "newspaper_name": source_name,
                    "cover": front_page_image,
                    "headline": story.get("headline") or "",
                    "story_type": story.get("story_type") or "actualidad",
                    "segment_type": story.get("segment_type") or "story",
                    "narrator_profile_id": story.get("narrator_profile_id") or "",
                    "narrator_role": story.get("narrator_role") or "",
                    "voice_profile_id": segment_voice.profile_id,
                    "narrator_name": segment_voice.narrator_name,
                    "gestures_dir": segment_voice.gestures_dir,
                    "text": str(story.get("speech") or story.get("summary") or "").strip(),
                    "page_numbers": story.get("page_numbers") or [],
                    "key_facts": story.get("key_facts") or [],
                    "tone_notes": story.get("tone_notes") or [],
                    "safety_notes": story.get("safety_notes") or "",
                    "cover_region": story.get("cover_region"),
                    "segment_audio_file": story.get("segment_audio_file"),
                    "audio_file": job["voice"].get("audio_path"),
                    "subtitle_segments_file": job["subtitles"].get("segments_path"),
                }
            )
    else:
        manifest_segments = [
            {
                "newspaper_name": source_name,
                "cover": front_page_image,
                "narrator_name": voice.narrator_name,
                "gestures_dir": voice.gestures_dir,
                "text": approved_text,
                "audio_file": job["voice"].get("audio_path"),
                "subtitle_segments_file": job["subtitles"].get("segments_path"),
            }
        ]

    narrative_manifest_path = _sync_story_narrative_manifest(
        job=job,
        job_manifest_path=job_manifest_path,
        voice_profile_path=voice_profile_path,
    )

    manifest = {
        "story_id": story_id,
        "video_template": video_template.template_id,
        "background": video_template.default_background,
        "music": video_template.default_music,
        "subtitle_policy": job["subtitles"]["policy_id"],
        "render_output": render_output,
        "story_narrative_manifest_path": narrative_manifest_path,
        "segments": manifest_segments,
    }

    target = output_path or job_manifest_path.with_name("story-manifest.json")
    written = write_json(target, manifest)

    job["video"]["story_manifest_path"] = written.resolve().relative_to(project_dir).as_posix()
    job["video"]["output_path"] = render_output
    job["audit"]["updated_at"] = datetime.now().isoformat(timespec="seconds")
    job["audit"].setdefault("events", []).append(
        {
            "stage": "compose",
            "status": "completed",
            "timestamp": job["audit"]["updated_at"],
            "details": "Story manifest generado desde job manifest.",
        }
    )
    write_json(job_manifest_path, job)
    return written


def build_daily_rundown_for_date(
    *,
    job_date: str,
    voice_profile_path: Path,
    subtitle_policy_path: Path,
    video_template_path: Path,
    output_dir: Path | None = None,
    max_newspapers: int | None = None,
    seed_rundown_dir: Path | None = None,
    force: bool = False,
    progress_callback=None,
) -> Path:
    def emit(stage: str, details: str) -> None:
        if progress_callback is not None:
            progress_callback(stage, details)

    project_dir = get_project_dir()
    emit("inicio", f"Preparando programa diario para {job_date}.")
    jobs_root = get_jobs_root(project_dir)
    job_paths = sorted((jobs_root / job_date).glob("*/job-manifest.json"))
    emit("lectura", f"Encontrados {len(job_paths)} job-manifest para el lote.")
    jobs = [read_json(path) | {"_path": path} for path in job_paths]
    jobs = [
        job
        for job in jobs
        if job.get("input_assets", {}).get("front_page_image")
        and job.get("story_narrative", {}).get("stories")
    ]
    if not jobs:
        raise ValueError(f"No hay jobs con speeches importados para `{job_date}`.")

    jobs = _sort_jobs_for_rundown(jobs)
    if max_newspapers is not None and max_newspapers > 0:
        original_count = len(jobs)
        jobs = jobs[:max_newspapers]
        emit(
            "modo",
            f"Modo desarrollo activo: usando {len(jobs)} de {original_count} periodico(s) listos.",
        )
    emit(
        "validacion",
        "Jobs listos: " + ", ".join(str(job.get("source_id") or "sin-source") for job in jobs),
    )
    fallback_voice = VoiceProfile.load(voice_profile_path)
    video_template = VideoTemplate.load(video_template_path)
    subtitle_policy = read_json(subtitle_policy_path)

    source_names = [_format_source_name(str(job.get("source_id") or "")) for job in jobs]
    story_count = sum(
        1
        for job in jobs
        for story in job.get("story_narrative", {}).get("stories", [])
        if str(story.get("speech") or story.get("summary") or "").strip()
    )
    if story_count == 0:
        raise ValueError(f"Los jobs de `{job_date}` no tienen speeches validos.")
    emit("validacion", f"Se usaran {len(jobs)} periodicos y {story_count} speeches.")

    run_stamp = datetime.now().strftime("%H%M%S")
    story_id = f"{job_date}-daily-rundown-{run_stamp}"
    target_dir = output_dir or project_dir / "data" / "rundowns" / job_date / run_stamp
    if target_dir.exists() and any(target_dir.iterdir()) and not force:
        raise ValueError("El rundown diario ya existe. Usa `force=True` para regenerarlo.")
    target_dir.mkdir(parents=True, exist_ok=True)
    audio_dir = target_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    emit("carpetas", f"Salida preparada en {target_dir.resolve().relative_to(project_dir).as_posix()}.")

    imported_intro = _select_imported_rundown_intro(jobs)
    emit(
        "intro",
        "Usando intro dinamica importada desde el primer prompt."
        if imported_intro
        else "No se encontro intro importada; se usara intro automatica de respaldo.",
    )
    segment_specs = _build_daily_rundown_segment_specs(
        jobs=jobs,
        voice_profile_path=voice_profile_path,
        project_dir=project_dir,
    )
    intro_text = str(segment_specs[0]["text"])
    emit("intro", f"Intro de presentador lista: {intro_text[:120]}{'...' if len(intro_text) > 120 else ''}")
    for segment in segment_specs[1:]:
        if str(segment.get("segment_type")) == "connector":
            emit("rundown", f"{segment.get('newspaper_name')}: bloque agregado.")
        elif str(segment.get("segment_type")) == "story":
            emit(
                "segmento",
                f"{segment.get('newspaper_name')} | {segment.get('story_type') or 'actualidad'} | "
                f"{segment.get('narrator_profile_id') or 'sin-narrador'} | {segment.get('headline') or 'sin titular'}",
            )

    reused_segment_audio_paths = _copy_reusable_seed_audio_segments(
        segment_specs=segment_specs,
        audio_dir=audio_dir,
        seed_rundown_dir=seed_rundown_dir,
        project_dir=project_dir,
        emit=emit,
    )

    segment_audio_paths: list[Path] = []
    for index, segment in enumerate(segment_specs, start=1):
        segment_audio_path = audio_dir / f"segment-{index:02d}.wav"
        reused_audio_path = reused_segment_audio_paths.get(index)
        if reused_audio_path is not None and reused_audio_path.exists():
            segment_audio_paths.append(reused_audio_path)
            segment["segment_audio_file"] = reused_audio_path.resolve().relative_to(project_dir).as_posix()
            emit(
                "audio",
                f"Audio reutilizado {index}/{len(segment_specs)}: "
                f"{reused_audio_path.resolve().relative_to(project_dir).as_posix()}",
            )
            continue
        emit(
            "audio",
            f"Generando audio {index}/{len(segment_specs)}: "
            f"{segment.get('newspaper_name')} - {segment.get('headline')}",
        )
        tts_voice = _resolve_tts_profile_for_narrator(
            narrator_profile_id=segment.get("narrator_profile_id"),
            fallback_voice_profile_path=voice_profile_path,
            project_dir=project_dir,
        )
        if str(segment.get("narrator_profile_id") or "") == "presentador":
            tts_voice = fallback_voice
        generate_voice_track(
            text=str(segment["text"]),
            provider=tts_voice.tts_provider,
            output_path=segment_audio_path,
            audio_file=None,
            voice=tts_voice.tts_voice,
            language=tts_voice.language,
            provider_settings=tts_voice.provider_settings,
        )
        segment_audio_paths.append(segment_audio_path)
        segment["segment_audio_file"] = segment_audio_path.resolve().relative_to(project_dir).as_posix()
        emit(
            "audio",
            f"Audio generado: {segment_audio_path.resolve().relative_to(project_dir).as_posix()}",
        )

    audio_path = target_dir / "narration.wav"
    emit("audio", f"Uniendo {len(segment_audio_paths)} audios en narration.wav.")
    concatenate_wav_files(segment_audio_paths, audio_path)
    total_duration = _get_wav_duration_seconds(audio_path)
    emit("audio", f"Audio final listo: {round(total_duration, 2)} segundos.")
    emit("subtitulos", "Generando subtitulos del programa completo.")
    full_text, subtitle_segments, aligned_duration = _build_rundown_subtitle_segments(
        segment_specs=segment_specs,
        subtitle_policy=subtitle_policy,
        project_dir=project_dir,
    )
    subtitles_path = target_dir / "subtitle-segments.json"
    write_json(
        subtitles_path,
        {
            "policy_id": subtitle_policy["policy_id"],
            "text_source": "daily_rundown",
            "text": full_text,
            "audio_duration_seconds": round(max(total_duration, aligned_duration), 3),
            "segments": subtitle_segments,
        },
    )
    emit("subtitulos", f"Subtitulos listos: {subtitles_path.resolve().relative_to(project_dir).as_posix()}.")
    for segment in segment_specs:
        segment["audio_file"] = audio_path.resolve().relative_to(project_dir).as_posix()
        segment["subtitle_segments_file"] = subtitles_path.resolve().relative_to(project_dir).as_posix()

    story_manifest_path = target_dir / "story-manifest.json"
    manifest = {
        "story_id": story_id,
        "video_template": video_template.template_id,
        "background": video_template.default_background,
        "music": video_template.default_music,
        "subtitle_policy": subtitle_policy["policy_id"],
        "render_output": f"output/{story_id}.mp4",
        "audio_path": audio_path.resolve().relative_to(project_dir).as_posix(),
        "subtitle_segments_path": subtitles_path.resolve().relative_to(project_dir).as_posix(),
        "segments": segment_specs,
    }
    write_json(story_manifest_path, manifest)
    emit("manifest", f"Story manifest creado: {story_manifest_path.resolve().relative_to(project_dir).as_posix()}.")

    gestures_dir = project_dir / str(segment_specs[0]["gestures_dir"])
    fallback_gestures = sorted(
        path
        for path in gestures_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    )
    if not fallback_gestures:
        raise ValueError(f"No se encontraron gestos para el presentador en: {gestures_dir}")

    video_segments: list[VideoSegment] = []
    for index, segment in enumerate(segment_specs, start=1):
        segment_gestures_dir = project_dir / str(segment["gestures_dir"])
        emit(
            "assets",
            f"Validando gestos {index}/{len(segment_specs)}: {segment.get('narrator_name')}.",
        )
        segment_gestures = sorted(
            path
            for path in segment_gestures_dir.iterdir()
            if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
        )
        if not segment_gestures:
            raise ValueError(f"No se encontraron gestos en: {segment_gestures_dir}")
        video_segments.append(
            VideoSegment(
                newspaper_name=str(segment["newspaper_name"]),
                cover_path=project_dir / str(segment["cover"]),
                headline=str(segment.get("headline") or ""),
                text=str(segment["text"]),
                narrator_name=str(segment["narrator_name"]),
                gesture_paths=segment_gestures,
                duration_seconds=_get_wav_duration_seconds(project_dir / str(segment["segment_audio_file"])),
                cover_region=segment.get("cover_region"),
                segment_type=str(segment.get("segment_type") or "story"),
            )
        )

    emit("remotion", "Sincronizando assets y actualizando generated-story.js.")
    compose_video_props(
        background_path=project_dir / video_template.default_background,
        gesture_paths=fallback_gestures,
        segments=video_segments,
        audio_path=audio_path,
        output_stem=story_id,
        spec=VideoSpec(fps=30, composition_id=video_template.composition_id),
        keep_previous_generated=True,
        subtitle_segments=read_json(subtitles_path).get("segments", []),
    )
    emit("remotion", "Preview diario listo en Remotion: NewsVideo-generated.")
    return story_manifest_path


def retry_daily_rundown_from_existing_audio(
    *,
    job_date: str,
    rundown_dir: Path,
    voice_profile_path: Path,
    subtitle_policy_path: Path,
    video_template_path: Path,
    progress_callback=None,
) -> Path:
    def emit(stage: str, details: str) -> None:
        if progress_callback is not None:
            progress_callback(stage, details)

    project_dir = get_project_dir()
    target_dir = rundown_dir if rundown_dir.is_absolute() else (project_dir / rundown_dir).resolve()
    audio_dir = target_dir / "audio"
    emit("inicio", f"Reintentando programa diario desde audios existentes: {target_dir.relative_to(project_dir).as_posix()}.")
    if not audio_dir.exists():
        raise ValueError(f"No existe la carpeta de audios: {audio_dir}")
    available_audio_paths = sorted(audio_dir.glob("segment-*.wav"))
    if not available_audio_paths:
        raise ValueError(f"No se encontraron audios reutilizables en: {audio_dir}")

    jobs_root = get_jobs_root(project_dir)
    job_paths = sorted((jobs_root / job_date).glob("*/job-manifest.json"))
    jobs = [read_json(path) | {"_path": path} for path in job_paths]
    jobs = [
        job
        for job in jobs
        if job.get("input_assets", {}).get("front_page_image")
        and job.get("story_narrative", {}).get("stories")
    ]
    if not jobs:
        raise ValueError(f"No hay jobs con speeches importados para `{job_date}`.")
    jobs = _sort_jobs_for_rundown(jobs)
    emit("lectura", f"Reconstruidos {len(jobs)} job(s) listos desde manifests.")

    video_template = VideoTemplate.load(video_template_path)
    subtitle_policy = read_json(subtitle_policy_path)
    story_count = sum(
        1
        for job in jobs
        for story in job.get("story_narrative", {}).get("stories", [])
        if str(story.get("speech") or story.get("summary") or "").strip()
    )
    if story_count == 0:
        raise ValueError(f"Los jobs de `{job_date}` no tienen speeches validos.")

    segment_specs = _build_daily_rundown_segment_specs(
        jobs=jobs,
        voice_profile_path=voice_profile_path,
        project_dir=project_dir,
    )
    emit(
        "lectura",
        f"Reconstruidos {len(segment_specs)} segmento(s) desde los manifests actuales para respetar cambios de enfoque.",
    )

    segment_audio_paths: list[Path] = []
    for index, segment in enumerate(segment_specs, start=1):
        if index > len(available_audio_paths):
            raise ValueError(
                f"Falta el audio existente `data/rundowns/{job_date}/{target_dir.name}/audio/segment-{index:02d}.wav`. "
                "Este reintento solo funciona cuando todos los segmentos ya fueron generados."
            )
        segment_audio_path = available_audio_paths[index - 1]
        segment_audio_paths.append(segment_audio_path)
        segment["segment_audio_file"] = segment_audio_path.resolve().relative_to(project_dir).as_posix()
        segment["segment_type"] = str(segment.get("segment_type") or ("intro" if index == 1 else "story"))
    extra_audio_paths = available_audio_paths[len(segment_audio_paths):]
    if extra_audio_paths:
        emit("validacion", f"Hay {len(extra_audio_paths)} audio(s) extra en la carpeta; se ignoraran.")
    emit("validacion", f"Reutilizando {len(segment_audio_paths)} audio(s) existentes.")

    run_stamp = target_dir.name
    story_id = f"{job_date}-daily-rundown-{run_stamp}"
    audio_path = target_dir / "narration.wav"
    emit("audio", f"Uniendo {len(segment_audio_paths)} audios existentes en narration.wav.")
    concatenate_wav_files(segment_audio_paths, audio_path)
    total_duration = _get_wav_duration_seconds(audio_path)
    emit("audio", f"Audio final listo: {round(total_duration, 2)} segundos.")

    emit("subtitulos", "Regenerando subtitulos del programa completo.")
    full_text, subtitle_segments, aligned_duration = _build_rundown_subtitle_segments(
        segment_specs=segment_specs,
        subtitle_policy=subtitle_policy,
        project_dir=project_dir,
    )
    subtitles_path = target_dir / "subtitle-segments.json"
    write_json(
        subtitles_path,
        {
            "policy_id": subtitle_policy["policy_id"],
            "text_source": "daily_rundown",
            "text": full_text,
            "audio_duration_seconds": round(max(total_duration, aligned_duration), 3),
            "segments": subtitle_segments,
        },
    )
    emit("subtitulos", f"Subtitulos listos: {subtitles_path.resolve().relative_to(project_dir).as_posix()}.")
    for segment in segment_specs:
        segment["audio_file"] = audio_path.resolve().relative_to(project_dir).as_posix()
        segment["subtitle_segments_file"] = subtitles_path.resolve().relative_to(project_dir).as_posix()

    story_manifest_path = target_dir / "story-manifest.json"
    manifest = {
        "story_id": story_id,
        "video_template": video_template.template_id,
        "background": video_template.default_background,
        "music": video_template.default_music,
        "subtitle_policy": subtitle_policy["policy_id"],
        "render_output": f"output/{story_id}.mp4",
        "audio_path": audio_path.resolve().relative_to(project_dir).as_posix(),
        "subtitle_segments_path": subtitles_path.resolve().relative_to(project_dir).as_posix(),
        "segments": segment_specs,
    }
    write_json(story_manifest_path, manifest)
    emit("manifest", f"Story manifest creado: {story_manifest_path.resolve().relative_to(project_dir).as_posix()}.")

    gestures_dir = project_dir / str(segment_specs[0]["gestures_dir"])
    fallback_gestures = sorted(
        path
        for path in gestures_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    )
    if not fallback_gestures:
        raise ValueError(f"No se encontraron gestos para el presentador en: {gestures_dir}")

    video_segments: list[VideoSegment] = []
    for index, segment in enumerate(segment_specs, start=1):
        segment_gestures_dir = project_dir / str(segment["gestures_dir"])
        emit("assets", f"Validando gestos {index}/{len(segment_specs)}: {segment.get('narrator_name')}.")
        segment_gestures = sorted(
            path
            for path in segment_gestures_dir.iterdir()
            if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
        )
        if not segment_gestures:
            raise ValueError(f"No se encontraron gestos en: {segment_gestures_dir}")
        video_segments.append(
            VideoSegment(
                newspaper_name=str(segment["newspaper_name"]),
                cover_path=project_dir / str(segment["cover"]),
                headline=str(segment.get("headline") or ""),
                text=str(segment["text"]),
                narrator_name=str(segment["narrator_name"]),
                gesture_paths=segment_gestures,
                duration_seconds=_get_wav_duration_seconds(project_dir / str(segment["segment_audio_file"])),
                cover_region=segment.get("cover_region"),
                segment_type=str(segment.get("segment_type") or "story"),
            )
        )

    emit("remotion", "Sincronizando assets y actualizando generated-story.js.")
    compose_video_props(
        background_path=project_dir / video_template.default_background,
        gesture_paths=fallback_gestures,
        segments=video_segments,
        audio_path=audio_path,
        output_stem=story_id,
        spec=VideoSpec(fps=30, composition_id=video_template.composition_id),
        keep_previous_generated=True,
        subtitle_segments=read_json(subtitles_path).get("segments", []),
    )
    emit("remotion", "Preview diario listo en Remotion: NewsVideo-generated.")
    return story_manifest_path


def compose_job_for_preview(
    *,
    job_manifest_path: Path,
    story_manifest_path: Path | None = None,
    video_template_path: Path,
) -> Path:
    project_dir = get_project_dir()
    job = read_json(job_manifest_path)
    video_template = VideoTemplate.load(video_template_path)
    resolved_story_manifest = story_manifest_path
    if resolved_story_manifest is None:
        story_manifest_value = job.get("video", {}).get("story_manifest_path")
        if not story_manifest_value:
            raise ValueError(
                "El job no tiene `video.story_manifest_path`. Genera primero el story-manifest o pasalo por `--story-manifest`."
            )
        resolved_story_manifest = project_dir / story_manifest_value

    story = read_json(resolved_story_manifest)
    background = project_dir / story["background"]
    subtitle_segments_value = story.get("subtitle_segments_path")
    if not subtitle_segments_value and story.get("segments"):
        subtitle_segments_value = story["segments"][0].get("subtitle_segments_file")
    subtitle_segments = []
    if subtitle_segments_value:
        subtitle_segments = read_json(project_dir / str(subtitle_segments_value)).get("segments", [])
    segments: list[VideoSegment] = []
    fallback_gesture_paths: list[Path] = []

    for index, segment in enumerate(story.get("segments", [])):
        gestures_dir = project_dir / segment["gestures_dir"]
        gesture_paths = sorted(
            path
            for path in gestures_dir.iterdir()
            if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
        )
        if not gesture_paths:
            raise ValueError(f"No se encontraron gestos en: {gestures_dir}")
        if index == 0:
            fallback_gesture_paths = gesture_paths
        segments.append(
            VideoSegment(
                newspaper_name=segment["newspaper_name"],
                cover_path=project_dir / segment["cover"],
                headline=segment.get("headline"),
                text=segment["text"],
                narrator_name=segment.get("narrator_name"),
                gesture_paths=gesture_paths,
                duration_seconds=(
                    _get_wav_duration_seconds(project_dir / str(segment["segment_audio_file"]))
                    if segment.get("segment_audio_file")
                    else None
                ),
                cover_region=segment.get("cover_region"),
                segment_type=str(segment.get("segment_type") or "story"),
            )
        )

    audio_path_value = story["segments"][0].get("audio_file") or job.get("voice", {}).get("audio_path")
    if not audio_path_value:
        raise ValueError(
            "No se encontro audio para la previsualizacion. Ejecuta `voice-job` antes de `compose-job`."
        )
    audio_path = project_dir / audio_path_value

    compose_video_props(
        background_path=background,
        gesture_paths=fallback_gesture_paths,
        segments=segments,
        audio_path=audio_path,
        output_stem=story["story_id"],
        spec=VideoSpec(
            fps=30,
            composition_id=video_template.composition_id,
        ),
        subtitle_segments=subtitle_segments,
    )

    timestamp = datetime.now().isoformat(timespec="seconds")
    job["status"] = "composed"
    job["video"]["story_manifest_path"] = resolved_story_manifest.resolve().relative_to(project_dir).as_posix()
    job["video"]["preview_composition_id"] = video_template.composition_id
    job["audit"]["updated_at"] = timestamp
    job["audit"].setdefault("events", []).append(
        {
            "stage": "compose_preview",
            "status": "completed",
            "timestamp": timestamp,
            "details": "Assets sincronizados y generated-story.js actualizado para previsualizacion en Remotion.",
        }
    )
    write_json(job_manifest_path, job)
    return resolved_story_manifest


def _apply_template(template: str, values: dict[str, str]) -> str:
    result = template
    for key, value in values.items():
        result = result.replace(f"{{{key}}}", value)
    return result


def publish_job(
    *,
    job_manifest_path: Path,
    publishing_profile_path: Path,
    confirm: bool = False,
    platform_post_id: str | None = None,
    post_url: str | None = None,
) -> Path:
    job = read_json(job_manifest_path)
    profile = read_json(publishing_profile_path)
    headline_candidates = job.get("extraction", {}).get("headline_candidates", [])
    headline = headline_candidates[0] if headline_candidates else _format_source_name(job["source_id"])
    approved_text = job.get("script", {}).get("approved_text") or job.get("script", {}).get("draft", "")
    if not approved_text.strip():
        raise ValueError("No hay texto aprobado o draft para preparar la publicacion.")

    source_name = _format_source_name(job["source_id"])
    script_excerpt = approved_text.strip()[:160].rstrip()
    publish_title = _apply_template(
        profile.get("title_template", "{source_name}: {headline}"),
        {"source_name": source_name, "headline": headline},
    )
    publish_description = _apply_template(
        profile.get("description_template", "{script_excerpt}"),
        {"script_excerpt": script_excerpt, "source_name": source_name, "headline": headline},
    )

    require_confirmation = bool(profile.get("require_human_confirmation", True))
    if platform_post_id or post_url:
        publication_status = "published"
    elif require_confirmation and not confirm:
        publication_status = "ready_for_review"
    else:
        publication_status = "queued"

    timestamp = datetime.now().isoformat(timespec="seconds")
    job["publication"] = {
        **job.get("publication", {}),
        "profile_id": profile["profile_id"],
        "platform": profile.get("platform"),
        "visibility": profile.get("visibility", "private"),
        "title": publish_title,
        "description": publish_description,
        "hashtags": profile.get("hashtags", []),
        "status": publication_status,
        "post_url": post_url,
        "platform_post_id": platform_post_id,
        "require_human_confirmation": require_confirmation,
    }
    if publication_status in {"queued", "published"}:
        job["status"] = publication_status
    job["audit"]["updated_at"] = timestamp
    job["audit"].setdefault("events", []).append(
        {
            "stage": "publish",
            "status": publication_status,
            "timestamp": timestamp,
            "details": "Metadata de publicacion preparada." if publication_status != "published" else "Publicacion registrada en el job.",
        }
    )
    return write_json(job_manifest_path, job)
