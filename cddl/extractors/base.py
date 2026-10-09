"""Extractor plugin contract.

An *extractor* turns one user-supplied page/stream URL into a concrete,
downloadable resource.  Extractors are intentionally pluggable so that you can
add sites you control or are authorised to use, without touching the engine.

Design rules of this project
----------------------------
* An extractor may follow documented, public endpoints (a plain ``.m3u8`` a page
  hands to its own player, a direct MP4, a WebVTT sidecar).
* An extractor must **not** contain code that defeats access controls: no DRM
  key negotiation, no signature/cookie forging, no reverse-engineering of a
  closed application's private, signed API.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar, Optional, Union

from ..hls import MasterPlaylist, MediaPlaylist


class ExtractorError(RuntimeError):
    """No extractor could handle the URL, or it failed."""


@dataclass
class SubtitleTrack:
    """A subtitle rendition we know how to fetch."""

    label: str
    url: str
    language: Optional[str] = None
    is_default: bool = False


@dataclass
class ResolvedSource:
    """What an extractor hands back to the engine."""

    #: ``"hls"`` (an m3u8 playlist) or ``"file"`` (a progressive media URL).
    kind: str
    url: str
    #: Headers that must accompany the *media* requests (Referer, Origin, ...).
    headers: dict[str, str] = field(default_factory=dict)
    title: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    #: Populated for ``kind == "hls"``.
    master: Optional[MasterPlaylist] = None
    media: Optional[MediaPlaylist] = None
    subtitles: list[SubtitleTrack] = field(default_factory=list)
    extractor: str = ""


class Extractor(ABC):
    """Base class for URL handlers."""

    #: Short identifier shown in ``--list-extractors`` and diagnostics.
    name: ClassVar[str] = "base"
    #: Higher priority wins when several extractors match a URL.
    priority: ClassVar[int] = 100
    #: Human description of what the extractor accepts.
    description: ClassVar[str] = ""

    def __init__(self, session, *, headers: Optional[dict[str, str]] = None, quiet: bool = False) -> None:
        self.session = session
        self.headers = dict(headers or {})
        self.quiet = quiet

    # -- contract --------------------------------------------------------
    @classmethod
    @abstractmethod
    def matches(cls, url: str) -> bool:
        """Return True when this extractor can handle ``url``."""

    @abstractmethod
    def resolve(self, url: str) -> ResolvedSource:
        """Resolve ``url`` into a downloadable :class:`ResolvedSource`."""

    # -- shared helpers --------------------------------------------------
    def fetch_playlist(self, url: str) -> Union[MasterPlaylist, MediaPlaylist]:
        """Download and parse an m3u8 playlist at ``url``."""
        from ..hls import parse_playlist

        text = self.session.get_text(url, headers=self.headers or None, expect=(200,))
        return parse_playlist(text, url)

    def guess_title(self, url: str) -> Optional[str]:
        """Best-effort title from the last meaningful path component."""
        from urllib.parse import unquote, urlparse

        path = urlparse(url).path
        stem = unquote(path.rsplit("/", 1)[-1])
        for suffix in (".m3u8", ".mp4", ".mkv", ".ts", ".mov", ".m4v", ".flv", ".webm"):
            if stem.lower().endswith(suffix):
                stem = stem[: -len(suffix)]
                break
        return stem or None