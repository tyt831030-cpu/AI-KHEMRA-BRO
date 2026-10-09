"""Thin, predictable wrapper around ffmpeg for the final container step."""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

#: container -> the ffmpeg muxer name to force with ``-f``
_FORMAT_FLAG = {"mp4": "mp4", "mkv": "matroska", "ts": "mpegts"}


class MuxError(RuntimeError):
    """ffmpeg was missing or refused the job."""


@dataclass
class MuxResult:
    path: str
    container: str
    size: int


def ffmpeg_path() -> Optional[str]:
    return shutil.which("ffmpeg")


def ffprobe_path() -> Optional[str]:
    return shutil.which("ffprobe")


def require_ffmpeg() -> str:
    path = ffmpeg_path()
    if not path:
        raise MuxError(
            "ffmpeg is required for the remux step; install it "
            "(apt install ffmpeg | brew install ffmpeg) or pass --container ts --no-remux"
        )
    return path


def _run(cmd: Sequence[str], *, quiet: bool, timeout: float = 180.0) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            list(cmd),
            stdout=subprocess.PIPE if quiet else None,
            stderr=subprocess.STDOUT if quiet else None,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise MuxError(f"media processing exceeded {timeout:g} seconds") from exc


def remux(
    source: str,
    destination: str,
    *,
    container: str = "mp4",
    audio: Optional[str] = None,
    subtitles: Optional[Iterable[str]] = None,
    faststart: bool = True,
    quiet: bool = True,
    extra_args: Sequence[str] = (),
) -> MuxResult:
    """Rewrite ``source`` into ``destination`` without re-encoding.

    ``audio`` is an optional second input holding a demuxed audio rendition
    (``#EXT-X-MEDIA:TYPE=AUDIO``); when given it is mapped as the output's audio
    track instead of the video file's own audio.
    ``mp4`` remuxes the transported AAC with ``aac_adtstoasc`` (required when the
    source is MPEG-TS).  ``mkv`` is used when you want soft subtitles muxed in.
    """
    ffmpeg = require_ffmpeg()
    container = container.lower().lstrip(".")
    if container not in _FORMAT_FLAG:
        raise MuxError(f"unsupported container {container!r}")

    os.makedirs(os.path.dirname(os.path.abspath(destination)) or ".", exist_ok=True)
    # Keep a real extension on the temp file (or pass -f), otherwise ffmpeg
    # cannot guess the muxer.
    suffix = os.path.splitext(destination)[1] or f".{container}"
    tmp = f"{destination}.muxing{suffix}"
    output_format = _FORMAT_FLAG[container]

    audio_input = audio if (audio and os.path.exists(audio)) else None
    sub_files: list[str] = []
    if subtitles:
        for sub in subtitles:
            if sub and os.path.exists(sub):
                sub_files.append(sub)

    def build(*, container_extras: bool) -> list[str]:
        cmd: list[str] = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", source]
        if audio_input:
            cmd += ["-i", audio_input]
        for sub in sub_files:
            cmd += ["-i", sub]

        first_sub_index = 1 + (1 if audio_input else 0)
        cmd += ["-map", "0:v?"]
        if audio_input:
            cmd += ["-map", "1:a?"]
        else:
            cmd += ["-map", "0:a?"]
        for idx in range(len(sub_files)):
            cmd += ["-map", f"{first_sub_index + idx}:0"]

        cmd += ["-c", "copy"]
        if container_extras:
            if container == "mp4":
                if any_ext(source, ".ts", ".m2ts") or (audio_input and any_ext(audio_input, ".ts", ".m2ts")):
                    cmd += ["-bsf:a", "aac_adtstoasc"]
                if faststart:
                    cmd += ["-movflags", "+faststart"]
                if sub_files:
                    cmd += ["-c:s", "mov_text"]
            elif container == "mkv":
                cmd += ["-c:s", "copy"]

        cmd += list(extra_args)
        cmd += ["-f", output_format, tmp]
        return cmd

    result = _run(build(container_extras=True), quiet=quiet)
    if result.returncode != 0 or not os.path.exists(tmp):
        # Second attempt without the container-specific extras: some sources are
        # already fragmented MP4 and reject aac_adtstoasc.
        result = _run(build(container_extras=False), quiet=quiet)
    if result.returncode != 0 or not os.path.exists(tmp):
        raise MuxError(
            f"ffmpeg failed to remux {os.path.basename(source)} "
            f"(exit {result.returncode}); try --container mkv or --no-remux"
        )

    os.replace(tmp, destination)
    return MuxResult(path=destination, container=container, size=os.path.getsize(destination))


def any_ext(path: str, *suffixes: str) -> bool:
    return path.lower().endswith(tuple(suffixes))


def probe_duration(path: str) -> Optional[float]:
    """Media duration in seconds via ffprobe, or ``None`` when unavailable."""
    probe = ffprobe_path()
    if not probe:
        return None
    try:
        proc = subprocess.run(
            [
                probe,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=10.0,
        )
    except subprocess.TimeoutExpired:
        return None
    try:
        return float(proc.stdout.decode().strip())
    except (ValueError, AttributeError):
        return None


def remux_webvtt_to_srt(vtt_path: str, srt_path: Optional[str] = None) -> str:
    """Convert an HLS subtitle track to SubRip using ffmpeg."""
    ffmpeg = require_ffmpeg()
    target = srt_path or os.path.splitext(vtt_path)[0] + ".srt"
    proc = _run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", vtt_path, target], quiet=True)
    if proc.returncode != 0 or not os.path.exists(target):
        return vtt_path
    return target
