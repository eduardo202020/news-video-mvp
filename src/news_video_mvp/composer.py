from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import wave
import shutil as which_shutil


class VideoRenderError(RuntimeError):
    """Raised when the Remotion render fails."""


@dataclass(slots=True)
class VideoSpec:
    width: int = 1080
    height: int = 1920
    fps: int = 30
    narrator_name: str = "Magaly"
    composition_id: str = "NewsVideo"


@dataclass(slots=True)
class VideoSegment:
    newspaper_name: str
    cover_path: Path
    text: str
    headline: str | None = None
    narrator_name: str | None = None
    gesture_paths: list[Path] | None = None
    duration_seconds: float | None = None
    cover_region: dict[str, float] | None = None
    support_visual: dict[str, object] | None = None
    segment_type: str | None = None


def render_video(
    background_path: Path,
    cover_path: Path,
    gesture_paths: list[Path],
    text: str,
    audio_path: Path,
    output_path: Path,
    spec: VideoSpec | None = None,
) -> Path:
    return render_video_sequence(
        background_path=background_path,
        gesture_paths=gesture_paths,
        segments=[
            VideoSegment(
                newspaper_name=_format_newspaper_name(cover_path.stem),
                cover_path=cover_path,
                text=text,
            )
        ],
        audio_path=audio_path,
        output_path=output_path,
        spec=spec,
    )


def render_video_sequence(
    background_path: Path,
    gesture_paths: list[Path],
    segments: list[VideoSegment],
    audio_path: Path,
    output_path: Path,
    spec: VideoSpec | None = None,
) -> Path:
    spec = spec or VideoSpec()
    props, remotion_dir = compose_video_props(
        background_path=background_path,
        gesture_paths=gesture_paths,
        segments=segments,
        audio_path=audio_path,
        output_stem=output_path.stem,
        spec=spec,
        subtitle_segments=None,
    )
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not segments:
        raise VideoRenderError("Debes proporcionar al menos un segmento para el video.")

    with TemporaryDirectory() as tmp_dir:
        props_path = Path(tmp_dir) / "remotion-props.json"
        props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")

        command = [
            *_resolve_remotion_command_prefix(),
            "remotion",
            "render",
            "src/index.jsx",
            spec.composition_id,
            str(output_path),
            "--props",
            str(props_path),
        ]
        completed = subprocess.run(
            command,
            cwd=remotion_dir,
            capture_output=True,
            text=True,
            check=False,
        )

    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        details = stderr or stdout or "Sin detalles del proceso."
        raise VideoRenderError(f"Fallo el render de Remotion: {details}")

    if not output_path.exists():
        raise VideoRenderError("Remotion termino sin generar el archivo de salida.")

    return output_path


def compose_video_props(
    background_path: Path,
    gesture_paths: list[Path],
    segments: list[VideoSegment],
    audio_path: Path,
    output_stem: str,
    spec: VideoSpec | None = None,
    keep_previous_generated: bool = False,
    subtitle_segments: list[dict[str, object]] | None = None,
) -> tuple[dict, Path]:
    spec = spec or VideoSpec()
    if not segments:
        raise VideoRenderError("Debes proporcionar al menos un segmento para el video.")

    project_root = Path(__file__).resolve().parents[2]
    remotion_dir = project_root / "remotion-app"
    public_dir = remotion_dir / "public"
    generated_dir = public_dir / "assets" / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)

    story_id = output_stem
    story_assets_dir = generated_dir / story_id
    if story_assets_dir.exists():
        shutil.rmtree(story_assets_dir)
    story_assets_dir.mkdir(parents=True, exist_ok=True)

    background_asset = _copy_asset(background_path, story_assets_dir / "background")
    audio_asset = _copy_asset(audio_path, story_assets_dir / "audio")
    gesture_assets = [
        _copy_asset(path, story_assets_dir / "gestures" / f"gesture_{index:02d}")
        for index, path in enumerate(gesture_paths)
    ]
    segment_props = []
    for index, segment in enumerate(segments):
        resolved_cover_path = _resolve_test_trimmed_cover_path(segment.cover_path, project_root=project_root)
        cover_asset = _copy_asset(resolved_cover_path, story_assets_dir / "covers" / f"cover_{index:02d}")
        segment_gesture_assets = []
        for gesture_index, gesture_path in enumerate(segment.gesture_paths or gesture_paths):
            copied = _copy_asset(
                gesture_path,
                story_assets_dir / "segment_gestures" / f"segment_{index:02d}" / f"gesture_{gesture_index:02d}",
            )
            segment_gesture_assets.append(_to_static_path(copied, public_dir))
        segment_props.append(
            {
                "newspaperName": segment.newspaper_name,
                "coverSrc": _to_static_path(cover_asset, public_dir),
                "headline": segment.headline or "",
                "text": segment.text,
                "narratorName": segment.narrator_name or spec.narrator_name,
                "gestures": segment_gesture_assets,
                "durationSeconds": segment.duration_seconds,
                "coverRegion": segment.cover_region,
                "supportVisual": segment.support_visual,
                "segmentType": segment.segment_type or "story",
            }
        )
    if not keep_previous_generated:
        _cleanup_generated_assets(generated_dir=generated_dir, keep_story_id=story_id)

    audio_duration = _get_wav_duration(audio_asset)
    duration_in_frames = max(1, int(round(audio_duration * spec.fps)))

    props = {
        "id": story_id,
        "newspaperName": segment_props[0]["newspaperName"],
        "coverSrc": segment_props[0]["coverSrc"],
        "backgroundSrc": _to_static_path(background_asset, public_dir),
        "audioSrc": _to_static_path(audio_asset, public_dir),
        "durationInFrames": duration_in_frames,
        "fps": spec.fps,
        "narratorName": segment_props[0]["narratorName"],
        "text": " ".join(segment.text for segment in segments),
        "gestures": [_to_static_path(path, public_dir) for path in gesture_assets],
        "segments": segment_props,
        "subtitleSegments": subtitle_segments or [],
    }
    _write_generated_story_module(remotion_dir=remotion_dir, props=props)
    return props, remotion_dir


