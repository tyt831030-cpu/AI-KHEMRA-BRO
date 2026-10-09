"""Resource-bounded download runner for the public Streamlit app."""
from __future__ import annotations

import shutil
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

from cddl import Options
from cddl.extractors import ExtractorError
from cddl.hls import UnsupportedEncryption
from cddl.http import RetryPolicy
from cddl.job import Plan, make_plan, run_plan

from safe_http import DownloadBudget, DownloadBudgetExceeded, SafeHttpSession, UnsafeUrlError

MAX_NETWORK_BYTES = 512 * 1024 * 1024
MAX_BROWSER_FILE_BYTES = 350 * 1024 * 1024
MAX_NETWORK_SECONDS = 25 * 60
MAX_JOB_SECONDS = 30 * 60
MAX_HLS_SEGMENTS = 10_000
MAX_HLS_DURATION_SECONDS = 4 * 60 * 60
MAX_HLS_SEGMENT_RANGE_BYTES = 16 * 1024 * 1024
MAX_HLS_INIT_BYTES = 8 * 1024 * 1024
DOWNLOAD_SLOTS = threading.BoundedSemaphore(2)


class TooManyDownloads(RuntimeError):
    """The process is already using all permitted download workers."""


class BrowserFileTooLarge(RuntimeError):
    """The result is too large to keep safely in Streamlit's session memory."""


def _check_plan(plan: Plan, source_url: str, session: SafeHttpSession, budget: DownloadBudget) -> None:
    """Accept only finished, bounded HLS VOD or direct MP4 sources."""
    if plan.media and not plan.media.has_endlist:
        raise ValueError("Only finished, on-demand HLS videos are supported.")
    if plan.audio_media and not plan.audio_media.has_endlist:
        raise ValueError("Live audio renditions are not supported.")

    playlists = [playlist for playlist in (plan.media, plan.audio_media) if playlist is not None]
    segment_count = sum(len(playlist.segments) for playlist in playlists)
    if segment_count > MAX_HLS_SEGMENTS:
        budget.exceeded = True
        raise DownloadBudgetExceeded("HLS segment count exceeds the job limit")

    for playlist in playlists:
        if playlist.total_duration > MAX_HLS_DURATION_SECONDS:
            budget.exceeded = True
            raise DownloadBudgetExceeded("HLS duration exceeds the job limit")
        for segment in playlist.segments:
            if segment.byte_range and not (1 <= segment.byte_range.length <= MAX_HLS_SEGMENT_RANGE_BYTES):
                budget.exceeded = True
                raise DownloadBudgetExceeded("HLS segment range exceeds the job limit")
            if segment.init_byte_range and not (1 <= segment.init_byte_range.length <= MAX_HLS_INIT_BYTES):
                budget.exceeded = True
                raise DownloadBudgetExceeded("HLS init range exceeds the job limit")

    if plan.source.kind == "file":
        source = plan.source.url or source_url
        if Path(urlsplit(source).path.lower()).suffix != ".mp4":
            raise ValueError("Use a direct link to an MP4 video or HLS playlist.")
        status, headers = session.probe(source)
        if status >= 400:
            raise ValueError("The video URL is not available to this server.")
        content_length = headers.get("Content-Length") or headers.get("content-length")
        if content_length:
            try:
                budget.check_length(int(content_length))
            except ValueError:
                pass
    elif plan.source.kind == "hls" and plan.media and plan.variant:
        bitrate = plan.variant.effective_bandwidth
        duration = plan.media.total_duration
        estimate = int(bitrate * duration / 8 * 1.5) if bitrate and duration else 0
        if estimate > budget.max_bytes:
            budget.exceeded = True
            raise DownloadBudgetExceeded("estimated HLS size exceeds the job limit")


