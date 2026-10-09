"""A dependency-free parser for the HLS playlist format (RFC 8216).

Supports everything needed to archive a finished VOD title:

* master playlists (``#EXT-X-STREAM-INF``) with resolution / bandwidth / codecs
* alternate renditions (``#EXT-X-MEDIA``: audio + subtitle tracks)
* media playlists with ``#EXTINF``, ``#EXT-X-KEY``, ``#EXT-X-MAP``,
  ``#EXT-X-BYTERANGE``, ``#EXT-X-DISCONTINUITY`` and ``#EXT-X-ENDLIST``
* AES-128 (``METHOD=AES-128``) key metadata -- *not* SAMPLE-AES, which is DRM
  and is rejected with an explicit error.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterator, Optional
from urllib.parse import urljoin

__all__ = [
    "HlsError",
    "UnsupportedEncryption",
    "Key",
    "ByteRange",
    "Segment",
    "Variant",
    "Rendition",
    "MediaPlaylist",
    "MasterPlaylist",
    "parse_playlist",
    "parse_attribute_list",
]

_ATTR_RE = re.compile(r'([A-Za-z0-9-]+)=("[^"]*"|[^,]*)')
_RESOLUTION_RE = re.compile(r"^(\d+)\s*[xX]\s*(\d+)$")


class HlsError(ValueError):
    """The playlist is malformed or is not HLS at all."""


class UnsupportedEncryption(HlsError):
    """The stream uses DRM (e.g. SAMPLE-AES) which this tool will not touch."""


# --------------------------------------------------------------------------
# attribute helpers
# --------------------------------------------------------------------------
def parse_attribute_list(text: str) -> dict[str, str]:
    """Parse an HLS attribute list such as ``METHOD=AES-128,URI="k.bin"``."""
    attrs: dict[str, str] = {}
    for match in _ATTR_RE.finditer(text):
        name, raw = match.group(1), match.group(2)
        if raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:
            raw = raw[1:-1]
        attrs[name.upper()] = raw
    return attrs


def _to_float(value: Optional[str], default: float = 0.0) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _to_int(value: Optional[str], default: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------------
# data model
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Key:
    """An ``#EXT-X-KEY`` tag."""

    method: str
    uri: Optional[str] = None
    iv: Optional[bytes] = None
    key_format: Optional[str] = None
    key_format_versions: Optional[str] = None

    @property
    def is_none(self) -> bool:
        return self.method.upper() == "NONE"

    @property
    def is_aes128(self) -> bool:
        return self.method.upper() == "AES-128"


@dataclass(frozen=True)
class ByteRange:
    """An ``#EXT-X-BYTERANGE`` sub-range of a resource."""

    length: int
    offset: int


@dataclass
class Segment:
    """One media segment of a VOD playlist."""

    uri: str
    duration: float
    sequence: int
    title: Optional[str] = None
    key: Optional[Key] = None
    init_section: Optional[str] = None
    init_byte_range: Optional[ByteRange] = None
    byte_range: Optional[ByteRange] = None
    discontinuity: bool = False
    program_date_time: Optional[str] = None
    #: Filled in by the downloader: where the decoded bytes were staged.
    local_path: Optional[str] = None


@dataclass
class Variant:
    """A rendition advertised by a master playlist."""

    uri: str
    bandwidth: Optional[int] = None
    average_bandwidth: Optional[int] = None
    resolution: Optional[tuple[int, int]] = None
    codecs: Optional[str] = None
    frame_rate: Optional[float] = None
    name: Optional[str] = None
    audio_group: Optional[str] = None
    subtitle_group: Optional[str] = None

    @property
    def label(self) -> str:
        parts = []
        if self.resolution:
            parts.append(f"{self.resolution[0]}x{self.resolution[1]}")
        if self.name:
            parts.append(self.name)
        bandwidth = self.average_bandwidth or self.bandwidth
        if bandwidth is not None:
            parts.append(f"{int(bandwidth / 1000)} kbps")
        if self.codecs:
            parts.append(self.codecs)
        return " ".join(parts) or self.uri

    @property
    def height(self) -> int:
        return self.resolution[1] if self.resolution else 0

    @property
    def effective_bandwidth(self) -> int:
        return int(self.average_bandwidth or self.bandwidth or 0)


@dataclass
class Rendition:
    """An ``#EXT-X-MEDIA`` alternate track (audio or subtitle)."""

    type: str
    group_id: str
    name: str
    uri: Optional[str] = None
    language: Optional[str] = None
    default: bool = False
    autoselect: bool = False
    forced: bool = False
    channels: Optional[str] = None


@dataclass
class MediaPlaylist:
    """A concrete list of segments that can be downloaded."""

    uri: str
    segments: list[Segment] = field(default_factory=list)
    target_duration: float = 0.0
    media_sequence: int = 0
    version: Optional[int] = None
    has_endlist: bool = False

    @property
    def is_live(self) -> bool:
        return not self.has_endlist

    @property
    def total_duration(self) -> float:
        return sum(seg.duration for seg in self.segments)

    @property
    def encryption_methods(self) -> set[str]:
        return {seg.key.method.upper() for seg in self.segments if seg.key}

    def __len__(self) -> int:
        return len(self.segments)

    def __iter__(self) -> Iterator[Segment]:
        return iter(self.segments)


