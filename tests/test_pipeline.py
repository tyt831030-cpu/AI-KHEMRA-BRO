"""End-to-end test: a local HTTP server serves a real, AES-128 encrypted HLS VOD.

This exercises the whole chain -- extractor -> master playlist -> variant
selection -> media playlist -> concurrent segment fetch -> AES-128 decryption ->
concatenation -> metadata sidecar -- without touching the public internet.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from cddl import Options, download
from cddl.extractors import ExtractorError, get_extractor
from cddl.http import HttpSession
from cddl.job import make_plan

SEGMENT_COUNT = 4
KEY = bytes(range(16))


def _encrypt(plaintext: bytes, sequence: int) -> bytes:
    """AES-128-CBC encrypt with PKCS#7 padding and an IV derived from the sequence."""
    iv = sequence.to_bytes(16, "big")
    padder = padding.PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()
    encryptor = Cipher(algorithms.AES(KEY), modes.CBC(iv)).encryptor()
    return encryptor.update(padded) + encryptor.finalize()


def _plaintexts() -> list[bytes]:
    return [f"segment-{i}-".encode() * (60 + i) for i in range(SEGMENT_COUNT)]


def _audio_plaintexts() -> list[bytes]:
    return [f"track-{i}-".encode() * (40 + i) for i in range(SEGMENT_COUNT)]


def _audio_playlist() -> str:
    lines = [
        "#EXTM3U",
        "#EXT-X-VERSION:3",
        "#EXT-X-TARGETDURATION:4",
        "#EXT-X-MEDIA-SEQUENCE:0",
        "#EXT-X-PLAYLIST-TYPE:VOD",
    ]
    for i in range(SEGMENT_COUNT):
        lines.append("#EXTINF:4.000,")
        lines.append(f"seg-{i}.aac")
    lines.append("#EXT-X-ENDLIST")
    return "\n".join(lines) + "\n"


def _media_playlist(encrypted: bool) -> str:
    lines = [
        "#EXTM3U",
        "#EXT-X-VERSION:3",
        "#EXT-X-TARGETDURATION:4",
        "#EXT-X-MEDIA-SEQUENCE:0",
        "#EXT-X-PLAYLIST-TYPE:VOD",
    ]
    if encrypted:
        # No IV attribute: the player must derive it from the media sequence.
        lines.append('#EXT-X-KEY:METHOD=AES-128,URI="/keys/k1.bin"')
    for i, chunk in enumerate(_plaintexts()):
        name = f"seg-{i}.ts"
        lines.append(f"#EXTINF:4.000,part-{i}")
        lines.append(name)
    lines.append("#EXT-X-ENDLIST")
    return "\n".join(lines) + "\n"


VTT_TRACK = """WEBVTT

00:00:00.000 --> 00:00:04.000
第一集开始

00:00:04.000 --> 00:00:08.000
剧情继续
"""


def _routes() -> dict[str, tuple[str, bytes]]:
    routes: dict[str, tuple[str, bytes]] = {
        "/keys/k1.bin": ("application/octet-stream", KEY),
        "/subs/zh.vtt": ("text/vtt", VTT_TRACK.encode("utf-8")),
    }
    routes["/low/index.m3u8"] = ("application/vnd.apple.mpegurl", _media_playlist(False).encode())
    routes["/high/index.m3u8"] = ("application/vnd.apple.mpegurl", _media_playlist(True).encode())
    routes["/aud/index.m3u8"] = ("application/vnd.apple.mpegurl", _audio_playlist().encode())
    for i, chunk in enumerate(_plaintexts()):
        routes[f"/low/seg-{i}.ts"] = ("video/mp2t", chunk)
        routes[f"/high/seg-{i}.ts"] = ("video/mp2t", _encrypt(chunk, i))
    for i, chunk in enumerate(_audio_plaintexts()):
        routes[f"/aud/seg-{i}.aac"] = ("audio/aac", chunk)

    master = "\n".join(
        [
            "#EXTM3U",
            "#EXT-X-VERSION:6",
            '#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="中文",LANGUAGE="zh",DEFAULT=YES,URI="/subs/zh.vtt"',
            '#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="aud",NAME="原声",LANGUAGE="zh",DEFAULT=YES,URI="/aud/index.m3u8"',
            '#EXT-X-STREAM-INF:BANDWIDTH=600000,AVERAGE-BANDWIDTH=500000,RESOLUTION=640x360,CODECS="avc1.4d401e"',
            "/low/index.m3u8",
            '#EXT-X-STREAM-INF:BANDWIDTH=5000000,AVERAGE-BANDWIDTH=4500000,RESOLUTION=1920x1080,'
            'CODECS="avc1.640028,mp4a.40.2",AUDIO="aud",SUBTITLES="subs"',
            "/high/index.m3u8",
            "",
        ]
    )
    routes["/master.m3u8"] = ("application/vnd.apple.mpegurl", master.encode())
    return routes


