"""Filesystem-safe naming for CJK (and mixed-script) library layouts.

Episode files must survive Windows, macOS and Linux at once, must not blow the
255-byte component limit, and must sort correctly.  Chinese titles are kept
verbatim (UTF-8, NFC) because transcoding them or replacing every rune with
``_`` makes a library useless.
"""
from __future__ import annotations

import hashlib
import os
import re
import unicodedata
from typing import Optional

#: Characters illegal on Windows plus POSIX separators and control codes.
_ILLEGAL_CHARS = r'<>:"/\|?*'
_ILLEGAL_RE = re.compile(f"[{re.escape(_ILLEGAL_CHARS)}]")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_WS_RE = re.compile(r"\s+")

#: Reserved DOS device names (still honoured by Windows 11).
_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

DEFAULT_TEMPLATE = "{show}/S{season:02d}E{episode:03d}{title_part}"


def _truncate_utf8(text: str, max_bytes: int) -> str:
    """Truncate to at most ``max_bytes`` UTF-8 bytes without splitting a rune."""
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    truncated = encoded[:max_bytes]
    while truncated:
        try:
            return truncated.decode("utf-8")
        except UnicodeDecodeError:
            truncated = truncated[:-1]
    return ""


def sanitize_filename(
    name: str,
    *,
    max_bytes: int = 180,
    replacement: str = "_",
    fallback: str = "untitled",
) -> str:
    """Turn arbitrary text into a safe single path component.

    * NFC-normalises (so macOS and Linux agree on byte content)
    * strips control characters and Windows-illegal punctuation
    * collapses whitespace, trims trailing dots/spaces (illegal on Windows)
    * caps the length in UTF-8 bytes, appending a short hash when it had to cut
    """
    text = unicodedata.normalize("NFC", str(name))
    text = _CONTROL_RE.sub("", text)
    text = _ILLEGAL_RE.sub(replacement, text)
    text = _WS_RE.sub(" ", text).strip()
    text = text.strip(". ")
    if not text:
        text = fallback

    stem = text.split(".")[0].upper()
    if stem in _RESERVED:
        text = f"{text}{replacement}"

    if len(text.encode("utf-8")) > max_bytes:
        digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
        keep = max_bytes - len(digest) - 2
        text = f"{_truncate_utf8(text, keep)}~{digest}"
    return text


def episode_filename(
    show: str,
    *,
    season: Optional[int] = None,
    episode: Optional[int] = None,
    title: Optional[str] = None,
    ext: str = ".mp4",
    template: Optional[str] = None,
) -> str:
    """Render a library-style filename such as ``斗罗大陆/S01E007 武魂觉醒.mp4``.

    ``template`` may use ``{show}``, ``{season}``, ``{episode}``, ``{title}``
    and ``{title_part}`` with normal ``str.format`` field syntax, e.g.
    ``"{show}/第{episode:03d}集.mp4"`` (put the extension in the template only
    when you want it there; it is appended otherwise).
    """
    show = sanitize_filename(show or "download", max_bytes=120)
    season = 1 if season is None else int(season)
    episode = 0 if episode is None else int(episode)
    clean_title = sanitize_filename(title, max_bytes=90) if title else ""
    title_part = f" {clean_title}" if clean_title else ""

    if template:
        rendered = template.format(
            show=show,
            season=season,
            episode=episode,
            title=clean_title,
            title_part=title_part,
        )
    else:
        rendered = DEFAULT_TEMPLATE.format(
            show=show, season=season, episode=episode, title_part=title_part
        )

    # Sanitize each component but keep the directory separators the template made.
    parts = [p for p in rendered.replace("\\", "/").split("/") if p not in ("", ".")]
    if not parts:
        parts = [show or "download"]
    # Append the extension unless the template already named one (e.g. ".mkv").
    if ext and not os.path.splitext(parts[-1])[1]:
        parts[-1] = f"{parts[-1]}{ext}"
    safe_parts = [sanitize_filename(p, max_bytes=180) for p in parts]
    return "/".join(safe_parts)


def episode_dirname(show: str, *, season: Optional[int] = None) -> str:
    """``斗罗大陆/Season 01`` -- the folder an episode lives in."""
    show = sanitize_filename(show or "download", max_bytes=120)
    if season is None:
        return show
    return f"{show}/Season {int(season):02d}"
