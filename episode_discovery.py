"""Best-effort episode discovery from public, server-rendered HTML only.

This intentionally does not execute JavaScript, call undocumented APIs, log in,
or bypass paywalls/DRM. Sites that do not expose episode links and media URLs
in public HTML require a supported, authorized source-specific integration.
"""
from __future__ import annotations

import re
import socket
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable
from urllib.parse import urldefrag, urljoin, urlsplit

from cddl.http import HttpError, RetryPolicy
from safe_http import DownloadBudget, DownloadBudgetExceeded, SafeHttpSession, UnsafeUrlError, validate_public_url

MAX_DISCOVERY_BYTES = 32 * 1024 * 1024
MAX_DISCOVERY_SECONDS = 90
MAX_EPISODE_PAGES = 100
MAX_THUMBNAILS = 100
MAX_THUMBNAIL_BYTES = 128 * 1024
_ALLOWED_THUMBNAIL_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

_EPISODE_PATTERNS = (
    re.compile(r"第\s*0*(\d{1,4})\s*[集话話期]", re.IGNORECASE),
    re.compile(r"\b(?:episode|ep)\s*[#._:\- ]*0*(\d{1,4})\b", re.IGNORECASE),
    re.compile(r"ភាគ\s*0*(\d{1,4})", re.IGNORECASE),
)
_EPISODE_URL_PATTERN = re.compile(r"/(?:episode|ep|e)[/_-]?0*(\d{1,4})(?:/|[._-]|$)", re.IGNORECASE)


@dataclass(frozen=True)
class Episode:
    number: int
    title: str
    page_url: str
    media_url: str | None
    thumbnail_bytes: bytes | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DiscoveryResult:
    series_title: str
    episodes: list[Episode]
    truncated: bool = False


class DiscoveryError(ValueError):
    """A safe, user-facing source discovery error."""


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchors: list[dict[str, str]] = []
        self.media_urls: list[str] = []
        self.title_parts: list[str] = []
        self.meta_title = ""
        self.meta_image = ""
        self._in_title = False
        self._anchor: dict[str, object] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): (value or "") for key, value in attrs}
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = (values.get("property") or values.get("name") or "").lower()
            content = values.get("content", "").strip()
            if key in {"og:title", "twitter:title"} and content and not self.meta_title:
                self.meta_title = content
            elif key in {"og:image", "twitter:image"} and content and not self.meta_image:
                self.meta_image = content
            elif key in {"og:video", "og:video:url", "twitter:player:stream"} and content:
                self.media_urls.append(content)
        elif tag == "a":
            if self._anchor is None:
                self._anchor = {
                    "href": values.get("href", "").strip(),
                    "title": values.get("title", "").strip(),
                    "text": [],
                    "thumbnail": "",
                }
        elif tag == "img":
            image = (values.get("src") or values.get("data-src") or values.get("data-original") or "").strip()
            if image:
                if self._anchor is not None and not self._anchor["thumbnail"]:
                    self._anchor["thumbnail"] = image
                elif not self.meta_image:
                    self.meta_image = image
        elif tag in {"video", "source"}:
            src = (values.get("src") or values.get("data-src") or "").strip()
            mime = values.get("type", "")
            if _is_media_url(src, mime):
                self.media_urls.append(src)
            if tag == "video" and values.get("poster") and not self.meta_image:
                self.meta_image = values["poster"]

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "a" and self._anchor is not None:
            anchor = self._anchor
            parts = anchor["text"]
            assert isinstance(parts, list)
            anchor["text"] = " ".join(str(part) for part in parts if str(part).strip())
            self.anchors.append({key: str(value) for key, value in anchor.items()})
            self._anchor = None

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self.title_parts.append(text)
        if self._anchor is not None:
            parts = self._anchor["text"]
            assert isinstance(parts, list)
            parts.append(text)

    @property
    def title(self) -> str:
        return self.meta_title or " ".join(self.title_parts).strip()


def _is_media_url(url: str, mime: str = "") -> bool:
    if not url:
        return False
    try:
        path = urlsplit(url).path.lower()
    except ValueError:
        return False
    kind = mime.lower()
    return path.endswith((".m3u8", ".mp4")) or kind in {
        "application/vnd.apple.mpegurl",
        "application/x-mpegurl",
        "audio/mpegurl",
        "video/mp4",
    }


def _episode_number(text: str) -> int | None:
    for pattern in _EPISODE_PATTERNS:
        match = pattern.search(text)
        if match:
            try:
                number = int(match.group(1))
            except (TypeError, ValueError):
                continue
            if number > 0:
                return number
    match = _EPISODE_URL_PATTERN.search(text)
    if match:
        try:
            number = int(match.group(1))
        except (TypeError, ValueError):
            return None
        return number if number > 0 else None
    return None


def _origin(url: str) -> tuple[str, str, int] | None:
    try:
        parsed = urlsplit(url)
        scheme = parsed.scheme.lower()
        if scheme not in {"http", "https"} or not parsed.hostname:
            return None
        return (scheme, parsed.hostname.lower().rstrip("."), parsed.port or (443 if scheme == "https" else 80))
    except ValueError:
        return None


