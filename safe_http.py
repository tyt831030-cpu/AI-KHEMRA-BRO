"""HTTP safety boundary for the public, link-only download service."""
from __future__ import annotations

import ipaddress
import socket
import threading
import time
from urllib.parse import urljoin, urlsplit

from requests import Response

from cddl.http import HttpSession


class UnsafeUrlError(ValueError):
    """The requested URL or redirect is not an acceptable public HTTP target."""


class DownloadBudgetExceeded(RuntimeError):
    """A job exceeded its byte or runtime budget."""


class DownloadBudget:
    def __init__(self, max_bytes: int, max_seconds: int) -> None:
        self.max_bytes = max_bytes
        self.max_seconds = max_seconds
        self.started = time.monotonic()
        self.bytes_used = 0
        self.exceeded = False
        self._lock = threading.Lock()

    @property
    def remaining(self) -> int:
        with self._lock:
            return max(0, self.max_bytes - self.bytes_used)

    @property
    def remaining_seconds(self) -> float:
        with self._lock:
            return max(0.0, self.max_seconds - (time.monotonic() - self.started))

    def check_time(self) -> None:
        with self._lock:
            if time.monotonic() - self.started >= self.max_seconds:
                self.exceeded = True
                raise DownloadBudgetExceeded("download time budget exceeded")

    def check_length(self, length: int) -> None:
        with self._lock:
            if time.monotonic() - self.started >= self.max_seconds or length > self.max_bytes - self.bytes_used:
                self.exceeded = True
                raise DownloadBudgetExceeded("download budget exceeded")

    def check_response_size(self, length: int, maximum: int) -> None:
        with self._lock:
            if time.monotonic() - self.started >= self.max_seconds or length > maximum:
                self.exceeded = True
                raise DownloadBudgetExceeded("individual response limit exceeded")

    def consume(self, amount: int) -> None:
        if amount <= 0:
            return
        with self._lock:
            if time.monotonic() - self.started >= self.max_seconds or amount > self.max_bytes - self.bytes_used:
                self.exceeded = True
                raise DownloadBudgetExceeded("download budget exceeded")
            self.bytes_used += amount


class LimitedResponse:
    """A small proxy that counts bytes and caps responses that callers buffer."""

    def __init__(self, response, budget: DownloadBudget, *, max_content_bytes: int = 16 * 1024 * 1024) -> None:
        self._response = response
        self._budget = budget
        self._max_content_bytes = max_content_bytes
        self._content_cache: bytes | None = None

    def __getattr__(self, name):
        return getattr(self._response, name)

    @property
    def content(self) -> bytes:
        if self._content_cache is not None:
            return self._content_cache
        length_header = self._response.headers.get("Content-Length")
        if length_header:
            try:
                content_length = int(length_header)
            except (TypeError, ValueError):
                content_length = 0
            if content_length > 0:
                self._budget.check_response_size(content_length, self._max_content_bytes)
                self._budget.check_length(content_length)
        chunks: list[bytes] = []
        response_bytes = 0
        for chunk in self._response.iter_content(chunk_size=64 * 1024):
            if chunk:
                response_bytes += len(chunk)
                self._budget.check_response_size(response_bytes, self._max_content_bytes)
                self._budget.consume(len(chunk))
                chunks.append(chunk)
        self._content_cache = b"".join(chunks)
        self._response._content = self._content_cache
        self._response._content_consumed = True
        return self._content_cache

    def iter_content(self, chunk_size=1, decode_unicode=False):
        step = chunk_size or 1
        if self._content_cache is not None:
            for start in range(0, len(self._content_cache), step):
                yield self._content_cache[start : start + step]
            return
        length_header = self._response.headers.get("Content-Length")
        if length_header:
            try:
                self._budget.check_length(int(length_header))
            except (TypeError, ValueError):
                pass
        for chunk in self._response.iter_content(chunk_size=chunk_size, decode_unicode=decode_unicode):
            if chunk:
                byte_count = len(chunk.encode("utf-8")) if isinstance(chunk, str) else len(chunk)
                self._budget.consume(byte_count)
            yield chunk

    def close(self) -> None:
        self._response.close()


_ALLOWED_PORTS = {80, 443}
_MAX_REDIRECTS = 5
_PLAYLIST_CONTENT_LIMIT = 4 * 1024 * 1024
_BUFFERED_RESPONSE_LIMIT = 16 * 1024 * 1024
_DNS_PIN = threading.local()
_ORIGINAL_GETADDRINFO = socket.getaddrinfo


