"""The download pipeline: resolve -> plan -> fetch segments -> mux -> metadata.

The pipeline is split in two so a caller can inspect a plan (``--list-formats``,
``--dry-run``) without touching the network for media bytes.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from dataclasses import dataclass, field
from typing import Optional, Sequence, Type, Union
from urllib.parse import urlparse

from .downloader import SegmentDownloader
from .extractors import Extractor, ExtractorError, ResolvedSource, get_extractor
from .hls import MasterPlaylist, MediaPlaylist, Variant, select_variant
from .http import HttpSession, RetryPolicy
from .muxer import MuxError, probe_duration, remux, remux_webvtt_to_srt
from .naming import episode_filename, sanitize_filename
from .utils import NullProgress, Progress, atomic_write, human_bytes, human_time

__all__ = ["Options", "Plan", "JobResult", "make_plan", "run_plan", "download", "build_session"]

#: Where a title's staged parts live when ``Options.temp_dir`` is unset.
PARTS_DIRNAME = ".cddl-parts"


# --------------------------------------------------------------------------
# options / results
# --------------------------------------------------------------------------
@dataclass
class Options:
    """Everything the pipeline can be told to do."""

    out_dir: str = "downloads"
    show: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    title: Optional[str] = None
    template: Optional[str] = None

    container: str = "mp4"
    quality: Union[str, int, None] = "best"
    remux_video: bool = True
    overwrite: bool = False
    dry_run: bool = False
    write_metadata: bool = True

    workers: int = 12
    retries: int = 5
    segment_retries: int = 3
    timeout: float = 30.0
    politeness_delay: float = 0.0
    proxy: Optional[str] = None
    insecure: bool = False

    user_agent: Optional[str] = None
    referer: Optional[str] = None
    headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)

    subtitles: bool = True
    subtitle_langs: Optional[list[str]] = None
    embed_subtitles: bool = False

    temp_dir: Optional[str] = None
    keep_segments: bool = False
    quiet: bool = False

    def segment_headers(self) -> dict[str, str]:
        """Headers applied to every media request."""
        headers: dict[str, str] = {}
        if self.referer:
            headers["Referer"] = self.referer
        headers.update(self.headers)
        return headers


@dataclass
class Plan:
    """A resolved, human-inspectable download plan."""

    url: str
    source: ResolvedSource
    media: Optional[MediaPlaylist]
    variant: Optional[Variant]
    variant_label: str
    output_path: str
    subtitle_tracks: list[tuple[str, str]] = field(default_factory=list)
    #: A demuxed audio rendition (``#EXT-X-MEDIA:TYPE=AUDIO``) when the platform
    #: ships audio separately from the video variant -- very common on modern
    #: streaming stacks.  ``None`` means the variant is self-contained.
    audio_media: Optional[MediaPlaylist] = None
    audio_url: Optional[str] = None
    audio_label: Optional[str] = None

    @property
    def segments(self) -> int:
        return len(self.media.segments) if self.media else 1

    @property
    def duration(self) -> float:
        return self.media.total_duration if self.media else 0.0

    def describe(self) -> str:
        lines = [
            f"  extractor     : {self.source.extractor}",
            f"  stream type   : {self.source.kind}",
            f"  selected      : {self.variant_label}",
            f"  segments      : {self.segments}",
            f"  duration      : {human_time(self.duration)}",
            f"  output        : {self.output_path}",
        ]
        if self.audio_label:
            lines.insert(4, f"  audio         : {self.audio_label} ({len(self.audio_media.segments) if self.audio_media else 0} segments)")
        if self.subtitle_tracks:
            lines.append(f"  subtitles     : {', '.join(lbl for lbl, _ in self.subtitle_tracks)}")
        if self.media and self.media.encryption_methods:
            lines.append(f"  encryption    : {', '.join(sorted(self.media.encryption_methods))}")
        return "\n".join(lines)


@dataclass
class JobResult:
    """Outcome of :func:`run_plan`."""

    url: str
    output_path: Optional[str]
    variant_label: str
    segments: int = 0
    bytes: int = 0
    duration: float = 0.0
    elapsed: float = 0.0
    skipped: bool = False
    dry_run: bool = False
    subtitle_paths: list[str] = field(default_factory=list)
    #: Set when a demuxed audio rendition was saved beside the video because the
    #: chosen container/`--no-remux` mode could not interleave it.
    audio_path: Optional[str] = None
    metadata_path: Optional[str] = None

    def summary(self) -> str:
        if self.dry_run:
            return f"[dry-run] would write {self.output_path} ({self.segments} segments, {human_time(self.duration)})"
        if self.skipped:
            return f"[skip] already present: {self.output_path}"
        return (
            f"[done] {self.output_path} ({self.segments} segments, "
            f"{human_bytes(self.bytes)}, {human_time(self.duration)} media, "
            f"{human_time(self.elapsed)} wall)"
        )


# --------------------------------------------------------------------------
# session
# --------------------------------------------------------------------------
def build_session(options: Options) -> HttpSession:
    """Create the shared HTTP session described by ``options``."""
    headers = dict(options.headers)
    if options.referer:
        headers.setdefault("Referer", options.referer)
    return HttpSession(
        headers=headers,
        cookies=options.cookies,
        timeout=options.timeout,
        retry=RetryPolicy(attempts=options.retries),
        pool_size=max(32, options.workers * 4),
        proxy=options.proxy,
        verify=not options.insecure,
        user_agent=options.user_agent,
    )


# --------------------------------------------------------------------------
# planning
# --------------------------------------------------------------------------
def make_plan(
    url: str,
    options: Options,
    session: HttpSession,
    *,
    extra_extractors: Optional[Sequence[Type[Extractor]]] = None,
) -> Plan:
    """Resolve ``url`` and decide exactly what will be downloaded and where."""
    if options.referer:
        session.update_headers({"Referer": options.referer})

    extractor = get_extractor(
        url,
        session,
        headers=options.segment_headers(),
        quiet=options.quiet,
        extra_extractors=extra_extractors,
    )
    source = extractor.resolve(url)

    media: Optional[MediaPlaylist] = None
    variant: Optional[Variant] = None
    variant_label = "progressive file"
    audio_media: Optional[MediaPlaylist] = None
    audio_url: Optional[str] = None
    audio_label: Optional[str] = None

    if source.kind == "hls":
        if source.master is not None:
            variant = select_variant(source.master, options.quality)
            media = _load_media(session, variant.uri, options)
            variant_label = variant.label
            if variant.audio_group:
                rendition = _pick_audio_rendition(source.master, variant.audio_group)
                if rendition is not None and rendition.uri:
                    audio_media = _load_media(session, rendition.uri, options)
                    audio_url = rendition.uri
                    audio_label = f"{rendition.name} [{rendition.language or '??'}]"
        elif source.media is not None:
            media = source.media
            variant_label = "single rendition"
        else:  # pragma: no cover - defensive
            raise ExtractorError("extractor returned an HLS source with no playlist")

    show = options.show or source.title or _title_from_url(url) or "download"
    title = options.title or (source.title if options.show else None)
    ext = "." + _extension_for(source, options)
    output_path = os.path.join(
        options.out_dir,
        episode_filename(
            show,
            season=options.season if options.season is not None else source.season,
            episode=options.episode if options.episode is not None else source.episode,
            title=title,
            ext=ext,
            template=options.template,
        ),
    )

    subtitle_tracks = _select_subtitles(source, options)

    return Plan(
        url=url,
        source=source,
        media=media,
        variant=variant,
        variant_label=variant_label,
        output_path=output_path,
        subtitle_tracks=subtitle_tracks,
        audio_media=audio_media,
        audio_url=audio_url,
        audio_label=audio_label,
    )


def _pick_audio_rendition(master: MasterPlaylist, group_id: str):
    """Choose the audio rendition to pair with a video variant.

    Prefers the ``DEFAULT=YES`` track in the group, then any track without a
    language tag (usually the original audio), then the first one with a URI.
    """
    candidates = [r for r in master.renditions if r.type.upper() == "AUDIO" and r.group_id == group_id]
    with_uri = [r for r in candidates if r.uri]
    if not with_uri:
        return None
    for rendition in with_uri:
        if rendition.default:
            return rendition
    untagged = [r for r in with_uri if not r.language]
    return untagged[0] if untagged else with_uri[0]


def _load_media(session: HttpSession, variant_url: str, options: Options) -> MediaPlaylist:
    from .hls import HlsError, parse_playlist

    text = session.get_text(variant_url, headers=options.segment_headers() or None, expect=(200,))
    try:
        playlist = parse_playlist(text, variant_url)
    except HlsError as exc:  # pragma: no cover - surfaced as a plan error
        raise ExtractorError(f"variant playlist {variant_url} is unusable: {exc}") from exc
    if isinstance(playlist, MasterPlaylist):
        # A nested master playlist: follow the highest-bandwidth entry once.
        nested = select_variant(playlist, options.quality)
        text = session.get_text(nested.uri, headers=options.segment_headers() or None, expect=(200,))
        playlist = parse_playlist(text, nested.uri)
        if isinstance(playlist, MasterPlaylist):  # pragma: no cover - give up sanely
            raise ExtractorError("playlist nesting is too deep to resolve")
    return playlist


def _select_subtitles(source: ResolvedSource, options: Options) -> list[tuple[str, str]]:
    if not options.subtitles or not source.subtitles:
        return []
    tracks = source.subtitles
    wanted = options.subtitle_langs
    if wanted:
        lowered = {lang.lower() for lang in wanted}
        tracks = [
            t for t in tracks
            if (t.language or "").lower() in lowered or t.label.lower() in lowered
        ]
    picked: list[tuple[str, str]] = []
    seen: set[str] = set()
    for track in tracks:
        key = track.url
        if key in seen:
            continue
        seen.add(key)
        picked.append((track.language or track.label or "sub", track.url))
    return picked


def _extension_for(source: ResolvedSource, options: Options) -> str:
    if source.kind == "file":
        suffix = os.path.splitext(urlparse(source.url).path)[1].lstrip(".")
        return suffix or options.container
    if options.container == "ts" and not options.remux_video:
        return "ts"
    return options.container


def _title_from_url(url: str) -> Optional[str]:
    stem = os.path.splitext(os.path.basename(urlparse(url).path))[0]
    return stem or None


# --------------------------------------------------------------------------
# execution
# --------------------------------------------------------------------------
def run_plan(
    plan: Plan,
    options: Options,
    session: HttpSession,
    *,
    progress: Optional[Progress] = None,
) -> JobResult:
    """Execute ``plan``: fetch media, mux, and write metadata."""
    started = time.monotonic()
    result = JobResult(
        url=plan.url,
        output_path=plan.output_path,
        variant_label=plan.variant_label,
        segments=plan.segments,
        duration=plan.duration,
    )

    if options.dry_run:
        result.dry_run = True
        return result

    if os.path.exists(plan.output_path) and not options.overwrite:
        result.skipped = True
        result.bytes = os.path.getsize(plan.output_path)
        return result

    os.makedirs(os.path.dirname(os.path.abspath(plan.output_path)) or ".", exist_ok=True)

    if plan.source.kind == "file":
        result.bytes = _download_progressive(plan, options, session, progress)
        result.elapsed = time.monotonic() - started
        result.subtitle_paths = _fetch_subtitles(plan, options, session)
        if options.write_metadata:
            result.metadata_path = _write_metadata(plan, options, result)
        return result

    assert plan.media is not None
    stage_dir = _stage_dir(plan, options)

    downloader = SegmentDownloader(
        session,
        workers=options.workers,
        segment_headers=options.segment_headers(),
        politeness_delay=options.politeness_delay,
        max_segment_retries=options.segment_retries,
        quiet=options.quiet,
    )
    stats = downloader.fetch_all(
        plan.media,
        stage_dir,
        label=os.path.basename(plan.output_path)[:28],
        progress=progress or (NullProgress() if options.quiet else Progress()),
    )
    result.segments = stats.segments
    result.bytes = stats.bytes

    # fMP4 playlists carry an EXT-X-MAP init section; TS playlists do not.  The
    # extension matters because MP4 output needs aac_adtstoasc only for TS input.
    staged_ext = ".mp4" if any(seg.init_section for seg in plan.media.segments) else ".ts"
    staged = os.path.join(stage_dir, f"joined{staged_ext}")
    downloader.concatenate(stage_dir, plan.media, staged)

    audio_staged: Optional[str] = None
    if plan.audio_media is not None:
        audio_dir = os.path.join(stage_dir, "audio")
        audio_progress = NullProgress(0) if options.quiet else Progress()
        audio_downloader = SegmentDownloader(
            session,
            workers=max(2, options.workers // 2),
            segment_headers=options.segment_headers(),
            politeness_delay=options.politeness_delay,
            max_segment_retries=options.segment_retries,
            quiet=options.quiet,
        )
        audio_stats = audio_downloader.fetch_all(
            plan.audio_media, audio_dir, label="audio", progress=audio_progress
        )
        audio_ext = ".mp4" if any(seg.init_section for seg in plan.audio_media.segments) else ".ts"
        audio_staged = os.path.join(stage_dir, f"joined_audio{audio_ext}")
        audio_downloader.concatenate(audio_dir, plan.audio_media, audio_staged)
        result.bytes += audio_stats.bytes

    if not options.keep_segments:
        _remove_staged_segments(stage_dir)

    subtitle_paths = _fetch_subtitles(plan, options, session)
    result.subtitle_paths = subtitle_paths

    if options.remux_video:
        embed = subtitle_paths if (options.embed_subtitles and options.container == "mkv") else None
        try:
            muxed = remux(
                staged,
                plan.output_path,
                container=options.container,
                audio=audio_staged,
                subtitles=embed,
                quiet=options.quiet,
            )
            result.bytes = muxed.size
        except MuxError:
            if options.container == "ts":
                raise
            fallback = os.path.splitext(plan.output_path)[0] + ".ts"
            os.replace(staged, fallback)
            result.output_path = fallback
            result.bytes = os.path.getsize(fallback)
            if audio_staged:
                sidecar = os.path.splitext(fallback)[0] + ".audio" + os.path.splitext(audio_staged)[1]
                os.replace(audio_staged, sidecar)
                result.audio_path = sidecar
    else:
        target = plan.output_path
        if not target.lower().endswith((".ts", ".mp4")):
            target = os.path.splitext(target)[0] + ".ts"
            result.output_path = target
        os.replace(staged, target)
        result.bytes = os.path.getsize(target)
        if audio_staged:
            # The container is raw TS, so the demuxed audio cannot be interleaved;
            # keep it beside the video instead of throwing the download away.
            sidecar = f"{os.path.splitext(target)[0]}.audio{os.path.splitext(audio_staged)[1]}"
            os.replace(audio_staged, sidecar)
            result.audio_path = sidecar

    if result.output_path:
        probed = probe_duration(result.output_path)
        if probed:
            result.duration = probed

    if not options.keep_segments:
        shutil.rmtree(stage_dir, ignore_errors=True)

    result.elapsed = time.monotonic() - started
    if options.write_metadata:
        result.metadata_path = _write_metadata(plan, options, result)
    return result


def download(
    url: str,
    options: Optional[Options] = None,
    session: Optional[HttpSession] = None,
    *,
    extra_extractors: Optional[Sequence[Type[Extractor]]] = None,
    progress: Optional[Progress] = None,
) -> JobResult:
    """One-call convenience: resolve, download, mux, report."""
    options = options or Options()
    owns_session = session is None
    session = session or build_session(options)
    try:
        plan = make_plan(url, options, session, extra_extractors=extra_extractors)
        return run_plan(plan, options, session, progress=progress)
    finally:
        if owns_session:
            session.close()


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _stage_dir(plan: Plan, options: Options) -> str:
    digest = hashlib.sha1(plan.url.encode("utf-8")).hexdigest()[:16]
    base = options.temp_dir or os.path.join(options.out_dir, PARTS_DIRNAME)
    return os.path.join(base, digest)


def _remove_staged_segments(stage_dir: str) -> None:
    """Free downloaded chunks after joining while keeping joined media for muxing."""
    for directory, _subdirs, filenames in os.walk(stage_dir):
        for filename in filenames:
            if filename.endswith((".seg", ".part")):
                try:
                    os.remove(os.path.join(directory, filename))
                except FileNotFoundError:
                    pass


def _download_progressive(
    plan: Plan,
    options: Options,
    session: HttpSession,
    progress: Optional[Progress],
) -> int:
    """Stream a single progressive file to disk with resume-by-restart semantics."""
    target = plan.output_path
    tmp = f"{target}.part"
    written = 0
    response = session.get(
        plan.source.url,
        headers=options.segment_headers() or None,
        expect=(200,),
        stream=True,
    )
    try:
        total = int(response.headers.get("Content-Length") or 0)
        meter = progress or (NullProgress() if options.quiet else Progress(total=total or 1))
        with open(tmp, "wb") as fh:
            for chunk in response.iter_content(chunk_size=1 << 18):
                if not chunk:
                    continue
                fh.write(chunk)
                written += len(chunk)
                meter.add(len(chunk))
                if not options.quiet:
                    meter.render(os.path.basename(target)[:28])
    finally:
        response.close()

    if not options.quiet and progress is not None:
        progress.render(os.path.basename(target)[:28], force=True)
    os.replace(tmp, target)
    return written


def _fetch_subtitles(plan: Plan, options: Options, session: HttpSession) -> list[str]:
    """Download subtitle renditions next to the video, converting VTT to SRT."""
    if not plan.subtitle_tracks:
        return []
    stem = os.path.splitext(plan.output_path)[0]
    paths: list[str] = []
    for label, url in plan.subtitle_tracks:
        safe = sanitize_filename(label, max_bytes=32, fallback="sub")
        vtt_path = f"{stem}.{safe}.vtt"
        try:
            data = _fetch_subtitle_bytes(session, url, options.segment_headers())
        except Exception:  # noqa: BLE001 - subtitles are optional
            continue
        if not data:
            continue
        atomic_write(vtt_path, data)
        paths.append(vtt_path)
        try:
            srt = remux_webvtt_to_srt(vtt_path)
            if srt != vtt_path:
                paths.append(srt)
        except MuxError:
            pass
    return paths


def _fetch_subtitle_bytes(session: HttpSession, url: str, headers: dict[str, str]) -> bytes:
    """Fetch a subtitle rendition, merging segmented WebVTT playlists into one file."""
    from .hls import HlsError, MediaPlaylist, parse_playlist

    payload = session.get_bytes(url, headers=headers or None)
    if payload.lstrip()[:7].upper() != b"#EXTM3U":
        return payload

    try:
        playlist = parse_playlist(payload.decode("utf-8", "replace"), url)
    except HlsError:
        return payload
    if not isinstance(playlist, MediaPlaylist):
        return payload

    chunks: list[bytes] = []
    for segment in playlist.segments:
        part = session.get_bytes(segment.uri, headers=headers or None)
        chunks.append(part)
    return _merge_webvtt(chunks)


def _merge_webvtt(chunks: list[bytes]) -> bytes:
    """Concatenate WebVTT segments, keeping one header and one timestamp map."""
    out: list[str] = []
    seen_header = False
    seen_timestamp_map = False
    for chunk in chunks:
        for line in chunk.decode("utf-8", "replace").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            stripped = line.strip()
            if stripped.upper().startswith("WEBVTT"):
                if not seen_header:
                    seen_header = True
                    out.append(line)
                continue
            if stripped.startswith("X-TIMESTAMP-MAP"):
                if not seen_timestamp_map:
                    seen_timestamp_map = True
                    out.append(line)
                continue
            out.append(line)
    if not seen_header:
        out.insert(0, "WEBVTT")
    return ("\n".join(out).strip("\n") + "\n").encode("utf-8")


def _write_metadata(plan: Plan, options: Options, result: JobResult) -> str:
    """Write a ``*.json`` sidecar so a library can be re-indexed later."""
    target = os.path.splitext(result.output_path or plan.output_path)[0] + ".json"
    payload = {
        "tool": "cddl",
        "source_url": plan.url,
        "extractor": plan.source.extractor,
        "stream_kind": plan.source.kind,
        "variant": plan.variant_label,
        "bandwidth": plan.variant.effective_bandwidth if plan.variant else None,
        "resolution": list(plan.variant.resolution) if plan.variant and plan.variant.resolution else None,
        "segments": result.segments,
        "duration_seconds": round(result.duration, 3),
        "bytes": result.bytes,
        "container": options.container,
        "output": os.path.basename(result.output_path or plan.output_path),
        "audio_rendition": plan.audio_label,
        "audio_sidecar": os.path.basename(result.audio_path) if result.audio_path else None,
        "subtitles": [os.path.basename(p) for p in result.subtitle_paths],
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    atomic_write(target, json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"))
    return target