@dataclass
class MasterPlaylist:
    """A playlist that lists other playlists."""

    uri: str
    variants: list[Variant] = field(default_factory=list)
    renditions: list[Rendition] = field(default_factory=list)
    version: Optional[int] = None

    def subtitle_renditions(self) -> list[Rendition]:
        return [r for r in self.renditions if r.type.upper() == "SUBTITLES" and r.uri]

    def audio_renditions(self) -> list[Rendition]:
        return [r for r in self.renditions if r.type.upper() == "AUDIO" and r.uri]


# --------------------------------------------------------------------------
# parser
# --------------------------------------------------------------------------
def parse_playlist(text: str, base_url: str) -> "MasterPlaylist | MediaPlaylist":
    """Parse ``text`` into a :class:`MasterPlaylist` or :class:`MediaPlaylist`."""
    if "#EXTM3U" not in text:
        raise HlsError("not an m3u8 playlist (missing #EXTM3U)")

    lines = [line.strip() for line in text.splitlines()]

    for line in lines:
        if line.startswith("#EXT-X-SESSION-KEY:"):
            attrs = parse_attribute_list(line.split(":", 1)[1])
            method = attrs.get("METHOD", "NONE").upper()
            key_format = attrs.get("KEYFORMAT")
            if method not in ("NONE", "AES-128") or (
                method == "AES-128" and key_format and key_format.lower() != "identity"
            ):
                raise UnsupportedEncryption("the HLS session advertises DRM/protected content")

    # ---- master detection first: #EXT-X-STREAM-INF is decisive ----------
    if any(line.startswith("#EXT-X-STREAM-INF") for line in lines):
        return _parse_master(lines, base_url)
    return _parse_media(lines, base_url)


def _parse_master(lines: list[str], base_url: str) -> MasterPlaylist:
    master = MasterPlaylist(uri=base_url)
    pending: Optional[dict[str, str]] = None

    for line in lines:
        if not line:
            continue
        if line.startswith("#EXT-X-VERSION"):
            master.version = _to_int(line.split(":", 1)[1].strip(), 0) or None
        elif line.startswith("#EXT-X-STREAM-INF"):
            pending = parse_attribute_list(line.split(":", 1)[1])
        elif line.startswith("#EXT-X-MEDIA"):
            attrs = parse_attribute_list(line.split(":", 1)[1])
            uri = attrs.get("URI")
            master.renditions.append(
                Rendition(
                    type=attrs.get("TYPE", "").upper(),
                    group_id=attrs.get("GROUP-ID", ""),
                    name=attrs.get("NAME", ""),
                    uri=urljoin(base_url, uri) if uri else None,
                    language=attrs.get("LANGUAGE"),
                    default=attrs.get("DEFAULT", "NO").upper() == "YES",
                    autoselect=attrs.get("AUTOSELECT", "NO").upper() == "YES",
                    forced=attrs.get("FORCED", "NO").upper() == "YES",
                    channels=attrs.get("CHANNELS"),
                )
            )
        elif line.startswith("#"):
            continue
        else:
            # A URI line: closes the preceding #EXT-X-STREAM-INF when present.
            if pending is not None:
                resolution = None
                if "RESOLUTION" in pending:
                    match = _RESOLUTION_RE.match(pending["RESOLUTION"])
                    if match:
                        resolution = (int(match.group(1)), int(match.group(2)))
                master.variants.append(
                    Variant(
                        uri=urljoin(base_url, line),
                        bandwidth=_to_int(pending.get("BANDWIDTH")) or None,
                        average_bandwidth=_to_int(pending.get("AVERAGE-BANDWIDTH")) or None,
                        resolution=resolution,
                        codecs=pending.get("CODECS"),
                        frame_rate=_to_float(pending.get("FRAME-RATE")) or None,
                        name=pending.get("NAME"),
                        audio_group=pending.get("AUDIO"),
                        subtitle_group=pending.get("SUBTITLES"),
                    )
                )
                pending = None
            else:
                # A bare URI in a master playlist: treat as a single variant.
                master.variants.append(Variant(uri=urljoin(base_url, line)))

    if not master.variants:
        raise HlsError("master playlist declares no variants")
    return master


