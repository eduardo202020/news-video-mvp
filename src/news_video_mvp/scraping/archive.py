from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
import json
from pathlib import Path
from urllib.request import Request, urlopen
import shutil

from ..automation_models import SourceConfig, write_json
from ..project import get_project_dir
from .assets import infer_extension_from_url
from .discovery import discover_source_assets


def _download_binary(source_url: str, destination: Path) -> Path:
    request = Request(
        source_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            )
        },
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(request, timeout=60) as response:
        destination.write_bytes(response.read())
    return destination


def resolve_source_storage_dir(
    *,
    source: SourceConfig,
    job_date: str,
    project_dir: Path | None = None,
) -> Path:
    root = project_dir or get_project_dir()
    folder_pattern = str(source.storage.get("folder_pattern") or f"data/raw/{source.source_id}/{{date}}/")
    return root / Path(folder_pattern.format(date=job_date))


def _write_archive_summary(
    *,
    project_dir: Path,
    job_date: str,
    sources_dir: Path,
    results: list[dict[str, object]],
) -> Path:
    counts = Counter(str(item.get("status") or "unknown") for item in results)
    grouped_sources: dict[str, list[str]] = {}
    for item in results:
        status = str(item.get("status") or "unknown")
        source_id = str(item.get("source_id") or "unknown")
        grouped_sources.setdefault(status, []).append(source_id)

    ordered_statuses = [
        "archived",
        "skipped_no_publication",
        "skipped",
        "unknown",
    ]
    summary_dir = project_dir / "data" / "raw" / "archive-summary"
    summary_path = summary_dir / f"{job_date}.json"
    latest_path = summary_dir / "latest.json"
    payload = {
        "date": job_date,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "sources_dir": str(sources_dir.as_posix()),
        "counts": {
            status: counts[status]
            for status in ordered_statuses
            if counts.get(status, 0)
        },
        "grouped_sources": {
            status: grouped_sources[status]
            for status in ordered_statuses
            if grouped_sources.get(status)
        },
        "results": results,
    }
    write_json(summary_path, payload)
    write_json(latest_path, payload)
    return summary_path


def archive_source_scrape(
    *,
    source_config_path: Path,
    job_date: str,
    source_url: str | None = None,
    max_supporting_pages: int = 3,
) -> Path:
    project_dir = get_project_dir()
    source = SourceConfig.load(source_config_path)
    discovery = discover_source_assets(
        source=source,
        job_date=job_date,
        source_url=source_url,
        max_supporting_pages=max_supporting_pages,
    )
    storage_dir = resolve_source_storage_dir(source=source, job_date=job_date, project_dir=project_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)

    if discovery.get("status") == "no_publication_for_date":
        payload = {
            "source_id": source.source_id,
            "display_name": source.display_name,
            "date": job_date,
            "issue_date": None,
            "source_url": discovery.get("source_url"),
            "discovery_type": discovery.get("discovery_type"),
            "headline_candidates": [],
            "pages": [],
            "status": "no_publication_for_date",
            "archived_at": datetime.now().isoformat(timespec="seconds"),
        }
        return write_json(storage_dir / "scrape-manifest.json", payload)

    archived_pages: list[dict[str, object]] = []
    for index, page in enumerate(discovery.get("pages", []), start=1):
        page_url = str(page.get("source_url") or "")
        if not page_url:
            continue
        role = str(page.get("role") or "supporting_page")
        page_number = int(page.get("page_number") or index)
        label = str(page.get("label") or f"Pagina {page_number}")
        scale = page.get("scale")
        stem = "front-page" if role == "front_page" else f"page-{page_number:02d}"
        suffix = infer_extension_from_url(page_url, ".jpg")
        destination = storage_dir / f"{stem}{suffix}"
        _download_binary(page_url, destination)
        archived_pages.append(
            {
                "role": role,
                "label": label,
                "page_number": page_number,
                "scale": int(scale) if scale is not None else None,
                "source_url": page_url,
                "local_path": destination.resolve().relative_to(project_dir).as_posix(),
            }
        )

    payload = {
        "source_id": source.source_id,
        "display_name": source.display_name,
        "date": job_date,
        "issue_date": discovery.get("issue_date"),
        "source_url": discovery.get("source_url"),
        "discovery_type": discovery.get("discovery_type"),
        "headline_candidates": discovery.get("headline_candidates", []),
        "pages": archived_pages,
        "archived_at": datetime.now().isoformat(timespec="seconds"),
    }
    probe_path = storage_dir / "page-count-probe.json"
    if probe_path.exists():
        probe_payload = json.loads(probe_path.read_text(encoding="utf-8"))
        payload["page_count_probe"] = {
            "page_count": probe_payload.get("page_count"),
            "first_page": probe_payload.get("first_page"),
            "last_page": probe_payload.get("last_page"),
            "max_probe_pages": probe_payload.get("max_probe_pages"),
            "probe_path": probe_path.resolve().relative_to(project_dir).as_posix(),
        }
    return write_json(storage_dir / "scrape-manifest.json", payload)


def prune_source_storage(
    *,
    source_config_path: Path,
    retention_days: int = 7,
) -> list[Path]:
    source = SourceConfig.load(source_config_path)
    project_dir = get_project_dir()
    folder_pattern = str(source.storage.get("folder_pattern") or f"data/raw/{source.source_id}/{{date}}/")
    sample_dir = project_dir / Path(folder_pattern.format(date="2000-01-01"))
    source_root = sample_dir.parent
    if not source_root.exists():
        return []

    cutoff = date.today() - timedelta(days=retention_days)
    deleted: list[Path] = []
    for child in source_root.iterdir():
        if not child.is_dir():
            continue
        try:
            folder_date = date.fromisoformat(child.name)
        except ValueError:
            continue
        if folder_date < cutoff:
            shutil.rmtree(child, ignore_errors=True)
            deleted.append(child)
    return deleted


def archive_all_sources(
    *,
    sources_dir: Path,
    job_date: str,
    max_supporting_pages: int = 3,
    retention_days: int = 7,
) -> list[dict[str, object]]:
    project_dir = get_project_dir()
    results: list[dict[str, object]] = []
    for source_config_path in sorted(sources_dir.glob("*.json")):
        source = SourceConfig.load(source_config_path)
        if "example.com" in source.base_url:
            results.append(
                {
                    "source_id": source.source_id,
                    "status": "skipped",
                    "reason": "source_config_placeholder",
                }
            )
            continue
        manifest_path = archive_source_scrape(
            source_config_path=source_config_path,
            job_date=job_date,
            max_supporting_pages=max_supporting_pages,
        )
        manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        deleted = prune_source_storage(
            source_config_path=source_config_path,
            retention_days=retention_days,
        )
        result_status = "archived"
        if manifest_payload.get("status") == "no_publication_for_date":
            result_status = "skipped_no_publication"
        results.append(
            {
                "source_id": source.source_id,
                "status": result_status,
                "manifest_path": manifest_path.resolve().relative_to(project_dir).as_posix(),
                "reason": manifest_payload.get("status"),
                "deleted_folders": [path.name for path in deleted],
            }
        )
    summary_path = _write_archive_summary(
        project_dir=project_dir,
        job_date=job_date,
        sources_dir=sources_dir,
        results=results,
    )
    for item in results:
        item["summary_path"] = summary_path.resolve().relative_to(project_dir).as_posix()
    return results
