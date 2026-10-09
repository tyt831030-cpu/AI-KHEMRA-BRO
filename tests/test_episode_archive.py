import io
import unittest
import zipfile
from unittest.mock import patch

from episode_archive import ArchiveLimitExceeded, build_episode_archive


class EpisodeArchiveTests(unittest.TestCase):
    def test_builds_ordered_zip_using_one_shared_budget(self):
        calls = []

        def fake_download(url, **kwargs):
            calls.append((url, kwargs))
            number = kwargs["episode"]
            return f"mp4-{number}".encode(), {"file": f"S01E{number:03d}.mp4"}

        episodes = [
            {"number": 1, "title": "First", "media_url": "https://cdn.example/one.mp4"},
            {"number": 2, "title": "Second", "media_url": "https://cdn.example/two.m3u8"},
        ]
        archive_bytes, archive_name = build_episode_archive(episodes, "Sample Drama", downloader=fake_download)

        self.assertEqual(archive_name, "Sample Drama_episodes.zip")
        self.assertIs(calls[0][1]["budget"], calls[1][1]["budget"])
        self.assertEqual(calls[1][1]["max_output_bytes"], calls[0][1]["max_output_bytes"] - len(b"mp4-1"))
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            self.assertEqual(archive.namelist(), ["S01E001.mp4", "S01E002.mp4"])
            self.assertEqual(archive.read("S01E001.mp4"), b"mp4-1")
            self.assertEqual(archive.read("S01E002.mp4"), b"mp4-2")

    def test_rejects_an_episode_without_a_supported_media_link(self):
        with self.assertRaisesRegex(ValueError, "no supported direct media link"):
            build_episode_archive([{"number": 1, "title": "Episode 1", "media_url": None}], "Sample")

    def test_stops_when_the_archive_size_budget_is_exceeded(self):
        episode = {"number": 1, "title": "First", "media_url": "https://cdn.example/one.mp4"}
        with patch("episode_archive.MAX_BROWSER_FILE_BYTES", 4):
            with self.assertRaises(ArchiveLimitExceeded):
                build_episode_archive([episode], "Sample", downloader=lambda *args, **kwargs: (b"12345", {"file": "one.mp4"}))


if __name__ == "__main__":
    unittest.main()
