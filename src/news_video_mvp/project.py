from __future__ import annotations

from pathlib import Path


def get_project_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def find_default_cover(project_dir: Path) -> Path:
    covers_dir = project_dir / "input" / "periodicos"
    if not covers_dir.exists() or not covers_dir.is_dir():
        raise FileNotFoundError(
            f"No se encontro el directorio de portadas: {covers_dir}"
        )

    candidates = sorted(
        path
        for path in covers_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    )
    if not candidates:
        raise FileNotFoundError(f"No se encontraron portadas en: {covers_dir}")

    preferred_names = ("trome.png", "trome.jpg", "trome.jpeg", "trome.webp")
    by_name = {path.name.casefold(): path for path in candidates}
    for preferred_name in preferred_names:
        match = by_name.get(preferred_name)
        if match is not None:
            return match

    return candidates[0]
