from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from ..automation_models import SourceConfig
from .prcdn import discover_prcdn_assets
from .schedule import resolve_publication_date


def _normalize_classes(value: str) -> set[str]:
    return {item.strip() for item in value.split() if item.strip()}


@dataclass(slots=True)
class SimpleSelector:
    tag: str | None = None
    class_name: str | None = None

    @classmethod
    def parse(cls, raw: str) -> "SimpleSelector":
        token = raw.strip()
        if not token:
            return cls()
        if " " in token:
            token = token.split()[-1]
        if token.startswith("."):
            return cls(class_name=token[1:])
        if "." in token:
            tag, class_name = token.split(".", 1)
            return cls(tag=tag or None, class_name=class_name or None)
        return cls(tag=token)

    def matches(self, *, tag: str, classes: set[str]) -> bool:
        if self.tag and self.tag != tag:
            return False
        if self.class_name and self.class_name not in classes:
            return False
        return True


class AssetDiscoveryParser(HTMLParser):
    def __init__(
        self,
        *,
        base_url: str,
        front_page_selector: str | None,
        supporting_page_selector: str | None,
        headline_selector: str | None,
        max_supporting_pages: int,
    ) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.front_page_selectors = _parse_selector_group(front_page_selector)
        self.supporting_page_selectors = _parse_selector_group(supporting_page_selector)
        self.headline_selectors = _parse_selector_group(headline_selector)
        self.max_supporting_pages = max_supporting_pages
        self.front_page_url: str | None = None
        self.supporting_pages: list[str] = []
        self.headline_candidates: list[str] = []
        self._headline_capture_stack: list[bool] = []
        self._headline_text_buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: value or "" for key, value in attrs}
        classes = _normalize_classes(attr_map.get("class", ""))

        if tag == "img":
            src = attr_map.get("src") or attr_map.get("data-src") or attr_map.get("data-original")
            if src:
                absolute_src = urljoin(self.base_url, src)
                if self.front_page_url is None and _matches_any(self.front_page_selectors, tag=tag, classes=classes):
                    self.front_page_url = absolute_src
                elif self.front_page_url is None and not self.front_page_selectors:
                    self.front_page_url = absolute_src

                if (
                    len(self.supporting_pages) < self.max_supporting_pages
                    and _matches_any(self.supporting_page_selectors, tag=tag, classes=classes)
                ):
                    self._append_supporting_page(absolute_src)

        if tag == "a" and len(self.supporting_pages) < self.max_supporting_pages:
            href = attr_map.get("href")
            if href and _matches_any(self.supporting_page_selectors, tag=tag, classes=classes):
                self._append_supporting_page(urljoin(self.base_url, href))

        capture_headline = _matches_any(self.headline_selectors, tag=tag, classes=classes)
        self._headline_capture_stack.append(capture_headline)
        if capture_headline:
            self._headline_text_buffer.append("")

    def handle_data(self, data: str) -> None:
        if self._headline_capture_stack and self._headline_capture_stack[-1]:
            self._headline_text_buffer[-1] += data

    def handle_endtag(self, tag: str) -> None:
        if not self._headline_capture_stack:
            return
        was_capturing = self._headline_capture_stack.pop()
        if was_capturing:
            text = " ".join(self._headline_text_buffer.pop().split()).strip()
            if text and text not in self.headline_candidates:
                self.headline_candidates.append(text)

    def _append_supporting_page(self, url: str) -> None:
        if url not in self.supporting_pages:
            self.supporting_pages.append(url)


def _parse_selector_group(raw: str | None) -> list[SimpleSelector]:
    if not raw:
        return []
    return [SimpleSelector.parse(token) for token in raw.split(",") if token.strip()]


def _matches_any(selectors: list[SimpleSelector], *, tag: str, classes: set[str]) -> bool:
    if not selectors:
        return False
    return any(selector.matches(tag=tag, classes=classes) for selector in selectors)


def fetch_html(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            )
        },
    )
    with urlopen(request, timeout=60) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def build_source_url(source: SourceConfig, *, job_date: str) -> str:
    pattern = source.discovery.get("front_page_url_pattern")
    if not pattern:
        return source.base_url
    publication_date = resolve_publication_date(source=source, job_date=job_date)
    if publication_date is None:
        return source.base_url
    return str(pattern).format(date=publication_date)


def discover_source_assets(
    *,
    source: SourceConfig,
    job_date: str,
    source_url: str | None = None,
    html: str | None = None,
    max_supporting_pages: int = 3,
) -> dict[str, object]:
    publication_date = resolve_publication_date(source=source, job_date=job_date)
    if publication_date is None:
        return {
            "source_url": source_url or source.base_url,
            "issue_date": None,
            "front_page_url": None,
            "supporting_pages": [],
            "headline_candidates": [],
            "discovery_type": source.discovery.get("type", "html"),
            "status": "no_publication_for_date",
        }

    if str(source.discovery.get("type", "")).strip() == "prcdn_image_sequence":
        return discover_prcdn_assets(
            source=source,
            job_date=job_date,
            max_supporting_pages=max_supporting_pages,
        )

    resolved_source_url = source_url or build_source_url(source, job_date=job_date)
    html_content = html if html is not None else fetch_html(resolved_source_url)
    selectors = source.selectors
    parser = AssetDiscoveryParser(
        base_url=resolved_source_url,
        front_page_selector=str(selectors.get("front_page_image") or ""),
        supporting_page_selector=str(
            selectors.get("supporting_page_images")
            or selectors.get("page_images")
            or selectors.get("supporting_page_links")
            or ""
        ),
        headline_selector=str(selectors.get("article_blocks") or ""),
        max_supporting_pages=max_supporting_pages,
    )
    parser.feed(html_content)

    supporting_pages = [
        {
            "role": "supporting_page",
            "label": f"Pagina {index + 2}",
            "page_number": index + 2,
            "source_url": url,
        }
        for index, url in enumerate(parser.supporting_pages[:max_supporting_pages])
    ]

    return {
        "source_url": resolved_source_url,
        "issue_date": publication_date,
        "front_page_url": parser.front_page_url,
        "supporting_pages": supporting_pages,
        "headline_candidates": parser.headline_candidates[:5],
        "discovery_type": source.discovery.get("type", "html"),
        "status": "ok",
    }
