import ipaddress
import socket
import unittest
from unittest.mock import Mock, patch

from requests import Response

from safe_http import (
    DownloadBudget,
    DownloadBudgetExceeded,
    LimitedResponse,
    SafeHttpSession,
    UnsafeUrlError,
    _DNS_PIN,
    _getaddrinfo_with_pin,
)


class FakeBody:
    headers = {}

    def iter_content(self, chunk_size=1, decode_unicode=False):
        yield b"abc"
        yield b"def"

    def close(self):
        pass


class ResponseBudgetTests(unittest.TestCase):
    def test_content_reads_are_counted(self):
        budget = DownloadBudget(max_bytes=10, max_seconds=60)
        wrapped = LimitedResponse(FakeBody(), budget)
        self.assertEqual(wrapped.content, b"abcdef")
        self.assertEqual(budget.bytes_used, 6)

    def test_streaming_read_stops_at_job_budget(self):
        budget = DownloadBudget(max_bytes=4, max_seconds=60)
        wrapped = LimitedResponse(FakeBody(), budget)
        with self.assertRaises(DownloadBudgetExceeded):
            _ = wrapped.content
        self.assertTrue(budget.exceeded)

    def test_buffered_response_cap_applies_without_content_length(self):
        budget = DownloadBudget(max_bytes=100, max_seconds=60)
        wrapped = LimitedResponse(FakeBody(), budget, max_content_bytes=5)
        with self.assertRaises(DownloadBudgetExceeded):
            _ = wrapped.content
        self.assertEqual(budget.bytes_used, 3)
        self.assertTrue(budget.exceeded)

    def test_dns_lookup_uses_the_validated_address_for_the_same_host(self):
        previous = getattr(_DNS_PIN, "target", None)
        _DNS_PIN.target = ("media.example", 443, (ipaddress.ip_address("93.184.216.34"),))
        try:
            with patch("safe_http._ORIGINAL_GETADDRINFO") as original:
                rows = _getaddrinfo_with_pin("media.example", 443, type=socket.SOCK_STREAM)
            self.assertEqual(rows[0][4][0], "93.184.216.34")
            original.assert_not_called()
        finally:
            if previous is None:
                del _DNS_PIN.target
            else:
                _DNS_PIN.target = previous

    def test_redirect_target_is_validated_before_second_request(self):
        redirect = Response()
        redirect.status_code = 302
        redirect.headers["Location"] = "http://127.0.0.1/private"
        redirect._content = b""
        redirect._content_consumed = True
        session = SafeHttpSession(budget=DownloadBudget(max_bytes=100, max_seconds=60), timeout=2)
        session._session.request = Mock(return_value=redirect)
        pinned = ("media.example", 443, (ipaddress.ip_address("93.184.216.34"),))
        with patch("safe_http.validate_public_url", side_effect=[pinned, UnsafeUrlError("private")]):
            with self.assertRaises(UnsafeUrlError):
                session.request("GET", "https://media.example/redirect", stream=True)
        session._session.request.assert_called_once()
        self.assertTrue(session.unsafe_target_seen)
        session.close()


if __name__ == "__main__":
    unittest.main()
