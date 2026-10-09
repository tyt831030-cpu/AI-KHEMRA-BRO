import unittest
from unittest.mock import patch

from safe_http import DownloadBudget, DownloadBudgetExceeded, UnsafeUrlError, validate_public_url


class UrlPolicyTests(unittest.TestCase):
    @patch("safe_http.socket.getaddrinfo")
    def test_accepts_public_https_hostname(self, resolver):
        resolver.return_value = [(2, 1, 6, "", ("93.184.216.34", 443))]
        validate_public_url("https://media.example/video.m3u8")

    @patch("safe_http.socket.getaddrinfo")
    def test_rejects_hostname_resolving_to_private_network(self, resolver):
        resolver.return_value = [(2, 1, 6, "", ("10.1.2.3", 443))]
        with self.assertRaises(UnsafeUrlError):
            validate_public_url("https://media.example/video.m3u8")

    def test_rejects_loopback_ip(self):
        with self.assertRaises(UnsafeUrlError):
            validate_public_url("http://127.0.0.1/video.m3u8")

    def test_rejects_url_credentials_and_nonstandard_ports(self):
        with self.assertRaises(UnsafeUrlError):
            validate_public_url("https://user:pass@example.com/video.m3u8")
        with self.assertRaises(UnsafeUrlError):
            validate_public_url("https://example.com:8443/video.m3u8")


class DownloadBudgetTests(unittest.TestCase):
    def test_byte_budget_is_shared_and_enforced(self):
        budget = DownloadBudget(max_bytes=10, max_seconds=60)
        budget.consume(7)
        with self.assertRaises(DownloadBudgetExceeded):
            budget.consume(4)
        self.assertTrue(budget.exceeded)


if __name__ == "__main__":
    unittest.main()
