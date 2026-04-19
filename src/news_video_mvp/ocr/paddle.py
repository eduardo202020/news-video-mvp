from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
from typing import Any


class PaddleOCRError(RuntimeError):
    """Raised when PaddleOCR is unavailable or fails."""


def _group_text_lines(*, texts: list[str], boxes: list[list[list[float]]]) -> list[str]:
    items: list[dict[str, Any]] = []
    for text, box in zip(texts, boxes):
        clean = " ".join(str(text).split()).strip()
        if not clean:
            continue
        points = [(float(point[0]), float(point[1])) for point in box]
        ys = [point[1] for point in points]
        xs = [point[0] for point in points]
        items.append(
            {
                "text": clean,
                "top": min(ys),
                "bottom": max(ys),
                "left": min(xs),
                "height": max(1.0, max(ys) - min(ys)),
            }
        )

    items.sort(key=lambda item: (item["top"], item["left"]))
    grouped: list[dict[str, Any]] = []
    for item in items:
        if not grouped:
            grouped.append(
                {
                    "top": item["top"],
                    "bottom": item["bottom"],
                    "height": item["height"],
                    "parts": [item],
                }
            )
            continue

        current = grouped[-1]
        vertical_gap = abs(item["top"] - current["top"])
        tolerance = max(current["height"], item["height"]) * 0.6
        if vertical_gap <= tolerance:
            current["parts"].append(item)
            current["bottom"] = max(current["bottom"], item["bottom"])
            current["height"] = max(current["height"], item["height"])
            continue

        grouped.append(
            {
                "top": item["top"],
                "bottom": item["bottom"],
                "height": item["height"],
                "parts": [item],
            }
        )

    lines: list[str] = []
    for group in grouped:
        ordered_parts = sorted(group["parts"], key=lambda part: part["left"])
        line = " ".join(part["text"] for part in ordered_parts).strip()
        if line:
            lines.append(line)
    return lines


@lru_cache(maxsize=2)
def _get_paddleocr(lang: str):
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    try:
        from paddleocr import PaddleOCR
    except Exception as exc:  # pragma: no cover - depends on optional install
        raise PaddleOCRError(
            "PaddleOCR no está instalado. Instala las dependencias opcionales de OCR para usar este motor."
        ) from exc

    try:
        return PaddleOCR(lang=lang)
    except Exception as exc:  # pragma: no cover - runtime/model setup
        raise PaddleOCRError(f"No se pudo inicializar PaddleOCR: {exc}") from exc


def extract_text_with_paddleocr(
    *,
    image_path: Path,
    lang: str = "es",
) -> dict[str, Any]:
    if not image_path.exists():
        raise FileNotFoundError(f"No existe la imagen para OCR: {image_path}")

    ocr = _get_paddleocr(lang)
    try:
        result = ocr.predict(str(image_path))
    except Exception as exc:  # pragma: no cover - runtime inference
        raise PaddleOCRError(f"PaddleOCR falló al procesar {image_path.name}: {exc}") from exc

    if not result:
        return {
            "text": "",
            "lines": [],
            "items": [],
        }

    first = result[0]
    texts = [str(text).strip() for text in first.get("rec_texts", [])]
    scores = [float(score) for score in first.get("rec_scores", [])]
    det_boxes = [box.tolist() if hasattr(box, "tolist") else box for box in first.get("dt_polys", [])]
    rec_boxes = [box.tolist() if hasattr(box, "tolist") else box for box in first.get("rec_boxes", [])]
    items = [
        {
            "text": text,
            "score": score,
            "box": box,
        }
        for text, score, box in zip(texts, scores, rec_boxes)
        if text
    ]
    boxes_for_grouping = det_boxes if det_boxes and len(det_boxes) == len(texts) else rec_boxes
    lines = _group_text_lines(texts=texts, boxes=boxes_for_grouping)
    return {
        "text": "\n".join(lines).strip(),
        "lines": lines,
        "items": items,
    }
