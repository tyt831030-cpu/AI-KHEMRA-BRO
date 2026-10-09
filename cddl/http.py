"""Hardened HTTP layer.

One :class:`HttpSession` is shared by every worker thread of a job so that
connection pooling, cookies and headers stay consistent.  Retries use
exponential backoff with jitter and honour ``Retry-After``.
"""
from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass
from typing import Iterable, Mapping, Optional, Sequence

import requests
from requests.adapters import HTTPAdapter

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

#: HTTP statuses worth retrying (transient by nature).
RETRYABLE_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})

#: Default set of origins we accept when following redirects for media.
_MEDIA_ACCEPT = "*/*"


class HttpError(RuntimeError):
    """Raised for a transport failure or an unexpected status code."""

    def __init__(self, message: str, *, status: Optional[int] = None, url: Optional[str] = None):
        super().__init__(message)
        self.status = status
        self.url = url


@dataclass
class RetryPolicy:
    """How hard to try before giving up on a single request."""

    attempts: int = 5
    backoff: float = 0.8
    backoff_max: float = 20.0
    jitter: float = 0.35

    def delay_for(self, attempt: int, retry_after: Optional[str] = None) -> float:
        if retry_after:
            try:
                return min(float(retry_after), 60.0)
            except (TypeError, ValueError):
                pass
        base = min(self.backoff * (2 ** (attempt - 1)), self.backoff_max)
        return base + random.uniform(0.0, base * self.jitter)


class HttpSession:
    """A pooling, retrying, thread-safe HTTP client."""

    def __init__(
        self,
        *,
        headers: Optional[Mapping[str, str]] = None,
        cookies: Optional[Mapping[str, str]] = None,
        timeout: float = 30.0,
        retry: Optional[RetryPolicy] = None,
        pool_size: int = 64,
        proxy: Optional[str] = None,
        verify: bool = True,
        user_agent: Optional[str] = None,
    ) -> None:
        self.timeout = timeout
        self.retry = retry or RetryPolicy()
        self._verify = verify
        self._lock = threading.Lock()

        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": user_agent or DEFAULT_UA,
                "Accept": _MEDIA_ACCEPT,
                "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
                "Connection": "keep-alive",
            }
        )
        if headers:
            session.headers.update(dict(headers))
        if cookies:
            session.cookies.update(dict(cookies))

        adapter = HTTPAdapter(pool_connections=pool_size, pool_maxsize=pool_size, max_retries=0)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        if proxy:
            session.proxies.update({"http": proxy, "https": proxy})

        self._session = session

    # -- header helpers -------------------------------------------------
    def update_headers(self, headers: Mapping[str, str]) -> None:
        """Merge extra headers (e.g. a per-host Referer) into the session."""
        with self._lock:
            self._session.headers.update(dict(headers))

    def update_cookies(self, cookies: Mapping[str, str]) -> None:
        with self._lock:
            self._session.cookies.update(dict(cookies))

    # -- core request ---------------------------------------------------
    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Perform a request, retrying transient failures."""
        headers = kwargs.pop("headers", None)
        stream = kwargs.pop("stream", False)
        allow_redirects = kwargs.pop("allow_redirects", True)
        timeout = kwargs.pop("timeout", self.timeout)

        last_error: Optional[BaseException] = None
        for attempt in range(1, self.retry.attempts + 1):
            try:
                response = self._session.request(
                    method,
                    url,
                    headers=headers,
                    timeout=timeout,
                    stream=stream,
                    allow_redirects=allow_redirects,
                    verify=self._verify,
                    **kwargs,
                )
            except requests.RequestException as exc:
                last_error = exc
                if attempt >= self.retry.attempts:
                    break
                time.sleep(self.retry.delay_for(attempt))
                continue

            if response.status_code in RETRYABLE_STATUS and attempt < self.retry.attempts:
                delay = self.retry.delay_for(attempt, response.headers.get("Retry-After"))
                response.close()
                time.sleep(delay)
                continue
            return response

        raise HttpError(
            f"{method} {url} failed after {self.retry.attempts} attempt(s): {last_error}",
            url=url,
        ) from last_error

    # -- convenience wrappers -------------------------------------------
    def get(
        self,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        expect: Sequence[int] = (200, 206),
        stream: bool = False,
        **kwargs,
    ) -> requests.Response:
        response = self.request("GET", url, headers=headers, stream=stream, **kwargs)
        if expect and response.status_code not in expect:
            response.close()
            raise HttpError(
                f"unexpected HTTP {response.status_code} for {url}",
                status=response.status_code,
                url=url,
            )
        return response

    def get_bytes(
        self, url: str, *, headers: Optional[Mapping[str, str]] = None, expect: Sequence[int] = (200, 206)
    ) -> bytes:
        response = self.get(url, headers=headers, expect=expect, stream=False)
        try:
            return response.content
        finally:
            response.close()

    def get_text(
        self,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        encoding: Optional[str] = None,
        expect: Sequence[int] = (200,),
    ) -> str:
        response = self.get(url, headers=headers, expect=expect, stream=False)
        try:
            # Playlists are ASCII by spec but are occasionally served with a
            # charset in the Content-Type; prefer that, then UTF-8.
            charset = encoding or response.encoding or "utf-8"
            return response.content.decode(charset, errors="replace")
        finally:
            response.close()

    def get_range(
        self,
        url: str,
        start: int,
        length: int,
        *,
        headers: Optional[Mapping[str, str]] = None,
    ) -> bytes:
        """Fetch a byte range (used by ``#EXT-X-BYTERANGE`` segments)."""
        hdrs = {"Range": f"bytes={start}-{start + length - 1}"}
        if headers:
            hdrs.update(headers)
        response = self.get(url, headers=hdrs, expect=(200, 206), stream=False)
        try:
            return response.content
        finally:
            response.close()

    def probe(self, url: str) -> tuple[int, Mapping[str, str]]:
        """HEAD a URL, falling back to a streamed GET when HEAD is refused."""
        try:
            response = self.request("HEAD", url, allow_redirects=True)
            if response.status_code < 400:
                info = dict(response.headers)
                status = response.status_code
                response.close()
                return status, info
            response.close()
        except HttpError:
            pass

        response = self.get(url, expect=(), stream=True)
        try:
            info = dict(response.headers)
            status = response.status_code
            response.close()
            return status, info
        finally:
            response.close()

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "HttpSession":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()