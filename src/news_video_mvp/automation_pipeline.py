from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import shutil
import wave
from urllib.parse import urlparse
from urllib.request import urlretrieve

from .automation_models import SourceConfig, VideoTemplate, VoiceProfile, read_json, write_json
from .project import get_project_dir
from .subtitles import build_subtitle_segments
from .tts import prepare_audio


def get_automation_dir(project_dir: Path | None = None) -> Path:
    return (project_dir or get_project_dir()) / "automation"


def get_jobs_root(project_dir: Path | None = None) -> Path:
    return (project_dir or get_project_dir()) / "data" / "jobs"


def build_job_id(*, job_date: str, source_id: str, suffix: str = "frontpage-001") -> str:
    return f"{job_date}-{source_id}-{suffix}"


def build_source_url(source: SourceConfig, *, job_date: str) -> str:
    pattern = source.discovery.get("front_page_url_pattern")
    if not pattern:
        return source.base_url
    return str(pattern).format(date=job_date)


def ensure_job_scaffold(job_dir: Path) -> None:
    for name in ("input", "work", "output", "review"):
        (job_dir / name).mkdir(parents=True, exist_ok=True)


def infer_extension_from_url(url: str, default: str = ".jpg") -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    return suffix or default


def stage_front_page_asset(
    *,
    job_dir: Path,
    front_page_image: Path | None,
    front_page_url: str | None,
    download_front_page: bool,
) -> Path | None:
    if front_page_image is not None:
        if not front_page_image.exists():
            raise FileNotFoundError(f"No existe la portada local: {front_page_image}")
        destination = job_dir / "input" / f"front-page{front_page_image.suffix.lower()}"
        shutil.copy2(front_page_image, destination)
        return destination

    if download_front_page and front_page_url:
        destination = job_dir / "input" / f"front-page{infer_extension_from_url(front_page_url)}"
        urlretrieve(front_page_url, destination)
        return destination

    return None


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
    job_id: str | None = None,
) -> Path:
    project_dir = get_project_dir()
    source = SourceConfig.load(source_config_path)
    voice = VoiceProfile.load(voice_profile_path)
    video_template = VideoTemplate.load(video_template_path)
    resolved_job_id = job_id or build_job_id(job_date=job_date, source_id=source.source_id)
    job_dir = get_jobs_root(project_dir) / job_date / resolved_job_id
    ensure_job_scaffold(job_dir)

    resolved_front_page_url = front_page_url or build_source_url(source, job_date=job_date)
    staged_front_page = stage_front_page_asset(
        job_dir=job_dir,
        front_page_image=front_page_image,
        front_page_url=resolved_front_page_url,
        download_front_page=download_front_page,
    )

    timestamp = datetime.now().isoformat(timespec="seconds")
    manifest = {
        "job_id": resolved_job_id,
        "source_id": source.source_id,
        "date": job_date,
        "approval_mode": approval_mode,
        "status": "scraped" if staged_front_page else "discovered",
        "input_assets": {
            "front_page_image": staged_front_page.relative_to(project_dir).as_posix()
            if staged_front_page
            else None,
            "source_url": resolved_front_page_url,
            "source_config": source_config_path.resolve().relative_to(project_dir).as_posix(),
        },
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
        "script": {
            "template_id": script_template_id,
            "draft": "",
            "approved_text": "",
            "review_notes": "",
        },
        "voice": {
            "profile_id": voice.profile_id,
            "provider": voice.tts_provider,
            "tts_voice": voice.tts_voice,
            "audio_path": None,
            "timestamps_path": None,
        },
        "subtitles": {
            "policy_id": subtitle_policy_id,
            "segments_path": None,
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
                    "status": "completed",
                    "timestamp": timestamp,
                    "details": "Job creado desde source config declarativo.",
                }
            ],
        },
    }
    return write_json(job_dir / "job-manifest.json", manifest)


def _resolve_repo_path(path_value: str | None) -> Path | None:
    if not path_value:
        return None
    return get_project_dir() / Path(path_value)


