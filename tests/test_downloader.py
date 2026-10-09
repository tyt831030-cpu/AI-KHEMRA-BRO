import tempfile
import unittest
from pathlib import Path
from typing import cast

from cddl.downloader import SegmentDownloader
from cddl.http import HttpSession
from cddl.hls import MediaPlaylist, Segment


class FakeResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def close(self) -> None:
        pass


class FakeSession:
    def __init__(self, resources: dict[str, bytes]) -> None:
        self.resources = resources
        self.init_requests: list[str] = []

    def get_bytes(self, url: str, **_kwargs) -> bytes:
        self.init_requests.append(url)
        return self.resources[url]

    def get(self, url: str, **_kwargs) -> FakeResponse:
        return FakeResponse(self.resources[url])


class InitSectionTests(unittest.TestCase):
    def test_concatenation_writes_each_init_only_when_map_changes(self):
        resources = {
            "https://media.example/init-a.mp4": b"INIT-A",
            "https://media.example/init-b.mp4": b"INIT-B",
            "https://media.example/part-1.m4s": b"PART-1",
            "https://media.example/part-2.m4s": b"PART-2",
            "https://media.example/part-3.m4s": b"PART-3",
        }
        playlist = MediaPlaylist(
            uri="https://media.example/episode.m3u8",
            has_endlist=True,
            segments=[
                Segment(uri="https://media.example/part-1.m4s", duration=1, sequence=0,
                        init_section="https://media.example/init-a.mp4"),
                Segment(uri="https://media.example/part-2.m4s", duration=1, sequence=1,
                        init_section="https://media.example/init-a.mp4"),
                Segment(uri="https://media.example/part-3.m4s", duration=1, sequence=2,
                        init_section="https://media.example/init-b.mp4"),
            ],
        )
        fake_session = FakeSession(resources)
        downloader = SegmentDownloader(cast(HttpSession, fake_session), workers=1, quiet=True)

        with tempfile.TemporaryDirectory() as root:
            stage = Path(root) / "stage"
            downloader.fetch_all(playlist, str(stage))
            output = Path(root) / "joined.mp4"
            downloader.concatenate(str(stage), playlist, str(output))
            self.assertEqual(output.read_bytes(), b"INIT-APART-1PART-2INIT-BPART-3")

        self.assertCountEqual(
            fake_session.init_requests,
            ["https://media.example/init-a.mp4", "https://media.example/init-b.mp4"],
        )
        self.assertEqual(len(fake_session.init_requests), 2)


if __name__ == "__main__":
    unittest.main()
