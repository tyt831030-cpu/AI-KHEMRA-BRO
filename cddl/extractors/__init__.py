"""Extractor registry.

Extractors are registered by priority; the highest-priority match for a URL
wins.  To support an additional site, drop a module in this package that
subclasses :class:`~cddl.extractors.base.Extractor` and add it to ``BUILTIN``
below (or pass ``extra_extractors=[...]`` to :func:`get_extractor`).
"""
from __future__ import annotations

from typing import Iterable, Optional, Sequence, Type

from .base import Extractor, ExtractorError, ResolvedSource, SubtitleTrack
from .generic import HlsExtractor, ProgressiveFileExtractor

#: Ordered low-to-high priority; the *last* match in this list wins.
BUILTIN: tuple[Type[Extractor], ...] = (ProgressiveFileExtractor, HlsExtractor)

__all__ = [
    "Extractor",
    "ExtractorError",
    "ResolvedSource",
    "SubtitleTrack",
    "HlsExtractor",
    "ProgressiveFileExtractor",
    "BUILTIN",
    "get_extractor",
    "list_extractors",
]


def list_extractors() -> list[dict[str, str]]:
    """Describe every known extractor (used by ``--list-extractors``)."""
    return [
        {"name": cls.name, "priority": str(cls.priority), "description": cls.description}
        for cls in BUILTIN
    ]


def get_extractor(
    url: str,
    session,
    *,
    headers: Optional[dict[str, str]] = None,
    quiet: bool = False,
    extra_extractors: Optional[Sequence[Type[Extractor]]] = None,
) -> Extractor:
    """Return an instantiated extractor able to handle ``url``."""
    candidates: Iterable[Type[Extractor]] = (*BUILTIN, *(extra_extractors or ()))
    matches = [cls for cls in candidates if cls.matches(url)]
    if not matches:
        known = ", ".join(f"{c.name} ({c.description})" for c in candidates)
        raise ExtractorError(
            f"no extractor handles {url}\n"
            f"Supported inputs: {known}\n"
            "Tip: pass the stream's .m3u8 manifest URL directly, or add your own "
            "Extractor subclass for a site you are authorised to use."
        )
    chosen = max(matches, key=lambda cls: cls.priority)
    return chosen(session, headers=headers, quiet=quiet)