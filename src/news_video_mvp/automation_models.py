from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


@dataclass(slots=True)
class SourceConfig:
    path: Path
    source_id: str
    display_name: str
    base_url: str
    discovery: dict[str, Any]
    selectors: dict[str, Any]
    storage: dict[str, Any]
    ocr_hints: dict[str, Any]
    schedule: dict[str, Any]

    @classmethod
    def load(cls, path: Path) -> "SourceConfig":
        data = read_json(path)
        return cls(
            path=path.resolve(),
            source_id=data["source_id"],
            display_name=data["display_name"],
            base_url=data.get("base_url", ""),
            discovery=data.get("discovery", {}),
            selectors=data.get("selectors", {}),
            storage=data.get("storage", {}),
            ocr_hints=data.get("ocr_hints", {}),
            schedule=data.get("schedule", {}),
        )


@dataclass(slots=True)
class VoiceProfile:
    path: Path
    profile_id: str
    narrator_name: str
    tts_provider: str
    tts_voice: str
    gestures_dir: str

    @classmethod
    def load(cls, path: Path) -> "VoiceProfile":
        data = read_json(path)
        return cls(
            path=path.resolve(),
            profile_id=data["profile_id"],
            narrator_name=data["narrator_name"],
            tts_provider=data["tts_provider"],
            tts_voice=data["tts_voice"],
            gestures_dir=data["gestures_dir"],
        )


@dataclass(slots=True)
class VideoTemplate:
    path: Path
    template_id: str
    composition_id: str
    subtitle_policy_id: str
    default_background: str
    default_music: dict[str, Any]

    @classmethod
    def load(cls, path: Path) -> "VideoTemplate":
        data = read_json(path)
        return cls(
            path=path.resolve(),
            template_id=data["template_id"],
            composition_id=data["composition_id"],
            subtitle_policy_id=data["subtitle_policy_id"],
            default_background=data["default_background"],
            default_music=data["default_music"],
        )


def parse_date(value: str) -> date:
    return date.fromisoformat(value)
