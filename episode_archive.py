"""Bounded all-episode ZIP preparation for Streamlit downloads."""
from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path
from typing import Any, Callable

from safe_downloader import (
    BrowserFileTooLarge,
    MAX_BROWSER_FILE_BYTES,
    MAX_NETWORK_BYTES,
    MAX_NETWORK_SECONDS,
    download_video,
)
from safe_http import DownloadBudget


class ArchiveLimitExceeded(ValueError):
    """The prepared series archive exceeds the browser download limit."""


def build_episode_archive(
    episodes: list[dict[str, Any]],
    series_title: str,
    *,
    downloader: Callable[..., tuple[bytes, dict[str, object]]] = download_video,
) -> tuple[bytes, str]:
    """Download the listed episodes sequentially under one shared budget."""
    budget = DownloadBudget(MAX_NETWORK_BYTES, MAX_NETWORK_SECONDS)
    total_mp4_bytes = 0
    used_names: set[str] = set()
    with tempfile.TemporaryDirectory(prefix="ai-khemra-series-") as directory:
        archive_path = Path(directory) / "episodes.zip"
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
            for episode in episodes:
                media_url = episode.get("media_url")
                if not media_url:
                    raise ValueError("An episode has no supported direct media link.")
                number = int(episode["number"])
                remaining = MAX_BROWSER_FILE_BYTES - total_mp4_bytes
                if remaining <= 0:
                    raise ArchiveLimitExceeded("All-episode archive reached the browser memory limit.")
                try:
                    payload, summary = downloader(
                        str(media_url),
                        show=series_title,
                        season=1,
                        episode=number,
                        title=str(episode.get("title") or ""),
                        quality="best",
                        budget=budget,
                        max_output_bytes=remaining,
                    )
                except BrowserFileTooLarge:
                    raise ArchiveLimitExceeded("All-episode archive reached the browser memory limit.") from None
                total_mp4_bytes += len(payload)
                if total_mp4_bytes > MAX_BROWSER_FILE_BYTES:
                    raise ArchiveLimitExceeded("All-episode archive reached the browser memory limit.")
                member = Path(str(summary["file"])).name
                if member in used_names:
                    member = f"{number:04d}_{member}"
                used_names.add(member)
                archive.writestr(member, payload)
                del payload
                if archive_path.stat().st_size > MAX_BROWSER_FILE_BYTES:
                    raise ArchiveLimitExceeded("All-episode archive reached the browser memory limit.")
        archive_bytes = archive_path.read_bytes()
        if len(archive_bytes) > MAX_BROWSER_FILE_BYTES:
            raise ArchiveLimitExceeded("All-episode archive reached the browser memory limit.")
    safe_title = "".join(ch if ch.isalnum() or ch in "-_. " else "_" for ch in series_title).strip(" ._")[:80] or "series"
    return archive_bytes, f"{safe_title}_episodes.zip"
