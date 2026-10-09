"""Unit tests for the HLS playlist parser and variant selection."""
from __future__ import annotations

import unittest

from cddl.hls import (
    HlsError,
    MasterPlaylist,
    MediaPlaylist,
    UnsupportedEncryption,
    parse_attribute_list,
    parse_playlist,
    select_variant,
)

MASTER = """#EXTM3U
#EXT-X-VERSION:6
#EXT-X-INDEPENDENT-SEGMENTS
#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="中文",LANGUAGE="zh",DEFAULT=YES,URI="subs/zh.m3u8"
#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="English",LANGUAGE="en",URI="subs/en.m3u8"
#EXT-X-STREAM-INF:BANDWIDTH=800000,AVERAGE-BANDWIDTH=700000,RESOLUTION=640x360,CODECS="avc1.4d401e,mp4a.40.2"
low/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=2400000,AVERAGE-BANDWIDTH=2200000,RESOLUTION=1280x720,CODECS="avc1.4d401f,mp4a.40.2",SUBTITLES="subs"
mid/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=6000000,RESOLUTION=1920x1080,FRAME-RATE=25.000,CODECS="avc1.640028,mp4a.40.2",SUBTITLES="subs"
https://cdn.example.com/high/index.m3u8?token=abc
"""

MEDIA = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:10
#EXT-X-MEDIA-SEQUENCE:0
#EXT-X-PLAYLIST-TYPE:VOD
#EXT-X-KEY:METHOD=AES-128,URI="keys/k1.bin",IV=0x00000000000000000000000000000001
#EXTINF:9.009,片头
seg-0.ts
#EXTINF:9.009,
seg-1.ts
#EXT-X-DISCONTINUITY
#EXT-X-KEY:METHOD=AES-128,URI="keys/k2.bin"
#EXTINF:8.000,
https://other.example.com/seg-2.ts
#EXT-X-ENDLIST
"""


class AttributeListTests(unittest.TestCase):
    def test_quoted_and_bare_values(self):
        attrs = parse_attribute_list('METHOD=AES-128,URI="https://a/b.bin",IV=0x01,DEFAULT=YES')
        self.assertEqual(attrs["METHOD"], "AES-128")
        self.assertEqual(attrs["URI"], "https://a/b.bin")
        self.assertEqual(attrs["IV"], "0x01")


class MasterPlaylistTests(unittest.TestCase):
    def setUp(self):
        self.master = parse_playlist(MASTER, "https://cdn.example.com/vod/master.m3u8")

    def test_is_master(self):
        self.assertIsInstance(self.master, MasterPlaylist)

    def test_variants_are_absolutised_and_parsed(self):
        self.assertEqual(len(self.master.variants), 3)
        low, mid, high = self.master.variants
        self.assertEqual(low.uri, "https://cdn.example.com/vod/low/index.m3u8")
        self.assertEqual(low.resolution, (640, 360))
        self.assertEqual(low.average_bandwidth, 700_000)
        self.assertEqual(mid.height, 720)
        self.assertEqual(mid.subtitle_group, "subs")
        self.assertEqual(high.frame_rate, 25.0)
        self.assertTrue(high.uri.endswith("?token=abc"))
        self.assertEqual(high.effective_bandwidth, 6_000_000)

    def test_subtitle_renditions(self):
        subs = self.master.subtitle_renditions()
        self.assertEqual([s.language for s in subs], ["zh", "en"])
        self.assertTrue(subs[0].uri.endswith("subs/zh.m3u8"))
        self.assertTrue(subs[0].default)

    def test_select_variant_quality_choices(self):
        self.assertEqual(select_variant(self.master, "best").height, 1080)
        self.assertEqual(select_variant(self.master, "worst").height, 360)
        # 720 is exact; 1000 rounds up to the next available height
        self.assertEqual(select_variant(self.master, 720).height, 720)
        self.assertEqual(select_variant(self.master, 1000).height, 1080)
        # Above the top rendition -> best available
        self.assertEqual(select_variant(self.master, 4320).height, 1080)
        # Below the bottom -> the smallest
        self.assertEqual(select_variant(self.master, 144).height, 360)

    def test_bad_quality_selector(self):
        with self.assertRaises(ValueError):
            select_variant(self.master, "4k-ish")


class MediaPlaylistTests(unittest.TestCase):
    def setUp(self):
        self.media = parse_playlist(MEDIA, "https://cdn.example.com/vod/high/index.m3u8")

    def test_is_media_and_finished(self):
        self.assertIsInstance(self.media, MediaPlaylist)
        self.assertFalse(self.media.is_live)
        self.assertEqual(len(self.media.segments), 3)
        self.assertAlmostEqual(self.media.total_duration, 26.018, places=3)

    def test_keys_and_iv(self):
        first, second, third = self.media.segments
        self.assertEqual(first.key.method, "AES-128")
        self.assertEqual(first.key.uri, "https://cdn.example.com/vod/high/keys/k1.bin")
        self.assertEqual(first.key.iv, b"\x00" * 15 + b"\x01")
        self.assertEqual(second.key.uri, first.key.uri)
        # Third segment moved to a new key with no IV -> derived from sequence
        self.assertEqual(third.key.uri, "https://cdn.example.com/vod/high/keys/k2.bin")
        self.assertIsNone(third.key.iv)
        self.assertEqual(third.sequence, 2)
        self.assertEqual(sorted(self.media.encryption_methods), ["AES-128"])

    def test_titles_discontinuity_and_absolute_uris(self):
        first, _, third = self.media.segments
        self.assertEqual(first.title, "片头")
        self.assertEqual(first.uri, "https://cdn.example.com/vod/high/seg-0.ts")
        self.assertTrue(third.discontinuity)
        self.assertEqual(third.uri, "https://other.example.com/seg-2.ts")


class ByteRangeTests(unittest.TestCase):
    def test_byterange_chaining_and_map(self):
        text = """#EXTM3U