def _same_origin(left: str, right: str) -> bool:
    return _origin(left) is not None and _origin(left) == _origin(right)


def _validated_url(url: str) -> str | None:
    clean, _fragment = urldefrag(url)
    try:
        validate_public_url(clean)
    except (UnsafeUrlError, OSError, UnicodeError, ValueError):
        return None
    return clean


def _safe_thumbnail_url(raw: str, base_url: str) -> str | None:
    if not raw:
        return None
    resolved = urljoin(base_url, raw.strip())
    if not _same_origin(resolved, base_url):
        return None
    return _validated_url(resolved)


def _load_thumbnail(
    session: SafeHttpSession,
    raw_url: str,
    base_url: str,
    cache: dict[str, bytes | None],
) -> bytes | None:
    image_url = _safe_thumbnail_url(raw_url, base_url)
    if not image_url:
        return None
    if image_url in cache:
        return cache[image_url]
    if len(cache) >= MAX_THUMBNAILS:
        return None

    response = None
    try:
        response = session.get(image_url, expect=(200,), stream=True)
        content_type = str(response.headers.get("Content-Type", "")).split(";", 1)[0].strip().lower()
        if content_type not in _ALLOWED_THUMBNAIL_TYPES:
            cache[image_url] = None
            return None
        length = response.headers.get("Content-Length")
        if length:
            try:
                if int(length) > MAX_THUMBNAIL_BYTES:
                    cache[image_url] = None
                    return None
            except (TypeError, ValueError):
                pass
        chunks: list[bytes] = []
        received = 0
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if chunk:
                received += len(chunk)
                if received > MAX_THUMBNAIL_BYTES:
                    cache[image_url] = None
                    return None
                chunks.append(chunk)
        data = b"".join(chunks) or None
        cache[image_url] = data
        return data
    except DownloadBudgetExceeded:
        raise
    except Exception:
        cache[image_url] = None
        return None
    finally:
        if response is not None:
            response.close()


def _fetch_page(session: SafeHttpSession, url: str) -> tuple[_PageParser, str]:
    response = session.get(url, expect=(200,), stream=False)
    try:
        content_type = str(response.headers.get("Content-Type", "")).lower()
        if content_type and "html" not in content_type and "xhtml" not in content_type:
            raise DiscoveryError("ប្រភពនេះមិនបង្ហាញទំព័រ HTML សាធារណៈដែលអាចស្វែងរកភាគបានទេ។")
        encoding = getattr(response, "encoding", None) or "utf-8"
        parser = _PageParser()
        parser.feed(response.content.decode(encoding, errors="replace"))
        parser.close()
        return parser, str(getattr(response, "url", url) or url)
    finally:
        response.close()


def _page_media_candidates(parser: _PageParser, base_url: str) -> list[str]:
    candidates = list(parser.media_urls)
    for anchor in parser.anchors:
        href = anchor.get("href", "").strip()
        if _is_media_url(href):
            candidates.append(href)
    resolved: list[str] = []
    for candidate in candidates:
        absolute = urljoin(base_url, candidate)
        if not _is_media_url(absolute):
            continue
        safe = _validated_url(absolute)
        if safe and safe not in resolved:
            resolved.append(safe)
    resolved.sort(key=lambda value: 0 if urlsplit(value).path.lower().endswith(".m3u8") else 1)
    return resolved


def _page_media(parser: _PageParser, base_url: str) -> str | None:
    candidates = _page_media_candidates(parser, base_url)
    return candidates[0] if candidates else None


def _anchor_label(anchor: dict[str, str]) -> str:
    return " ".join(part for part in (anchor.get("title", ""), anchor.get("text", "")) if part).strip()


def _anchor_search_text(anchor: dict[str, str]) -> str:
    return " ".join(part for part in (anchor.get("title", ""), anchor.get("text", ""), anchor.get("href", "")) if part)