def _resolve_test_trimmed_cover_path(source_path: Path, *, project_root: Path) -> Path:
    source_path = source_path.resolve()
    try:
        relative = source_path.relative_to(project_root)
    except ValueError:
        return source_path

    parts = relative.parts
    if len(parts) < 6:
        return source_path
    if parts[:3] != ("data", "jobs", parts[2]):
        return source_path
    if parts[3].count("-") < 3:
        return source_path
    if parts[4] != "input":
        return source_path

    job_date = parts[2]
    job_id = parts[3]
    trimmed_candidate = project_root / "data" / "tests" / "trim-front-pages" / job_date / job_id / source_path.name
    if trimmed_candidate.exists():
        return trimmed_candidate
    return source_path


def _copy_asset(source: Path, target_without_suffix: Path) -> Path:
    source = source.resolve()
    destination = target_without_suffix.with_suffix(source.suffix.lower())
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def _to_static_path(asset_path: Path, public_dir: Path) -> str:
    return asset_path.resolve().relative_to(public_dir.resolve()).as_posix()


def _get_wav_duration(audio_path: Path) -> float:
    with wave.open(str(audio_path), "rb") as wav_file:
        frame_count = wav_file.getnframes()
        frame_rate = wav_file.getframerate()
        if frame_rate <= 0:
            raise VideoRenderError(f"No se pudo leer la duracion de {audio_path}.")
        return frame_count / frame_rate


def _format_newspaper_name(stem: str) -> str:
    return stem.replace("_", " ").replace("-", " ").title()


def _resolve_remotion_command_prefix() -> list[str]:
    for candidate in ("npx.cmd", "npx"):
        resolved = which_shutil.which(candidate)
        if resolved:
            return [resolved]
    for candidate in ("npm.cmd", "npm"):
        resolved = which_shutil.which(candidate)
        if resolved:
            return [resolved, "exec", "--"]
    raise VideoRenderError(
        "No se encontro `npx` ni `npm` en el sistema. Instala Node.js para usar Remotion."
    )


def _write_generated_story_module(remotion_dir: Path, props: dict) -> None:
    target = remotion_dir / "src" / "generated-story.js"
    serialized = json.dumps(props, ensure_ascii=False, indent=2)
    target.write_text(
        "export const generatedStory = " + serialized + ";\n",
        encoding="utf-8",
    )


def _cleanup_generated_assets(generated_dir: Path, keep_story_id: str) -> None:
    for path in generated_dir.iterdir():
        if not path.is_dir() or path.name == keep_story_id:
            continue
        shutil.rmtree(path, ignore_errors=True)


def concatenate_wav_files(audio_paths: list[Path], output_path: Path) -> Path:
    if not audio_paths:
        raise VideoRenderError("No hay audios para concatenar.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(audio_paths[0]), "rb") as first_wav:
        params = first_wav.getparams()
        frames = [first_wav.readframes(first_wav.getnframes())]
        format_params = params[:3] + params[4:6]

    for audio_path in audio_paths[1:]:
        with wave.open(str(audio_path), "rb") as wav_file:
            current_params = wav_file.getparams()
            current_format_params = current_params[:3] + current_params[4:6]
            if current_format_params != format_params:
                raise VideoRenderError(
                    "No se pudieron concatenar los audios porque no comparten el mismo formato WAV."
                )
            frames.append(wav_file.readframes(wav_file.getnframes()))

    with wave.open(str(output_path), "wb") as output_wav:
        output_wav.setparams(params)
        for chunk in frames:
            output_wav.writeframes(chunk)

    return output_path