def _parse_media(lines: list[str], base_url: str) -> MediaPlaylist:
    playlist = MediaPlaylist(uri=base_url)
    current_key: Optional[Key] = None
    current_map: Optional[str] = None
    current_map_range: Optional[ByteRange] = None
    pending_duration: Optional[float] = None
    pending_title: Optional[str] = None
    pending_range: Optional[ByteRange] = None
    pending_discontinuity = False
    pending_pdt: Optional[str] = None
    prev_range_end = 0
    seq = 0

    for line in lines:
        if not line:
            continue

        if line.startswith("#EXT-X-VERSION"):
            playlist.version = _to_int(line.split(":", 1)[1].strip(), 0) or None

        elif line.startswith("#EXT-X-TARGETDURATION"):
            playlist.target_duration = _to_float(line.split(":", 1)[1].strip(), 0.0)

        elif line.startswith("#EXT-X-MEDIA-SEQUENCE"):
            playlist.media_sequence = _to_int(line.split(":", 1)[1].strip(), 0)

        elif line.startswith("#EXT-X-ENDLIST"):
            playlist.has_endlist = True

        elif line.startswith("#EXT-X-DISCONTINUITY-SEQUENCE"):
            continue

        elif line.startswith("#EXT-X-DISCONTINUITY"):
            pending_discontinuity = True

        elif line.startswith("#EXT-X-PROGRAM-DATE-TIME"):
            pending_pdt = line.split(":", 1)[1].strip()

        elif line.startswith("#EXT-X-KEY"):
            attrs = parse_attribute_list(line.split(":", 1)[1])
            method = attrs.get("METHOD", "NONE").upper()
            key_format = attrs.get("KEYFORMAT")
            if method == "AES-128" and key_format and key_format.lower() != "identity":
                raise UnsupportedEncryption(
                    "non-identity AES key formats are DRM/protected content and are not supported"
                )
            if method == "NONE":
                current_key = None
            elif method not in ("AES-128",):
                raise UnsupportedEncryption(
                    f"segment encryption METHOD={method} is DRM/protected content; "
                    "this tool only handles unencrypted or AES-128 (non-DRM) HLS"
                )
            else:
                uri = attrs.get("URI")
                iv_raw = attrs.get("IV")
                iv = None
                if iv_raw:
                    iv_hex = iv_raw[2:] if iv_raw.lower().startswith("0x") else iv_raw
                    try:
                        iv = bytes.fromhex(iv_hex.rjust(32, "0"))
                    except ValueError as exc:
                        raise HlsError(f"bad IV {iv_raw!r}") from exc
                current_key = Key(
                    method=method,
                    uri=urljoin(base_url, uri) if uri else None,
                    iv=iv,
                    key_format=key_format,
                    key_format_versions=attrs.get("KEYFORMATVERSIONS"),
                )

        elif line.startswith("#EXT-X-MAP"):
            attrs = parse_attribute_list(line.split(":", 1)[1])
            map_uri = attrs.get("URI")
            current_map = urljoin(base_url, map_uri) if map_uri else None
            current_map_range = _parse_range(attrs.get("BYTERANGE"), 0)

        elif line.startswith("#EXT-X-BYTERANGE"):
            pending_range = _parse_range(line.split(":", 1)[1].strip(), prev_range_end)

        elif line.startswith("#EXTINF"):
            payload = line[len("#EXTINF:") :]
            value, _, title = payload.partition(",")
            pending_duration = _to_float(value.strip(), 0.0)
            pending_title = title.strip() or None

        elif line.startswith("#"):
            continue

        else:
            # URI line -> emit a segment.
            if pending_range is not None and pending_range.offset == prev_range_end:
                # remember where this range ended so "n@offset"-less ranges chain
                prev_range_end = pending_range.offset + pending_range.length
            uri = urljoin(base_url, line)
            playlist.segments.append(
                Segment(
                    uri=uri,
                    duration=pending_duration if pending_duration is not None else 0.0,
                    sequence=playlist.media_sequence + seq,
                    title=pending_title,
                    key=current_key,
                    init_section=current_map,
                    init_byte_range=current_map_range,
                    byte_range=pending_range,
                    discontinuity=pending_discontinuity,
                    program_date_time=pending_pdt,
                )
            )
            seq += 1
            pending_duration = None
            pending_title = None
            pending_range = None
            pending_discontinuity = False
            pending_pdt = None

    if not playlist.segments:
        if playlist.is_live:
            raise HlsError("media playlist contains no segments (is the stream live and empty?)")
        raise HlsError("media playlist contains no segments")
    return playlist


def _parse_range(value: Optional[str], default_offset: int) -> Optional[ByteRange]:
    if not value:
        return None
    text = value.strip()
    if "@" in text:
        length, _, offset = text.partition("@")
        return ByteRange(length=_to_int(length), offset=_to_int(offset))
    return ByteRange(length=_to_int(text), offset=default_offset)


# --------------------------------------------------------------------------
# selection helpers
# --------------------------------------------------------------------------
def select_variant(master: MasterPlaylist, quality: str | int | None) -> Variant:
    """Pick a variant from a master playlist.

    ``quality`` accepts ``"best"``, ``"worst"``, a height such as ``1080`` (the
    closest height that is not smaller is preferred), or ``None`` for best.
    """
    variants = sorted(master.variants, key=lambda v: (v.height, v.effective_bandwidth))

    if quality in (None, "best"):
        return variants[-1]
    if quality == "worst":
        return variants[0]
    if isinstance(quality, int) or (isinstance(quality, str) and quality.isdigit()):
        target = int(quality)
        at_or_above = [v for v in variants if v.height >= target]
        if at_or_above:
            return at_or_above[0]
        return variants[-1]
    raise ValueError(f"unsupported quality selector: {quality!r} (use best/worst/<height>)")
