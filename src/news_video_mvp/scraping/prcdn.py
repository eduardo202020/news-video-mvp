from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..automation_models import SourceConfig
from .schedule import resolve_publication_date


@dataclass(slots=True)
class PrcdnDiscoverySettings:
    base_image_url: str
    file_code: str
    suffix: str = "00000000001001"
    page_start: int = 1
    page_end: int = 10
    scale_start: int = 46
    scale_end: int = 300
    stop_after_missing_page: bool = True
    missing_pages_tolerance: int = 1


def build_prcdn_image_url(
    *,
    base_image_url: str,
    file_code: str,
    job_date: str,
    page: int,
    scale: int,
    suffix: str = "00000000001001",
) -> str:
    compact_date = job_date.replace("-", "")
    params = {
        "file": f"{file_code}{compact_date}{suffix}",
        "page": str(page),
        "scale": str(scale),
    }
    return f"{base_image_url}?{urlencode(params)}"


def _request_ok(url: str) -> bool:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            )
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            content_type = response.headers.get_content_type()
            return response.status == 200 and content_type.startswith("image/")
    except Exception:
        return False


def _find_best_scale_for_page(
    *,
    settings: PrcdnDiscoverySettings,
    job_date: str,
    page: int,
) -> tuple[int | None, str | None]:
    # Asumimos que si un scale alto funciona, todos los menores tambien.
    # Eso permite buscar el maximo valido con pocas requests.
    result_cache: dict[int, bool] = {}
    url_cache: dict[int, str] = {}

    def check(scale: int) -> bool:
        if scale not in result_cache:
            url = build_prcdn_image_url(
                base_image_url=settings.base_image_url,
                file_code=settings.file_code,
                job_date=job_date,
                page=page,
                scale=scale,
                suffix=settings.suffix,
            )
            url_cache[scale] = url
            result_cache[scale] = _request_ok(url)
        return result_cache[scale]

    if not check(settings.scale_start):
        return None, None

    low = settings.scale_start
    high = settings.scale_end
    best = low

    while low <= high:
        mid = (low + high) // 2
        if check(mid):
            best = mid
            low = mid + 1
        else:
            high = mid - 1

    return best, url_cache[best]


def _load_prcdn_settings(source: SourceConfig) -> PrcdnDiscoverySettings:
    discovery = source.discovery
    return PrcdnDiscoverySettings(
        base_image_url=str(discovery.get("base_image_url") or source.base_url),
        file_code=str(discovery["file_code"]),
        suffix=str(discovery.get("suffix", "00000000001001")),
        page_start=int(discovery.get("page_start", 1)),
        page_end=int(discovery.get("page_end", 10)),
        scale_start=int(discovery.get("scale_start", 46)),
        scale_end=int(discovery.get("scale_end", 300)),
        stop_after_missing_page=bool(discovery.get("stop_after_missing_page", True)),
        missing_pages_tolerance=max(1, int(discovery.get("missing_pages_tolerance", 1))),
    )


def discover_prcdn_assets(
    *,
    source: SourceConfig,
    job_date: str,
    max_supporting_pages: int = 3,
) -> dict[str, object]:
    settings = _load_prcdn_settings(source)
    issue_date = resolve_publication_date(source=source, job_date=job_date)
    if issue_date is None:
        return {
            "source_url": settings.base_image_url,
            "issue_date": None,
            "front_page_url": None,
            "supporting_pages": [],
            "headline_candidates": [],
            "discovery_type": "prcdn_image_sequence",
            "pages": [],
            "status": "no_publication_for_date",
        }
    discovered_pages: list[dict[str, object]] = []
    max_total_pages = max(1, max_supporting_pages + 1)
    consecutive_missing_pages = 0

    for page in range(settings.page_start, settings.page_end + 1):
        if len(discovered_pages) >= max_total_pages:
            break
        best_scale, best_url = _find_best_scale_for_page(
            settings=settings,
            job_date=issue_date,
            page=page,
        )
        if best_scale is None or best_url is None:
            consecutive_missing_pages += 1
            if (
                settings.stop_after_missing_page
                and consecutive_missing_pages >= settings.missing_pages_tolerance
            ):
                break
            continue
        consecutive_missing_pages = 0

        discovered_pages.append(
            {
                "role": "front_page" if page == settings.page_start else "supporting_page",
                "label": "Portada" if page == settings.page_start else f"Pagina {page}",
                "page_number": page,
                "source_url": best_url,
                "scale": best_scale,
            }
        )

    front_page_url = None
    supporting_pages = []
    for page in discovered_pages:
        if page["role"] == "front_page" and front_page_url is None:
            front_page_url = str(page["source_url"])
        else:
            supporting_pages.append(page)

    return {
        "source_url": settings.base_image_url,
        "issue_date": issue_date,
        "front_page_url": front_page_url,
        "supporting_pages": supporting_pages,
        "headline_candidates": [],
        "discovery_type": "prcdn_image_sequence",
        "pages": discovered_pages,
        "status": "ok",
    }


