from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass(slots=True)
class StorySegmentConfig:
    cover: Path | None
    text: str
    newspaper_name: str | None = None
    narrator_name: str | None = None
    gestures_dir: Path | None = None
    output: Path | None = None
    audio_file: Path | None = None
    tts_provider: str | None = None
    tts_voice: str | None = None


@dataclass(slots=True)
class StoryConfig:
    render_mode: str
    background: Path | None
    stories: list[StorySegmentConfig]
    config_path: Path
    output: Path | None = None
    output_dir: Path | None = None
    gestures_dir: Path | None = None


def resolve_path(path_value: Path | str | None, *, base_dir: Path) -> Path | None:
    if path_value is None:
        return None
    path = Path(path_value)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def ensure_image_file(path: Path, *, label: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"No existe {label}: {path}")
    if path.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
        raise FileNotFoundError(f"{label} no tiene un formato de imagen soportado: {path}")
    return path


def load_story_config(config_path: Path) -> StoryConfig:
    if not config_path.exists():
        raise FileNotFoundError(f"No existe el archivo de configuracion: {config_path}")

    raw = json.loads(config_path.read_text(encoding="utf-8"))
    stories = raw.get("stories")
    if not isinstance(stories, list) or not stories:
        raise ValueError(
            "El archivo de configuracion debe incluir una lista `stories` con al menos un item."
        )

    base_dir = config_path.parent
    return StoryConfig(
        render_mode=raw.get("render_mode", "batch"),
        background=resolve_path(raw.get("background"), base_dir=base_dir),
        output=resolve_path(raw.get("output"), base_dir=base_dir),
        output_dir=resolve_path(raw.get("output_dir"), base_dir=base_dir),
        gestures_dir=resolve_path(raw.get("gestures_dir"), base_dir=base_dir),
        config_path=config_path.resolve(),
        stories=[
            StorySegmentConfig(
                cover=resolve_path(item.get("cover"), base_dir=base_dir),
                text=str(item.get("text", "")).strip(),
                newspaper_name=item.get("newspaper_name"),
                narrator_name=item.get("narrator_name"),
                gestures_dir=resolve_path(item.get("gestures_dir"), base_dir=base_dir),
                output=resolve_path(item.get("output"), base_dir=base_dir),
                audio_file=resolve_path(item.get("audio_file"), base_dir=base_dir),
                tts_provider=item.get("tts_provider"),
                tts_voice=item.get("tts_voice"),
            )
            for item in stories
        ],
    )


def validate_gestures_dir(gestures_dir: Path) -> list[Path]:
    if not gestures_dir.exists() or not gestures_dir.is_dir():
        raise FileNotFoundError(f"No existe el directorio de gestos: {gestures_dir}")

    gesture_paths = sorted(
        path
        for path in gestures_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
    )
    if not gesture_paths:
        raise FileNotFoundError(
            f"No se encontraron imagenes de gesto en: {gestures_dir}"
        )
    return gesture_paths
