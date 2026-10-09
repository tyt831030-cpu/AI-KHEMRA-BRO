import unittest
from unittest.mock import patch

from episode_discovery import DiscoveryError, discover_episodes


SERIES_URL = "https://series.example/show"
EP1_URL = "https://series.example/ep/1"
EP2_URL = "https://series.example/ep/2"


class FakeResponse:
    def __init__(self, url, body, content_type="text/html; charset=utf-8"):
        self.url = url
        self.content = body.encode("utf-8") if isinstance(body, str) else body
        self.encoding = "utf-8"
        self.status_code = 200
        self.headers = {"Content-Type": content_type, "Content-Length": str(len(self.content))}

    def iter_content(self, chunk_size=1):
        for start in range(0, len(self.content), chunk_size):
            yield self.content[start : start + chunk_size]

    def close(self):
        pass


class FakeSession:
    def __init__(self, pages, **_kwargs):
        self.pages = pages

    def get(self, url, **_kwargs):
        if url in self.pages:
            return FakeResponse(url, self.pages[url])
        if url.lower().endswith(".jpg"):
            return FakeResponse(url, b"fake-image-data", "image/jpeg")
        raise OSError("page not in test fixture")

    def close(self):
        pass


class EpisodeDiscoveryTests(unittest.TestCase):
    def test_finds_episode_titles_media_links_and_same_site_thumbnails(self):
        pages = {
            SERIES_URL: (
                "<html><head><title>Sample Drama</title>"
                '<meta property="og:image" content="/cover.jpg"></head><body>'
                '<a href="/ep/1"><img src="/thumb/1.jpg"/>第1集 初遇</a>'
                '<a href="/ep/2">第2集 重逢</a></body></html>'
            ),
            EP1_URL: (
                "<html><head><title>Sample Drama 第1集</title>"
                '<meta property="og:image" content="/thumb/episode-1.jpg"></head>'
                '<body><video><source src="https://cdn.example/one.m3u8" '
                'type="application/vnd.apple.mpegurl"></video></body></html>'
            ),
            EP2_URL: (
                "<html><head><title>Sample Drama 第2集</title></head>"
                '<body><video src="https://cdn.example/two.mp4"></video></body></html>'
            ),
        }
        import ipaddress

        public_ip = ipaddress.ip_address("93.184.216.34")
        with patch("episode_discovery.validate_public_url", return_value=("example", 443, (public_ip,))):
            result = discover_episodes(SERIES_URL, session_factory=lambda **kwargs: FakeSession(pages, **kwargs))

        self.assertEqual(result.series_title, "Sample Drama")
        self.assertEqual([episode.number for episode in result.episodes], [1, 2])
        self.assertEqual(result.episodes[0].title, "第1集 初遇")
        self.assertEqual(result.episodes[0].media_url, "https://cdn.example/one.m3u8")
        self.assertEqual(result.episodes[0].thumbnail_bytes, b"fake-image-data")
        self.assertEqual(result.episodes[1].media_url, "https://cdn.example/two.mp4")

    def test_direct_public_media_link_becomes_one_episode(self):
        import ipaddress

        public_ip = ipaddress.ip_address("93.184.216.34")
        with patch("episode_discovery.validate_public_url", return_value=("cdn.example", 443, (public_ip,))):
            result = discover_episodes("https://cdn.example/episode-01.m3u8?token=sample")
        self.assertEqual(len(result.episodes), 1)
        self.assertEqual(result.episodes[0].number, 1)
        self.assertEqual(result.episodes[0].media_url, "https://cdn.example/episode-01.m3u8?token=sample")

    def test_cross_origin_episode_pages_are_not_followed(self):
        pages = {
            SERIES_URL: '<html><title>Sample Drama</title><a href="https://other.example/ep/1">第1集</a></html>'
        }
        import ipaddress

        public_ip = ipaddress.ip_address("93.184.216.34")
        with patch("episode_discovery.validate_public_url", return_value=("example", 443, (public_ip,))):
            with self.assertRaises(DiscoveryError):
                discover_episodes(SERIES_URL, session_factory=lambda **kwargs: FakeSession(pages, **kwargs))

    def test_unlisted_dynamic_source_returns_clear_message(self):
        pages = {SERIES_URL: "<html><title>Sample Drama</title><script>loadEpisodes()</script></html>"}
        import ipaddress

        public_ip = ipaddress.ip_address("93.184.216.34")
        with patch("episode_discovery.validate_public_url", return_value=("example", 443, (public_ip,))):
            with self.assertRaisesRegex(DiscoveryError, "JavaScript"):
                discover_episodes(SERIES_URL, session_factory=lambda **kwargs: FakeSession(pages, **kwargs))


if __name__ == "__main__":
    unittest.main()
