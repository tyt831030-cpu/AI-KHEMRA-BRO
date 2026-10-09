"""Concurrent segment downloader with on-disk staging and resume support.

Segments are decoded in memory (a few MiB each) and written straight to a
staging directory, so a 40-episode season never has to fit in RAM.  A completed
segment file is a de-facto checkpoint: re-running the same job skips it.
"""
from __future__ import annotations

import hashlib
import os
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from typing import Callable, Optional

from .crypto import KeyStore, decrypt_segment
from .hls import MediaPlaylist, Segment
from .http import HttpSession
from .utils import NullProgress, Progress, human_bytes, human_time


class DownloaderError(RuntimeError):
    """Raised when segments could not be fetched completely."""


@dataclass
class DownloadStats:
    segments: int = 0
    bytes: int = 0
    duration: float = 0.0
    elapsed: float = 0.0
    skipped: int = 0
    failed: int = 0


class SegmentDownloader:
    """Fetch every segment of a :class:`MediaPlaylist` into a staging folder."""

    def __init__(
        self,
        session: HttpSession,
        *,
        workers: int = 12,
        segment_headers: Optional[dict[str, str]] = None,
        politeness_delay: float = 0.0,
        max_segment_retries: int = 3,
        quiet: bool = False,
    ) -> None:
        self.session = session
        self.workers = max(1, int(workers))
        self.segment_headers = segment_headers or {}
        self.politeness_delay = max(0.0, politeness_delay)
        self.max_segment_retries = max(1, max_segment_retries)
        self.quiet = quiet
        self.key_store = KeyStore(session)

    # -- public API ------------------------------------------------------
    def fetch_all(
        self,
        playlist: MediaPlaylist,
        stage_dir: str,
        *,
        label: str = "",
        progress: Optional[Progress | NullProgress] = None,
    ) -> DownloadStats:
        """Download (or verify) all segments into ``stage_dir``."""
        os.makedirs(stage_dir, exist_ok=True)
        segments = list(playlist.segments)

        # Preload keys so workers never serialise on a key fetch.
        self.key_store.preload([seg.key for seg in segments if seg.key])

        # Init sections (fMP4) are written once and shared by all fragments.
        seen_inits: set[tuple[str, int | None, int | None]] = set()
        for seg in segments:
            init_key = self._init_identity(seg)
            if init_key and init_key not in seen_inits:
                seen_inits.add(init_key)
                self._fetch_init(seg, stage_dir)

        progress = progress or Progress(total=len(segments))
        progress.total = len(segments)

        pending: list[tuple[int, Segment]] = []
        skipped = 0
        skipped_bytes = 0
        for index, seg in enumerate(segments):
            path = self._segment_path(stage_dir, index)
            seg.local_path = path
            if os.path.exists(path) and os.path.getsize(path) > 0:
                skipped += 1
                skipped_bytes += os.path.getsize(path)
                progress.add(os.path.getsize(path))
            else:
                pending.append((index, seg))

        stats = DownloadStats(segments=len(segments), duration=playlist.total_duration)
        stats.skipped = skipped
        stats.bytes = skipped_bytes

        if pending:
            failures = self._download_batch(pending, stage_dir, progress, label)
            stats.failed = len(failures)
            if failures:
                preview = ", ".join(str(i) for i, _ in failures[:8])
                raise DownloaderError(
                    f"{len(failures)} segment(s) failed after {self.max_segment_retries} "
                    f"attempt(s) (indices: {preview}{'...' if len(failures) > 8 else ''}); "
                    "re-run the same command to resume"
                )

        done, nbytes, _ = progress.snapshot()
        stats.bytes = nbytes
        stats.elapsed = progress.elapsed

        missing = [i for i in range(len(segments)) if not self._has_segment(stage_dir, i)]
        if missing:
            raise DownloaderError(f"staging directory is incomplete: {len(missing)} file(s) missing")
        return stats

    def concatenate(self, stage_dir: str, playlist: MediaPlaylist, out_path: str) -> str:
        """Binary-concatenate staged segments (valid for MPEG-TS and fragmented MP4)."""
        tmp = f"{out_path}.joining"
        with open(tmp, "wb") as out:
            active_init: tuple[str, int | None, int | None] | None = None
            for index in range(len(playlist.segments)):
                segment = playlist.segments[index]
                init_key = self._init_identity(segment)
                if init_key != active_init:
                    if init_key is not None:
                        init_path = self._init_path(segment, stage_dir)
                        if not os.path.isfile(init_path):
                            raise DownloaderError("an HLS init section is missing from staging")
                        with open(init_path, "rb") as init_part:
                            while True:
                                chunk = init_part.read(1 << 20)
                                if not chunk:
                                    break
                                out.write(chunk)
                    active_init = init_key
                with open(self._segment_path(stage_dir, index), "rb") as part:
                    while True:
                        chunk = part.read(1 << 20)
                        if not chunk:
                            break
                        out.write(chunk)
        os.replace(tmp, out_path)
        return out_path

    # -- internals -------------------------------------------------------
    @staticmethod
    def _segment_path(stage_dir: str, index: int) -> str:
        return os.path.join(stage_dir, f"{index:06d}.seg")

    @staticmethod
    def _init_identity(seg: Segment) -> tuple[str, int | None, int | None] | None:
        if not seg.init_section:
            return None
        byte_range = seg.init_byte_range
        return (
            seg.init_section,
            byte_range.offset if byte_range else None,
            byte_range.length if byte_range else None,
        )

    @classmethod
    def _init_path(cls, seg: Segment, stage_dir: str) -> str:
        identity = cls._init_identity(seg)
        if identity is None:
            raise DownloaderError("segment has no HLS init section")
        digest = hashlib.sha256(repr(identity).encode("utf-8")).hexdigest()[:24]
        return os.path.join(stage_dir, f"init-{digest}.seg")

    def _has_segment(self, stage_dir: str, index: int) -> bool:
        path = self._segment_path(stage_dir, index)
        return os.path.exists(path) and os.path.getsize(path) > 0

    def _fetch_init(self, seg: Segment, stage_dir: str) -> None:
        assert seg.init_section is not None
        path = self._init_path(seg, stage_dir)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return
        if seg.init_byte_range:
            data = self.session.get_range(
                seg.init_section,
                seg.init_byte_range.offset,
                seg.init_byte_range.length,
                headers=self.segment_headers,
            )
        else:
            data = self.session.get_bytes(seg.init_section, headers=self.segment_headers)
        if len(data) > 8 * 1024 * 1024:
            raise DownloaderError("HLS init section exceeds the 8 MiB limit")
        tmp = f"{path}.part"
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)

    def _fetch_one(self, index: int, seg: Segment, stage_dir: str) -> int:
        path = self._segment_path(stage_dir, index)

        if seg.byte_range:
            payload = self.session.get_range(
                seg.uri, seg.byte_range.offset, seg.byte_range.length, headers=self.segment_headers
            )
        else:
            response = self.session.get(
                seg.uri, headers=self.segment_headers, expect=(200, 206), stream=True
            )
            try:
                payload = response.content
            finally:
                response.close()

        if seg.key and seg.key.is_aes128:
            payload = decrypt_segment(payload, seg.key, self.key_store.key_bytes(seg.key), seg.sequence)

        tmp = f"{path}.part"
        with open(tmp, "wb") as fh:
            fh.write(payload)
        os.replace(tmp, path)
        return len(payload)

    def _download_batch(
        self,
        pending: list[tuple[int, Segment]],
        stage_dir: str,
        progress: Progress | NullProgress,
        label: str,
    ) -> list[tuple[int, Segment]]:
        failures: list[tuple[int, Segment]] = []

        def task(item: tuple[int, Segment]) -> tuple[int, Segment, Optional[int], Optional[BaseException]]:
            index, seg = item
            last: Optional[BaseException] = None
            for attempt in range(1, self.max_segment_retries + 1):
                try:
                    if self.politeness_delay:
                        import time as _time

                        _time.sleep(self.politeness_delay)
                    return index, seg, self._fetch_one(index, seg, stage_dir), None
                except BaseException as exc:  # noqa: BLE001 - reported to the caller
                    last = exc
                    if attempt < self.max_segment_retries:
                        import time as _time

                        _time.sleep(min(1.5 * attempt, 8.0))
            return index, seg, None, last

        with ThreadPoolExecutor(max_workers=self.workers, thread_name_prefix="seg") as pool:
            iterator = iter(pending)
            in_flight: dict = {}
            for _ in range(min(self.workers * 2, len(pending))):
                item = next(iterator, None)
                if item is None:
                    break
                in_flight[pool.submit(task, item)] = item

            while in_flight:
                done, _ = wait(list(in_flight), return_when=FIRST_COMPLETED)
                for future in done:
                    in_flight.pop(future, None)
                    index, seg, nbytes, error = future.result()
                    if error is not None:
                        progress.fail()
                        failures.append((index, seg))
                    else:
                        progress.add(nbytes or 0)
                    if not self.quiet:
                        progress.render(label)
                    nxt = next(iterator, None)
                    if nxt is not None:
                        in_flight[pool.submit(task, nxt)] = nxt

        if not self.quiet:
            progress.render(label, force=True)
        return failures


def format_stats(stats: DownloadStats, *, prefix: str = "  downloaded") -> str:
    """One-line human summary of a finished download."""
    return (
        f"{prefix} {stats.segments} segments, {human_bytes(stats.bytes)} media "
        f"({human_time(stats.duration)}) in {human_time(stats.elapsed)}"
    )