def _normalize_text_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _load_ocr_text(
    *,
    job_manifest_path: Path,
    ocr_text: str | None,
    ocr_text_file: Path | None,
) -> tuple[str, Path | None]:
    if ocr_text_file is not None:
        if not ocr_text_file.exists():
            raise FileNotFoundError(f"No existe el archivo OCR: {ocr_text_file}")
        return ocr_text_file.read_text(encoding="utf-8"), ocr_text_file

    if ocr_text is not None:
        work_file = job_manifest_path.with_name("ocr-text.txt")
        work_file.write_text(ocr_text, encoding="utf-8")
        return ocr_text, work_file

    job = read_json(job_manifest_path)
    front_page = _resolve_repo_path(job["input_assets"].get("front_page_image"))
    if front_page is None:
        raise ValueError("El job no tiene `input_assets.front_page_image`.")
    sidecar = front_page.with_suffix(".txt")
    if sidecar.exists():
        return sidecar.read_text(encoding="utf-8"), sidecar

    raise ValueError(
        "No se encontro texto OCR. Pasa `--ocr-text`, `--ocr-text-file` o crea un sidecar `.txt` junto a la portada."
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


def extract_and_classify_job(
    *,
    job_manifest_path: Path,
    editorial_policy_path: Path,
    ocr_text: str | None = None,
    ocr_text_file: Path | None = None,
    ocr_confidence: float | None = None,
) -> Path:
    project_dir = get_project_dir()
    job = read_json(job_manifest_path)
    policy = read_json(editorial_policy_path)
    raw_text, ocr_file_path = _load_ocr_text(
        job_manifest_path=job_manifest_path,
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
            "details": f"Extraidos {len(blocks)} bloques OCR y {len(headline_candidates)} titulares candidatos.",
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
    voice = VoiceProfile.load(voice_profile_path)
    subtitle_policy = read_json(subtitle_policy_path)
    approved_text = job.get("script", {}).get("approved_text", "").strip()
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

    prepare_audio(
        text=approved_text,
        provider=voice.tts_provider,
        output_path=audio_path,
        audio_file=audio_file,
        voice=voice.tts_voice,
    )
    total_duration = _get_wav_duration_seconds(audio_path)
    segments = build_subtitle_segments(
        approved_text,
        total_duration=total_duration,
        max_chars=int(subtitle_policy.get("max_chars_per_block", 72)),
    )
    subtitle_payload = {
        "policy_id": subtitle_policy["policy_id"],
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
        "profile_id": voice.profile_id,
        "provider": voice.tts_provider,
        "tts_voice": voice.tts_voice,
        "audio_path": audio_path.resolve().relative_to(project_dir).as_posix(),
        "timestamps_path": None,
    }
    job["subtitles"] = {
        **job.get("subtitles", {}),
        "policy_id": subtitle_policy["policy_id"],
        "segments_path": subtitle_segments_path.resolve().relative_to(project_dir).as_posix(),
    }
    job["status"] = "subtitled"
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
    approved_text = job["script"].get("approved_text") or job["script"].get("draft")
    if not approved_text:
        raise ValueError(
            "El job-manifest no tiene `script.approved_text` ni `script.draft`; no se puede construir el story-manifest."
        )

    front_page_image = job["input_assets"].get("front_page_image")
    if not front_page_image:
        raise ValueError(
            "El job-manifest no tiene `input_assets.front_page_image`; primero debes asociar o descargar la portada."
        )

    manifest = {
        "story_id": story_id,
        "video_template": video_template.template_id,
        "background": video_template.default_background,
        "music": video_template.default_music,
        "subtitle_policy": job["subtitles"]["policy_id"],
        "render_output": render_output,
        "segments": [
            {
                "newspaper_name": job["source_id"].replace("-", " ").title(),
                "cover": front_page_image,
                "narrator_name": voice.narrator_name,
                "gestures_dir": voice.gestures_dir,
                "text": approved_text,
                "audio_file": job["voice"].get("audio_path"),
                "subtitle_segments_file": job["subtitles"].get("segments_path"),
            }
        ],
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
