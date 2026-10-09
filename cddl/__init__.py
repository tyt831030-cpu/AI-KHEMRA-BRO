"""cddl - a general-purpose, law-abiding downloader for HLS / MP4 video sources.

The package is deliberately *source-agnostic*.  It understands the standard
streaming formats (HLS ``m3u8`` playlists, progressive MP4/TS files) and the
standard, non-DRM segment encryption defined by the HLS specification
(``METHOD=AES-128``).  It does **not** contain, and will not contain, code that
breaks DRM (Widevine / FairPlay / PlayReady / SAMPLE-AES) or that impersonates a
specific commercial application's private, signed API.

Typical use: archiving series you own or are otherwise licensed to keep, pulling
your own VOD renditions, or grabbing openly licensed (public-domain / CC) video.

Public API
----------
>>> from cddl import HttpSession, Options, download
>>> with HttpSession() as s:
...     download("https://example.com/ep01.m3u8", Options(out_dir="downloads"), s)
"""
from __future__ import annotations

from .http import HttpError, HttpSession, RetryPolicy
from .job import Options, JobResult, download
from .naming import episode_filename, sanitize_filename

__version__ = "1.0.0"

__all__ = [
    "__version__",
    "HttpSession",
    "HttpError",
    "RetryPolicy",
    "Options",
    "JobResult",
    "download",
    "sanitize_filename",
    "episode_filename",
]