def download_video(
    url: str,
    *,
    show: str,
    season: int,
    episode: int,
    title: str = "",
    quality: str | int = "best",
) -> tuple[bytes, dict[str, object]]:
    """Download one authorized video and return a bounded browser payload.

    Temporary segment and output files are removed before this function returns.
    Streamlit retains only the capped output bytes in the requesting session.
    """
    if not DOWNLOAD_SLOTS.acquire(blocking=False):
        raise TooManyDownloads("download capacity is busy")

    root: str | None = None
    session: SafeHttpSession | None = None
    started = time.monotonic()
    budget = DownloadBudget(MAX_NETWORK_BYTES, MAX_NETWORK_SECONDS)
    try:
        root = tempfile.mkdtemp(prefix="ai-khemra-video-")
        output_dir = Path(root) / "out"
        parts_dir = Path(root) / "parts"
        output_dir.mkdir(parents=True, exist_ok=True)
        parts_dir.mkdir(parents=True, exist_ok=True)

        session = SafeHttpSession(
            budget=budget,
            timeout=25,
            retry=RetryPolicy(attempts=1, backoff=0.4, backoff_max=3.0, jitter=0.15),
            pool_size=16,
        )
        options = Options(
            out_dir=str(output_dir),
            show=show.strip(),
            season=season,
            episode=episode,
            title=title.strip() or None,
            container="mp4",
            quality=quality,
            remux_video=True,
            overwrite=True,
            write_metadata=False,
            workers=4,
            retries=1,
            segment_retries=2,
            timeout=25,
            subtitles=False,
            embed_subtitles=False,
            temp_dir=str(parts_dir),
            keep_segments=False,
            quiet=True,
        )

        plan = make_plan(url.strip(), options, session)
        _check_plan(plan, url.strip(), session, budget)
        if time.monotonic() - started > MAX_JOB_SECONDS:
            budget.exceeded = True
            raise DownloadBudgetExceeded("overall job timeout")

        result = run_plan(plan, options, session)
        if budget.exceeded or time.monotonic() - started > MAX_JOB_SECONDS:
            budget.exceeded = True
            raise DownloadBudgetExceeded("overall job timeout")
        if result.audio_path:
            raise RuntimeError("The audio track could not be packaged with the video.")
        if not result.output_path:
            raise RuntimeError("No output video was produced.")

        output = Path(result.output_path).resolve()
        if output_dir.resolve() not in output.parents or not output.is_file():
            raise RuntimeError("The output file could not be prepared.")
        if output.suffix.lower() != ".mp4" or output.stat().st_size <= 0:
            raise RuntimeError("The source could not be packaged as an MP4 video.")
        output_size = output.stat().st_size
        if output_size > MAX_BROWSER_FILE_BYTES:
            raise BrowserFileTooLarge("The output exceeds Streamlit's browser download memory limit.")

        payload = output.read_bytes()
        summary: dict[str, object] = {
            "file": output.name,
            "bytes": output_size,
            "duration": result.duration,
            "segments": result.segments,
            "variant": result.variant_label,
        }
        return payload, summary
    except Exception:
        if session is not None and session.unsafe_target_seen:
            raise UnsafeUrlError("a URL or redirect targeted a non-public address") from None
        if budget.exceeded:
            raise DownloadBudgetExceeded("the download exceeded its time or byte budget") from None
        raise
    finally:
        if session is not None:
            session.close()
        if root is not None:
            shutil.rmtree(root, ignore_errors=True)
        DOWNLOAD_SLOTS.release()


def public_error_message(exc: Exception) -> str:
    """Map third-party/network errors to brief Khmer messages without echoing URLs."""
    if isinstance(exc, UnsafeUrlError):
        return "URL ឬ redirect មួយមានគោលដៅទៅ private/local network ដែលត្រូវបានរារាំង។"
    if isinstance(exc, DownloadBudgetExceeded):
        return "លើសកម្រិត 512 MiB, 25 នាទី network (អតិបរមា 30 នាទីសរុប), ឬកម្រិត HLS។ សូមជ្រើសរើសគុណភាពទាបជាង។"
    if isinstance(exc, BrowserFileTooLarge):
        return "ឯកសារ MP4 ធំជាង 350 MiB ដែល browser download របស់ app នេះអនុញ្ញាត។ សូមជ្រើសរើសគុណភាពទាបជាង។"
    if isinstance(exc, TooManyDownloads):
        return "មានការទាញយកពីរដំណើរការរួចហើយ។ សូមរង់ចាំបន្តិច រួចសាកម្ដងទៀត។"
    if isinstance(exc, UnsupportedEncryption):
        return "ប្រភពនេះប្រើ DRM ឬការការពារដែលមិនត្រូវបានគាំទ្រ។"
    if isinstance(exc, (ValueError, ExtractorError)):
        message = str(exc)
        if "DRM" in message or "SAMPLE-AES" in message or "protected content" in message:
            return "ប្រភពនេះប្រើ DRM ឬការការពារដែលមិនត្រូវបានគាំទ្រ។"
        if "finished, on-demand" in message or "MP4 video or HLS" in message:
            return message
        return "តំណនេះមិនមែនជា HLS ឬ MP4 video file ផ្ទាល់ដែលគាំទ្រទេ។"
    return "ទាញយកមិនបានទេ។ សូមពិនិត្យតំណ និងសិទ្ធិចូលប្រើ រួចសាកល្បងម្ដងទៀត។"