def _getaddrinfo_with_pin(host, port, family=0, type=0, proto=0, flags=0):
    """Use the just-validated DNS answer on this thread, preserving TLS hostname checks."""
    target = getattr(_DNS_PIN, "target", None)
    if target is not None:
        pinned_host, pinned_port, addresses = target
        host_key = str(host).strip("[]").rstrip(".").lower()
        try:
            requested_port = int(port)
        except (TypeError, ValueError):
            requested_port = -1
        if host_key == pinned_host and requested_port == pinned_port:
            rows = []
            for address in addresses:
                address_family = socket.AF_INET if address.version == 4 else socket.AF_INET6
                if family not in (0, socket.AF_UNSPEC, address_family):
                    continue
                socktype = type or socket.SOCK_STREAM
                sockaddr = (str(address), requested_port) if address.version == 4 else (str(address), requested_port, 0, 0)
                rows.append((address_family, socktype, proto, "", sockaddr))
            if rows:
                return rows
            raise socket.gaierror(socket.EAI_ADDRFAMILY, "no validated address matches the requested family")
    return _ORIGINAL_GETADDRINFO(host, port, family, type, proto, flags)


# Pinning is thread-local and only applies to the matching host/port during a
# validated request; all unrelated process lookups delegate to the original.
if socket.getaddrinfo is not _getaddrinfo_with_pin:
    socket.getaddrinfo = _getaddrinfo_with_pin


def validate_public_url(url: str) -> tuple[str, int, tuple[ipaddress.IPv4Address | ipaddress.IPv6Address, ...]]:
    """Validate URL syntax and return the exact public DNS answers to pin."""
    if not url or len(url) > 2048 or any(ord(char) < 32 or ord(char) == 127 for char in url):
        raise UnsafeUrlError("invalid URL")
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise UnsafeUrlError("invalid URL") from exc
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"} or not parsed.hostname:
        raise UnsafeUrlError("only public HTTP(S) URLs are supported")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeUrlError("URL credentials are not supported")
    default_port = 443 if scheme == "https" else 80
    effective_port = port or default_port
    if port is not None and (port not in _ALLOWED_PORTS or port != default_port):
        raise UnsafeUrlError("non-standard URL ports are not supported")

    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".localhost") or host.endswith(".local"):
        raise UnsafeUrlError("local network targets are blocked")

    try:
        literal = ipaddress.ip_address(host)
        addresses = [literal]
    except ValueError:
        try:
            host = host.encode("idna").decode("ascii")
            rows = socket.getaddrinfo(host, effective_port, type=socket.SOCK_STREAM)
        except (OSError, UnicodeError) as exc:
            raise UnsafeUrlError("host could not be resolved") from exc
        addresses = []
        for row in rows:
            try:
                addresses.append(ipaddress.ip_address(str(row[4][0]).split("%", 1)[0]))
            except ValueError as exc:
                raise UnsafeUrlError("host resolved to an invalid address") from exc

    if not addresses or any(not address.is_global for address in addresses):
        raise UnsafeUrlError("private, loopback, reserved, and local addresses are blocked")
    return host, effective_port, tuple(addresses)


class SafeHttpSession(HttpSession):
    """HttpSession with validated redirects, pinned DNS, and job-wide limits."""

    def __init__(self, *, budget: DownloadBudget, **kwargs) -> None:
        super().__init__(**kwargs)
        self.budget = budget
        self.unsafe_target_seen = False
        self._session.trust_env = False

    def request(self, method: str, url: str, **kwargs) -> Response:
        requested_stream = bool(kwargs.pop("stream", False))
        requested_timeout = float(kwargs.pop("timeout", self.timeout))
        kwargs.pop("allow_redirects", None)
        verb = method.upper()
        if verb not in {"GET", "HEAD"}:
            raise UnsafeUrlError("only GET and HEAD requests are supported")

        current = url
        for redirect_number in range(_MAX_REDIRECTS + 1):
            self.budget.check_time()
            try:
                host, port, addresses = validate_public_url(current)
            except UnsafeUrlError:
                self.unsafe_target_seen = True
                raise

            previous_pin = getattr(_DNS_PIN, "target", None)
            _DNS_PIN.target = (host, port, addresses)
            try:
                effective_timeout = min(requested_timeout, self.budget.remaining_seconds)
                if effective_timeout <= 0:
                    self.budget.check_time()
                response = super().request(
                    verb,
                    current,
                    stream=True,
                    timeout=effective_timeout,
                    allow_redirects=False,
                    **kwargs,
                )
            finally:
                if previous_pin is None:
                    try:
                        del _DNS_PIN.target
                    except AttributeError:
                        pass
                else:
                    _DNS_PIN.target = previous_pin

            if not response.is_redirect:
                response_path = urlsplit(current).path.lower()
                response_limit = _PLAYLIST_CONTENT_LIMIT if response_path.endswith(".m3u8") else _BUFFERED_RESPONSE_LIMIT
                wrapped = LimitedResponse(response, self.budget, max_content_bytes=response_limit)
                if not requested_stream and verb != "HEAD":
                    _ = wrapped.content
                return wrapped  # type: ignore[return-value]

            location = response.headers.get("Location")
            response.close()
            if not location or redirect_number >= _MAX_REDIRECTS:
                raise UnsafeUrlError("redirect limit exceeded")
            current = urljoin(current, location)

        raise UnsafeUrlError("redirect limit exceeded")
