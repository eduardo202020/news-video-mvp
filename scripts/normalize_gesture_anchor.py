from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


VALID_EXTENSIONS = {".png", ".webp"}


@dataclass
class GestureResult:
    path: Path
    width_before: int
    height_before: int
    width_after: int
    height_after: int
    trim_right: int
    trim_bottom: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Recorta padding transparente en la derecha y abajo de los gestos "
            "para unificar el anclaje inferior derecho."
        )
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("remotion-app/public/assets/gestures/cuy"),
        help="Directorio raiz con carpetas de gestos por narrador.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo reporta los recortes calculados sin modificar archivos.",
    )
    return parser.parse_args()


def iter_gesture_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in VALID_EXTENSIONS
    )


def trim_anchor(path: Path, *, dry_run: bool) -> GestureResult | None:
    with Image.open(path) as image:
        rgba = image.convert("RGBA")
        bbox = rgba.getbbox()
        if not bbox:
            return None

        left, top, right, bottom = bbox
        width_before, height_before = rgba.size
        trim_right = width_before - right
        trim_bottom = height_before - bottom

        if trim_right == 0 and trim_bottom == 0:
            return GestureResult(
                path=path,
                width_before=width_before,
                height_before=height_before,
                width_after=width_before,
                height_after=height_before,
                trim_right=0,
                trim_bottom=0,
            )

        cropped = rgba.crop((0, 0, right, bottom))
        if not dry_run:
            cropped.save(path)

        width_after, height_after = cropped.size
        return GestureResult(
            path=path,
            width_before=width_before,
            height_before=height_before,
            width_after=width_after,
            height_after=height_after,
            trim_right=trim_right,
            trim_bottom=trim_bottom,
        )


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    if not root.exists():
        raise FileNotFoundError(f"No existe el directorio raiz de gestos: {root}")

    files = iter_gesture_files(root)
    if not files:
        print(f"No se encontraron gestos en: {root}")
        return 0

    changed = 0
    for path in files:
        result = trim_anchor(path, dry_run=args.dry_run)
        if result is None:
            print(f"SKIP {path.relative_to(root)} | sin pixeles visibles")
            continue

        changed_flag = result.trim_right > 0 or result.trim_bottom > 0
        if changed_flag:
            changed += 1
        print(
            f"{'PLAN' if args.dry_run else 'DONE'} "
            f"{path.relative_to(root)} | "
            f"{result.width_before}x{result.height_before} -> "
            f"{result.width_after}x{result.height_after} | "
            f"trim_right={result.trim_right} trim_bottom={result.trim_bottom}"
        )

    print(
        f"{'Dry run' if args.dry_run else 'Normalizacion'} completada. "
        f"Archivos con ajuste de ancla: {changed}/{len(files)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
