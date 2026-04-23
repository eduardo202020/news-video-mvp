from __future__ import annotations

import json
from pathlib import Path
import sys


PROJECT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from news_video_mvp.scraping.assets import trim_white_margins


def main() -> int:
    job_date = sys.argv[1] if len(sys.argv) > 1 else "2026-04-21"
    threshold = int(sys.argv[2]) if len(sys.argv) > 2 else 245
    padding = int(sys.argv[3]) if len(sys.argv) > 3 else 24
    source_paths = sorted((PROJECT_DIR / "data" / "jobs" / job_date).glob("*/input/front-page.*"))
    output_dir = PROJECT_DIR / "data" / "tests" / "trim-front-pages" / job_date
    output_dir.mkdir(parents=True, exist_ok=True)

    if not source_paths:
        print(json.dumps({"status": "no_files", "job_date": job_date}, ensure_ascii=False, indent=2))
        return 0

    results: list[dict[str, object]] = []
    for source_path in source_paths:
        output_path = output_dir / source_path.parent.parent.name / source_path.name
        result = trim_white_margins(
            source_path=source_path,
            output_path=output_path,
            threshold=threshold,
            padding=padding,
        )
        results.append(
            {
                "job_id": source_path.parent.parent.name,
                "source": Path(result["source_path"]).relative_to(PROJECT_DIR).as_posix(),
                "output": Path(result["output_path"]).relative_to(PROJECT_DIR).as_posix(),
                "bbox": result["bbox"],
                "padding": result["padding"],
                "original_size": result["original_size"],
                "cropped_size": result["cropped_size"],
            }
        )

    summary_path = output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "job_date": job_date,
                "threshold": threshold,
                "padding": padding,
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(summary_path.relative_to(PROJECT_DIR).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