#EXT-X-VERSION:7
#EXT-X-TARGETDURATION:4
#EXT-X-MAP:URI="init.mp4"
#EXTINF:4.0,
#EXT-X-BYTERANGE:1200@0
media.mp4
#EXTINF:4.0,
#EXT-X-BYTERANGE:800
media.mp4
#EXT-X-ENDLIST
"""
        media = parse_playlist(text, "https://cdn.example.com/x/playlist.m3u8")
        first, second = media.segments
        self.assertEqual(first.init_section, "https://cdn.example.com/x/init.mp4")
        self.assertEqual(first.byte_range.length, 1200)
        self.assertEqual(first.byte_range.offset, 0)
        self.assertEqual(second.byte_range.length, 800)
        self.assertEqual(second.byte_range.offset, 1200)  # chained from the previous range


class ErrorTests(unittest.TestCase):
    def test_not_a_playlist(self):
        with self.assertRaises(HlsError):
            parse_playlist("<html>nope</html>", "https://x/m.m3u8")

    def test_drm_is_rejected_explicitly(self):
        drm = """#EXTM3U
#EXT-X-TARGETDURATION:4
#EXT-X-KEY:METHOD=SAMPLE-AES,URI="skd://key",KEYFORMAT="com.apple.streamingkeydelivery"
#EXTINF:4.0,
seg.ts
#EXT-X-ENDLIST
"""
        with self.assertRaises(UnsupportedEncryption) as ctx:
            parse_playlist(drm, "https://x/m.m3u8")
        self.assertIn("DRM", str(ctx.exception))

    def test_empty_media_playlist(self):
        with self.assertRaises(HlsError):
            parse_playlist("#EXTM3U\n#EXT-X-TARGETDURATION:4\n#EXT-X-ENDLIST\n", "https://x/m.m3u8")


if __name__ == "__main__":
    unittest.main()