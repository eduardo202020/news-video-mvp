from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ..automation_models import read_json, write_json
from ..project import get_project_dir


def infer_extension_from_url(url: str, default: str = ".jpg") -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    return suffix or default


def _download_asset_with_headers(*, source_url: str, destination: Path) -> None:
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


def _stage_local_or_remote_asset(
    *,
    destination_dir: Path,
    destination_name: str,
    source_image: Path | None,
    source_url: str | None,
    download: bool,
    default_extension: str = ".jpg",
) -> Path | None:
    if source_image is not None:
        if not source_image.exists():
            raise FileNotFoundError(f"No existe el asset local: {source_image}")
        destination = destination_dir / f"{destination_name}{source_image.suffix.lower()}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_image, destination)
        return destination

    if download and source_url:
        destination = destination_dir / f"{destination_name}{infer_extension_from_url(source_url, default_extension)}"
        _download_asset_with_headers(source_url=source_url, destination=destination)
        return destination

    return None


def stage_front_page_asset(
    *,
    job_dir: Path,
    front_page_image: Path | None,
    front_page_url: str | None,
    download_front_page: bool,
) -> Path | None:
    return _stage_local_or_remote_asset(
        destination_dir=job_dir / "input",
        destination_name="front-page",
        source_image=front_page_image,
        source_url=front_page_url,
        download=download_front_page,
    )


def stage_supporting_page_asset(
    *,
    job_dir: Path,
    page_number: int,
    page_image: Path | None,
    page_url: str | None,
    download_page: bool,
) -> Path | None:
    return _stage_local_or_remote_asset(
        destination_dir=job_dir / "input" / "pages",
        destination_name=f"page-{page_number:02d}",
        source_image=page_image,
        source_url=page_url,
        download=download_page,
    )


def _build_page_asset_record(
    *,
    asset_path: Path,
    source_url: str | None,
    role: str,
    label: str,
    page_number: int | None,
    project_dir: Path,
) -> dict[str, str | int | None]:
    return {
        "role": role,
        "label": label,
        "page_number": page_number,
        "source_url": source_url,
        "local_path": asset_path.resolve().relative_to(project_dir).as_posix(),
    }


def build_input_assets(
    *,
    project_dir: Path,
    source_config_path: Path,
    source_url: str,
    front_page_url: str | None,
    front_page_asset: Path | None,
    supporting_pages: list[dict[str, str | int | None]] | None = None,
) -> dict[str, object]:
    pages = list(supporting_pages or [])
    if front_page_asset is not None:
        pages.insert(
            0,
            _build_page_asset_record(
                asset_path=front_page_asset,
                source_url=front_page_url,
                role="front_page",
                label="Portada",
                page_number=1,
                project_dir=project_dir,
            ),
        )

    return {
        "front_page_image": front_page_asset.resolve().relative_to(project_dir).as_posix()
        if front_page_asset
        else None,
        "front_page_url": front_page_url,
        "source_url": source_url,
        "source_config": source_config_path.resolve().relative_to(project_dir).as_posix(),
        "pages": pages,
    }


def ingest_supporting_pages(
    *,
    job_manifest_path: Path,
    page_urls: list[str] | None = None,
    page_images: list[Path] | None = None,
) -> Path:
    page_urls = page_urls or []
    page_images = page_images or []
    if not page_urls and not page_images:
        raise ValueError("Debes proporcionar al menos un `--page-url` o `--page-image`.")

    project_dir = get_project_dir()
    job = read_json(job_manifest_path)
    job_dir = job_manifest_path.parent
    pages = list(job.get("input_assets", {}).get("pages", []))

    next_page_number = max(
        [int(page.get("page_number") or 1) for page in pages if page.get("page_number") is not None] or [1]
    )

    for page_image in page_images:
        next_page_number += 1
        staged = _stage_local_or_remote_asset(
            destination_dir=job_dir / "input" / "pages",
            destination_name=f"page-{next_page_number:02d}",
            source_image=page_image,
            source_url=None,
            download=False,
        )
        if staged is None:
            continue
        pages.append(
            _build_page_asset_record(
                asset_path=staged,
                source_url=None,
                role="supporting_page",
                label=f"Pagina {next_page_number}",
                page_number=next_page_number,
                project_dir=project_dir,
            )
        )

    for page_url in page_urls:
        next_page_number += 1
        staged = _stage_local_or_remote_asset(
            destination_dir=job_dir / "input" / "pages",
            destination_name=f"page-{next_page_number:02d}",
            source_image=None,
            source_url=page_url,
            download=True,
        )
        if staged is None:
            continue
        pages.append(
            _build_page_asset_record(
                asset_path=staged,
                source_url=page_url,
                role="supporting_page",
                label=f"Pagina {next_page_number}",
                page_number=next_page_number,
                project_dir=project_dir,
            )
        )

    timestamp = datetime.now().isoformat(timespec="seconds")
    job.setdefault("input_assets", {})["pages"] = pages
    job["status"] = "scraped"
    job.setdefault("audit", {})["updated_at"] = timestamp
    job["audit"].setdefault("events", []).append(
        {
            "stage": "scrape_pages",
            "status": "completed",
            "timestamp": timestamp,
            "details": f"Se registraron {len(page_urls) + len(page_images)} paginas de apoyo en el job.",
        }
    )
    return write_json(job_manifest_path, job)