def discover_episodes(
    source_url: str,
    *,
    session_factory: Callable[..., SafeHttpSession] = SafeHttpSession,
) -> DiscoveryResult:
    """Find episode links visible in public HTML; never execute page scripts."""
    source_url = source_url.strip()
    if not source_url or len(source_url) > 2048:
        raise DiscoveryError("សូមបញ្ចូល URL ទំព័ររឿងដែលមានទម្រង់ត្រឹមត្រូវ។")
    direct = _validated_url(source_url)
    if not direct:
        raise DiscoveryError("តំណនេះមិនមែនជា URL សាធារណៈដែល app អនុញ្ញាតទេ។")

    if _is_media_url(direct):
        filename = Path(urlsplit(direct).path).stem.replace("_", " ").replace("-", " ").strip()
        title = filename or "វីដេអូ"
        return DiscoveryResult(title, [Episode(1, title, direct, direct, None)])

    budget = DownloadBudget(MAX_DISCOVERY_BYTES, MAX_DISCOVERY_SECONDS)
    session = session_factory(
        budget=budget,
        timeout=10,
        retry=RetryPolicy(attempts=1),
        pool_size=4,
    )
    thumbnail_cache: dict[str, bytes | None] = {}
    try:
        root, final_url = _fetch_page(session, direct)
        series_title = root.title or (urlsplit(final_url).hostname or "រឿង")
        fallback_thumb_url = root.meta_image

        candidates: list[tuple[int | None, str, str, str]] = []
        unlabeled_direct: list[tuple[str, str, str]] = []
        seen_hrefs: set[str] = set()
        for anchor in root.anchors:
            href = anchor.get("href", "").strip()
            if not href:
                continue
            try:
                absolute = urldefrag(urljoin(final_url, href))[0]
            except ValueError:
                continue
            search_text = _anchor_search_text(anchor)
            label = _anchor_label(anchor)
            number = _episode_number(search_text)
            direct_media = _is_media_url(absolute)
            same_site_page = _same_origin(absolute, final_url)
            if absolute in seen_hrefs:
                continue
            if direct_media and number is None:
                safe_media = _validated_url(absolute)
                if safe_media:
                    thumb_raw = anchor.get("thumbnail", "") or fallback_thumb_url
                    unlabeled_direct.append((label, safe_media, thumb_raw))
                continue
            if number is None or (not direct_media and not same_site_page):
                continue
            seen_hrefs.add(absolute)
            thumb_raw = anchor.get("thumbnail", "") or fallback_thumb_url
            candidates.append((number, label, absolute, thumb_raw))

        if not candidates and len(unlabeled_direct) == 1:
            label, media_url, thumb_raw = unlabeled_direct[0]
            candidates.append((1, label, media_url, thumb_raw))
        elif not candidates and len(unlabeled_direct) > 1:
            raise DiscoveryError("ទំព័រនេះបង្ហាញ video links ច្រើនដោយគ្មានលេខភាគច្បាស់ ដូច្នេះ app មិនអាចសន្និដ្ឋានថាជាភាគខុសៗគ្នាបានទេ។")

        if not candidates:
            root_media = _page_media(root, final_url)
            if root_media:
                thumbnail = _load_thumbnail(session, fallback_thumb_url, final_url, thumbnail_cache)
                return DiscoveryResult(series_title, [Episode(1, series_title, final_url, root_media, thumbnail)])
            raise DiscoveryError(
                "មិនអាចរកបញ្ជីភាគក្នុង HTML សាធារណៈបានទេ។ ប្រភពអាចបង្ហាញតាម JavaScript ឬក្នុង app ប៉ុណ្ណោះ។ សូមប្រើទំព័រដែលបង្ហាញ episode links ជាសាធារណៈ ឬបិទភ្ជាប់ direct HLS (.m3u8) / MP4 link ដែលអ្នកមានសិទ្ធិទាញយក។"
            )

        truncated = len(candidates) > MAX_EPISODE_PAGES
        candidates = candidates[:MAX_EPISODE_PAGES]
        episodes: list[Episode] = []
        seen_numbers: set[int] = set()
        for order, (number, label, page_url, thumbnail_raw) in enumerate(candidates, start=1):
            actual_number = number or order
            if actual_number in seen_numbers:
                continue
            seen_numbers.add(actual_number)
            safe_page = _validated_url(page_url)
            if not safe_page:
                continue

            if _is_media_url(safe_page):
                media_url = safe_page
                resolved_page = safe_page
                page_title = ""
                page_thumbnail_raw = thumbnail_raw
            else:
                try:
                    page, resolved_page = _fetch_page(session, safe_page)
                    page_title = page.title
                    media_url = _page_media(page, resolved_page)
                    page_thumbnail_raw = thumbnail_raw or page.meta_image
                except DiscoveryError:
                    raise
                except (HttpError, DownloadBudgetExceeded, UnsafeUrlError, OSError, socket.gaierror):
                    media_url = None
                    page_title = ""
                    page_thumbnail_raw = thumbnail_raw

            title = label or page_title or f"ភាគ {actual_number}"
            thumbnail_base = resolved_page if _origin(resolved_page) else final_url
            thumbnail = _load_thumbnail(session, page_thumbnail_raw, thumbnail_base, thumbnail_cache)
            episodes.append(Episode(actual_number, title, resolved_page, media_url, thumbnail))

        if not episodes:
            raise DiscoveryError("មិនអាចស្វែងរកភាគដែលអាចប្រើបានពីទំព័រនេះទេ។")
        episodes.sort(key=lambda item: item.number)
        return DiscoveryResult(series_title, episodes, truncated)
    except DiscoveryError:
        raise
    except (UnsafeUrlError, DownloadBudgetExceeded):
        raise DiscoveryError("ការស្វែងរកត្រូវបានបញ្ឈប់ដោយដែនកំណត់សុវត្ថិភាព ឬទំហំ/ពេលវេលា។") from None
    except (HttpError, OSError, socket.gaierror, UnicodeError, ValueError):
        raise DiscoveryError("មិនអាចអានទំព័រប្រភពនេះបានទេ។ សូមពិនិត្យ URL និងថាទំព័រអាចបើកជាសាធារណៈ។") from None
    finally:
        session.close()
