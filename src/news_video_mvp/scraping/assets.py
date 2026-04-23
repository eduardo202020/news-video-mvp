from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
from tempfile import NamedTemporaryFile
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from PIL import Image

from ..automation_models import read_json, write_json
from ..project import get_project_dir

FRONT_PAGE_TRIM_THRESHOLD = 245
FRONT_PAGE_TRIM_PADDING = 20


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


def _find_non_white_bbox(image: Image.Image, *, threshold: int = 245) -> tuple[int, int, int, int] | None:
    rgb_image = image.convert("RGB")
    width, height = rgb_image.size
    pixels = rgb_image.load()
    min_x = width
    min_y = height
    max_x = -1
    max_y = -1

    for y in range(height):
        for x in range(width):
            red, green, blue = pixels[x, y]
            if red < threshold or green < threshold or blue < threshold:
                if x < min_x:
                    min_x = x
                if y < min_y:
                    min_y = y
                if x > max_x:
                    max_x = x
                if y > max_y:
                    max_y = y

    if max_x < min_x or max_y < min_y:
        return None
    return (min_x, min_y, max_x + 1, max_y + 1)


def trim_white_margins(
    *,
    source_path: Path,
    output_path: Path,
    threshold: int = 245,
    padding: int = 24,
) -> dict[str, object]:
    source_path = source_path.resolve()
    output_path = output_path.resolve()
    with Image.open(source_path) as image:
        bbox = _find_non_white_bbox(image, threshold=threshold)
        original_size = image.size
        if bbox is None:
            cropped = image.copy()
            bbox = (0, 0, original_size[0], original_size[1])
        else:
            padded_bbox = (
                max(0, bbox[0] - padding),
                max(0, bbox[1] - padding),
                min(original_size[0], bbox[2] + padding),
                min(original_size[1], bbox[3] + padding),
            )
            bbox = padded_bbox
            cropped = image.crop(bbox)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cropped.save(output_path)
        cropped_size = cropped.size

    return {
        "source_path": source_path.as_posix(),
        "output_path": output_path.as_posix(),
        "threshold": threshold,
        "padding": padding,
        "bbox": {
            "left": int(bbox[0]),
            "top": int(bbox[1]),
            "right": int(bbox[2]),
            "bottom": int(bbox[3]),
        },
        "original_size": {"width": int(original_size[0]), "height": int(original_size[1])},
        "cropped_size": {"width": int(cropped_size[0]), "height": int(cropped_size[1])},
    }


def _trim_front_page_in_place(asset_path: Path) -> None:
    asset_path = asset_path.resolve()
    with NamedTemporaryFile(
        suffix=asset_path.suffix,
        prefix=f"{asset_path.stem}-trim-",
        dir=str(asset_path.parent),
        delete=False,
    ) as temp_file:
        temp_path = Path(temp_file.name)
    try:
        trim_white_margins(
            source_path=asset_path,
            output_path=temp_path,
            threshold=FRONT_PAGE_TRIM_THRESHOLD,
            padding=FRONT_PAGE_TRIM_PADDING,
        )
        shutil.move(str(temp_path), str(asset_path))
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


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
    staged = _stage_local_or_remote_asset(
        destination_dir=job_dir / "input",
        destination_name="front-page",
        source_image=front_page_image,
        source_url=front_page_url,
        download=download_front_page,
    )
    if staged is not None:
        _trim_front_page_in_place(staged)
    return staged


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