def resolve_prcdn_pages(
    *,
    source: SourceConfig,
    job_date: str,
    page_numbers: list[int],
) -> dict[str, object]:
    settings = _load_prcdn_settings(source)
    issue_date = resolve_publication_date(source=source, job_date=job_date)
    if issue_date is None:
        return {
            "source_url": settings.base_image_url,
            "issue_date": None,
            "pages": [],
            "discovery_type": "prcdn_image_sequence",
            "status": "no_publication_for_date",
        }

    resolved_pages: list[dict[str, object]] = []
    for page_number in sorted(dict.fromkeys(page_numbers)):
        best_scale, best_url = _find_best_scale_for_page(
            settings=settings,
            job_date=issue_date,
            page=page_number,
        )
        if best_scale is None or best_url is None:
            continue
        resolved_pages.append(
            {
                "role": "front_page" if page_number == settings.page_start else "supporting_page",
                "label": "Portada" if page_number == settings.page_start else f"Pagina {page_number}",
                "page_number": page_number,
                "source_url": best_url,
                "scale": best_scale,
            }
        )

    return {
        "source_url": settings.base_image_url,
        "issue_date": issue_date,
        "pages": resolved_pages,
        "discovery_type": "prcdn_image_sequence",
        "status": "ok",
    }


def probe_prcdn_page_count(
    *,
    source: SourceConfig,
    job_date: str,
    max_probe_pages: int | None = None,
) -> dict[str, object]:
    settings = _load_prcdn_settings(source)
    issue_date = resolve_publication_date(source=source, job_date=job_date)
    if issue_date is None:
        return {
            "source_id": source.source_id,
            "display_name": source.display_name,
            "job_date": job_date,
            "issue_date": None,
            "page_count": 0,
            "first_page": None,
            "last_page": None,
            "max_probe_pages": max(settings.page_start, max_probe_pages or settings.page_end),
            "scale_range": {
                "start": settings.scale_start,
                "end": settings.scale_end,
            },
            "valid_pages": [],
            "probe_type": "prcdn_image_sequence",
            "status": "no_publication_for_date",
        }
    page_limit = max(settings.page_start, max_probe_pages or settings.page_end)
    valid_pages: list[dict[str, object]] = []
    consecutive_missing_pages = 0

    for page in range(settings.page_start, page_limit + 1):
        best_scale, best_url = _find_best_scale_for_page(
            settings=settings,
            job_date=issue_date,
            page=page,
        )
        if best_scale is None or best_url is None:
            consecutive_missing_pages += 1
            if (
                settings.stop_after_missing_page
                and consecutive_missing_pages >= settings.missing_pages_tolerance
            ):
                break
            continue

        consecutive_missing_pages = 0
        valid_pages.append(
            {
                "page_number": page,
                "scale": best_scale,
                "source_url": best_url,
            }
        )

    page_count = 0
    if valid_pages:
        page_count = int(valid_pages[-1]["page_number"])

    return {
        "source_id": source.source_id,
        "display_name": source.display_name,
        "job_date": job_date,
        "issue_date": issue_date,
        "page_count": page_count,
        "first_page": valid_pages[0]["page_number"] if valid_pages else None,
        "last_page": valid_pages[-1]["page_number"] if valid_pages else None,
        "max_probe_pages": page_limit,
        "scale_range": {
            "start": settings.scale_start,
            "end": settings.scale_end,
        },
        "valid_pages": valid_pages,
        "probe_type": "prcdn_image_sequence",
        "status": "ok",
    }