def _drm_playlist() -> str:
    return "\n".join(
        [
            "#EXTM3U",
            "#EXT-X-TARGETDURATION:4",
            '#EXT-X-KEY:METHOD=SAMPLE-AES,URI="skd://x",KEYFORMAT="com.apple.streamingkeydelivery"',
            "#EXTINF:4.0,",
            "seg.ts",
            "#EXT-X-ENDLIST",
            "",
        ]
    )


class _Handler(BaseHTTPRequestHandler):
    routes: dict[str, tuple[str, bytes]] = {}
    hits: list = []

    def _respond(self, body: bool) -> None:
        path = urlsplit(self.path).path
        _Handler.hits.append(path)
        entry = _Handler.routes.get(path)
        if entry is None:
            self.send_error(404, "not found")
            return
        ctype, payload = entry
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if body:
            self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802
        self._respond(True)

    def do_HEAD(self) -> None:  # noqa: N802
        self._respond(False)

    def log_message(self, *args) -> None:  # silence the test output
        pass


class PipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _Handler.routes = _routes()
        _Handler.hits = []
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.expected_plain = b"".join(_plaintexts())
        cls.expected_audio = b"".join(_audio_plaintexts())

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="cddl-test-")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- tests -----------------------------------------------------------
    def test_encrypted_1080p_download_decrypts_correctly(self):
        options = Options(
            out_dir=self.tmp,
            show="测试剧集",
            season=1,
            episode=3,
            title="武魂觉醒",
            quality=1080,
            container="ts",
            remux_video=False,   # no ffmpeg needed for the assertion
            workers=4,
            quiet=True,
        )
        result = download(f"{self.base}/master.m3u8", options)

        self.assertFalse(result.skipped)
        self.assertEqual(result.segments, SEGMENT_COUNT)
        self.assertTrue(result.output_path.endswith("测试剧集/S01E003 武魂觉醒.ts"))
        with open(result.output_path, "rb") as fh:
            self.assertEqual(fh.read(), self.expected_plain)

    def test_plain_360p_variant(self):
        options = Options(out_dir=self.tmp, show="plain", quality=360, container="ts",
                          remux_video=False, workers=2, quiet=True)
        result = download(f"{self.base}/master.m3u8", options)
        with open(result.output_path, "rb") as fh:
            self.assertEqual(fh.read(), self.expected_plain)

    def test_metadata_sidecar_records_the_plan(self):
        options = Options(out_dir=self.tmp, show="meta", quality=1080, container="ts",
                          remux_video=False, quiet=True)
        result = download(f"{self.base}/master.m3u8", options)
        self.assertIsNotNone(result.metadata_path)
        with open(result.metadata_path, "r", encoding="utf-8") as fh:
            meta = json.load(fh)
        self.assertEqual(meta["resolution"], [1920, 1080])
        self.assertEqual(meta["segments"], SEGMENT_COUNT)
        self.assertEqual(meta["stream_kind"], "hls")
        self.assertEqual(meta["extractor"], "generic-hls")
        self.assertEqual(meta["audio_rendition"], "原声 [zh]")

    def test_separate_audio_rendition_is_downloaded_and_preserved(self):
        """A variant with AUDIO="aud" must not silently lose its sound."""
        options = Options(out_dir=self.tmp, show="audio", quality=1080, container="ts",
                          remux_video=False, quiet=True)
        result = download(f"{self.base}/master.m3u8", options)

        self.assertIsNotNone(result.audio_path, "the demuxed audio rendition was dropped")
        self.assertTrue(result.audio_path.endswith(".audio.ts"))
        self.assertTrue(os.path.exists(result.audio_path))
        with open(result.audio_path, "rb") as fh:
            self.assertEqual(fh.read(), self.expected_audio)

    def test_plan_reports_the_audio_rendition(self):
        with HttpSession() as session:
            plan = make_plan(
                f"{self.base}/master.m3u8", Options(out_dir=self.tmp, show="p", quality=1080), session
            )
        self.assertEqual(plan.audio_url, f"{self.base}/aud/index.m3u8")
        self.assertIsNotNone(plan.audio_media)
        self.assertEqual(plan.audio_label, "原声 [zh]")

    def test_variant_without_an_audio_group_stays_silent(self):
        with HttpSession() as session:
            plan = make_plan(
                f"{self.base}/master.m3u8", Options(out_dir=self.tmp, show="p2", quality=360), session
            )
        self.assertIsNone(plan.audio_url)
        self.assertIsNone(plan.audio_media)

    def test_second_run_is_skipped_and_third_resumes_from_segments(self):
        options = Options(out_dir=self.tmp, show="resume", container="ts", remux_video=False, quiet=True)
        first = download(f"{self.base}/high/index.m3u8", options)
        self.assertTrue(os.path.exists(first.output_path))

        again = download(f"{self.base}/high/index.m3u8", options)
        self.assertTrue(again.skipped)

        forced = download(
            f"{self.base}/high/index.m3u8",
            Options(out_dir=self.tmp, show="resume", container="ts", remux_video=False,
                    quiet=True, overwrite=True, keep_segments=True),
        )
        self.assertFalse(forced.skipped)
        with open(forced.output_path, "rb") as fh:
            self.assertEqual(fh.read(), self.expected_plain)

    def test_subtitles_are_saved_next_to_the_video(self):
        options = Options(out_dir=self.tmp, show="subs", quality=360, container="ts",
                          remux_video=False, quiet=True, subtitle_langs=["zh"])
        result = download(f"{self.base}/master.m3u8", options)
        vtt_paths = [p for p in result.subtitle_paths if p.endswith(".zh.vtt")]
        self.assertEqual(len(vtt_paths), 1, result.subtitle_paths)
        with open(vtt_paths[0], "rb") as fh:
            self.assertIn("第一集开始".encode(), fh.read())

    def test_dry_run_performs_no_media_transfer(self):
        _Handler.hits.clear()
        options = Options(out_dir=self.tmp, show="dry", quality=1080, dry_run=True, quiet=True)
        result = download(f"{self.base}/master.m3u8", options)
        self.assertTrue(result.dry_run)
        self.assertFalse(os.path.exists(result.output_path))
        self.assertFalse(any("/high/seg-" in hit for hit in _Handler.hits))

    def test_drm_stream_is_refused(self):
        _Handler.routes["/drm.m3u8"] = ("application/vnd.apple.mpegurl", _drm_playlist().encode())
        with HttpSession() as session:
            extractor = get_extractor(f"{self.base}/drm.m3u8", session)
            with self.assertRaises(ExtractorError) as ctx:
                extractor.resolve(f"{self.base}/drm.m3u8")
        self.assertIn("DRM", str(ctx.exception))

    def test_unknown_url_has_no_extractor(self):
        with HttpSession() as session:
            with self.assertRaises(ExtractorError):
                get_extractor("ftp://example.com/movie", session)

    def test_checksum_is_stable_across_runs(self):
        options = Options(out_dir=self.tmp, show="hash", quality=1080, container="ts",
                          remux_video=False, quiet=True)
        first = download(f"{self.base}/master.m3u8", options)
        digest = _sha256(first.output_path)
        second = download(
            f"{self.base}/master.m3u8",
            Options(out_dir=self.tmp, show="hash2", quality=1080, container="ts",
                    remux_video=False, quiet=True),
        )
        self.assertEqual(_sha256(second.output_path), digest)


def _sha256(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


if __name__ == "__main__":
    unittest.main()
