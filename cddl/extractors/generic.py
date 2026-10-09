"""Generic extractors: a direct HLS playlist, or a direct media file."""
from __future__ import annotations

from urllib.parse import urlparse

from ..hls import HlsError, MasterPlaylist, MediaPlaylist, UnsupportedEncryption, parse_playlist
from .base import Extractor, ExtractorError, ResolvedSource, SubtitleTrack

_HLS_HINTS = (".m3u8", ".m3u", "/m3u8", "manifest", "/hls/", "playlist")
_FILE_SUFFIXES = (".mp4", ".mkv", ".ts", ".mov", ".m4v", ".flv", ".webm", ".avi")


def _suffix(url: str) -> str:
    path = urlparse(url).path.lower()
    return path.rsplit(".", 1)[-1] if "." in path.rsplit("/", 1)[-1] else ""


class HlsExtractor(Extractor):
    """Handle any URL that resolves to an m3u8 playlist (master or media)."""

    name = "generic-hls"
    priority = 10
    description = "Direct HLS (.m3u8) master or media playlists, including AES-128 encrypted VOD"

    @classmethod
    def matches(cls, url: str) -> bool:
        lowered = url.lower()
        if _suffix(url) in ("m3u8", "m3u"):
            return True
        return any(hint in lowered for hint in _HLS_HINTS)

    def resolve(self, url: str) -> ResolvedSource:
        text = self.session.get_text(url, headers=self.headers or None, expect=(200,))
        try:
            playlist = parse_playlist(text, url)
        except UnsupportedEncryption as exc:
            raise ExtractorError(str(exc)) from exc
        except HlsError as exc:
            raise ExtractorError(f"{url} is not a usable HLS playlist: {exc}") from exc

        source = ResolvedSource(
            kind="hls",
            url=url,
            headers=dict(self.headers),
            title=self.guess_title(url),
            extractor=self.name,
        )

        if isinstance(playlist, MasterPlaylist):
            source.master = playlist
            source.subtitles = [
                SubtitleTrack(
                    label=r.name or (r.language or "sub"),
                    url=r.uri,
                    language=r.language,
                    is_default=r.default,
                )
                for r in playlist.subtitle_renditions() if r.uri
            ]
        else:
            source.media = playlist
        return source

    def load_media_playlist(self, url: str) -> MediaPlaylist:
        """Fetch a variant URI and require it to be a media playlist."""
        text = self.session.get_text(url, headers=self.headers or None, expect=(200,))
        playlist = parse_playlist(text, url)
        if isinstance(playlist, MasterPlaylist):
            raise ExtractorError(f"expected a media playlist at {url}, got a master playlist")
        return playlist


class ProgressiveFileExtractor(Extractor):
    """Handle a direct link to a single media file."""

    name = "generic-file"
    priority = 20
    description = "Direct progressive downloads (.mp4 .mkv .ts .mov .m4v .flv .webm)"

    @classmethod
    def matches(cls, url: str) -> bool:
        return "." + _suffix(url) in _FILE_SUFFIXES

    def resolve(self, url: str) -> ResolvedSource:
        status, info = self.session.probe(url)
        if status >= 400:
            raise ExtractorError(f"HTTP {status} while probing {url}")
        return ResolvedSource(
            kind="file",
            url=url,
            headers=dict(self.headers),
            title=self.guess_title(url),
            extractor=self.name,
        )
