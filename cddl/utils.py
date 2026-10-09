"""Small shared helpers: byte formatting, progress accounting, atomic writes."""
from __future__ import annotations

import os
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Optional


def human_bytes(n: float) -> str:
    """Format a byte count the way a human reads it (1024-based)."""
    n = float(n)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(n) < 1024.0 or unit == "TiB":
            return f"{n:,.0f} {unit}" if unit == "B" else f"{n:,.2f} {unit}"
        n /= 1024.0
    return f"{n:.2f} TiB"


def human_time(seconds: float) -> str:
    """Format a duration as ``1h02m03s`` / ``02m03s`` / ``03s``."""
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m{s:02d}s"
    if m:
        return f"{m:02d}m{s:02d}s"
    return f"{s:02d}s"


def human_duration_hms(seconds: float) -> str:
    """Format media duration as ``HH:MM:SS.mmm``."""
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def atomic_write(path: str, data: bytes) -> None:
    """Write ``data`` to ``path`` so that readers never observe a partial file."""
    tmp = f"{path}.part-{os.getpid()}-{threading.get_ident()}"
    with open(tmp, "wb") as fh:
        fh.write(data)
    os.replace(tmp, path)


@dataclass
class Progress:
    """Thread-safe progress accounting shared by all segment workers."""

    total: int = 0
    started_at: float = field(default_factory=time.monotonic)
    done: int = 0
    bytes_done: int = 0
    failed: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _last_render: float = 0.0

    def add(self, nbytes: int) -> None:
        with self._lock:
            self.done += 1
            self.bytes_done += nbytes

    def fail(self) -> None:
        with self._lock:
            self.failed += 1

    def snapshot(self) -> tuple[int, int, int]:
        with self._lock:
            return self.done, self.bytes_done, self.failed

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self.started_at

    def render(self, label: str = "", *, force: bool = False, stream=None) -> None:
        """Redraw a one-line status bar (TTY) or nothing (piped output)."""
        stream = stream or sys.stderr
        now = time.monotonic()
        if not force and now - self._last_render < 0.4:
            return
        self._last_render = now
        done, nbytes, failed = self.snapshot()
        pct = (done / self.total * 100.0) if self.total else 0.0
        speed = nbytes / self.elapsed if self.elapsed > 0 else 0.0
        eta = ((self.total - done) / (done / self.elapsed)) if done and self.elapsed > 0 else 0.0
        line = (
            f"  {label} {done}/{self.total} segments ({pct:5.1f}%)  "
            f"{human_bytes(nbytes)}  {human_bytes(speed)}/s  ETA {human_time(eta)}"
        )
        if failed:
            line += f"  [{failed} retried]"
        if stream.isatty():
            try:
                width = os.get_terminal_size().columns - 1
            except OSError:
                width = 120
            stream.write("\r" + line[:width].ljust(width)[:width])
            stream.flush()
            if force:
                stream.write("\n")
        elif force:
            stream.write(line + "\n")
            stream.flush()


class NullProgress:
    """No-op progress object used by library callers that want silence."""

    def __init__(self, total: int = 0) -> None:
        self.total = total

    @property
    def elapsed(self) -> float:  # noqa: D102
        return 0.0

    def snapshot(self) -> tuple[int, int, int]:  # noqa: D102
        return (0, 0, 0)

    def add(self, nbytes: int) -> None:  # noqa: D102
        pass

    def fail(self) -> None:  # noqa: D102
        pass

    def render(self, label: str = "", *, force: bool = False, stream=None) -> None:  # noqa: D102
        pass


def parse_int_set(spec: str) -> list[int]:
    """Parse ``"1-5,9,12"`` into ``[1, 2, 3, 4, 5, 9, 12]`` (order preserved)."""
    out: list[int] = []
    for chunk in spec.replace(" ", "").split(","):
        if not chunk:
            continue
        if "-" in chunk:
            a, b = chunk.split("-", 1)
            start, end = int(a), int(b)
            step = 1 if end >= start else -1
            out.extend(range(start, end + step, step))
        else:
            out.append(int(chunk))
    seen, uniq = set(), []
    for n in out:
        if n not in seen:
            seen.add(n)
            uniq.append(n)
    return uniq


def parse_kv_header(value: str) -> tuple[str, str]:
    """Parse ``"Referer: https://x/"`` into ``("Referer", "https://x/")``."""
    if ":" not in value:
        raise ValueError(f"header must look like 'Name: value', got {value!r}")
    name, _, val = value.partition(":")
    return name.strip(), val.strip()


def parse_cookie_string(value: str) -> dict[str, str]:
    """Parse a ``document.cookie`` style string into a dict."""
    jar: dict[str, str] = {}
    for part in value.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        k, _, v = part.partition("=")
        jar[k.strip()] = v.strip()
    return jar


def load_cookie_file(path: str) -> dict[str, str]:
    """Load cookies from a JSON object, a Netscape cookie file, or ``k=v`` lines."""
    import json

    with open(path, "r", encoding="utf-8-sig") as fh:
        text = fh.read()

    stripped = text.lstrip()
    if stripped.startswith("{"):
        data = json.loads(stripped)
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
        raise ValueError("cookie JSON must be an object of name/value pairs")

    jar: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) >= 7:  # Netscape format
            jar[fields[5]] = fields[6]
        elif "=" in line:
            k, _, v = line.partition("=")
            jar[k.strip()] = v.strip()
    return jar


def which_ffmpeg() -> Optional[str]:
    """Return the ffmpeg executable path, or ``None``."""
    from shutil import which

    return which("ffmpeg")
