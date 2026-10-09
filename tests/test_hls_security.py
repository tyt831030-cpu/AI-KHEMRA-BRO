import unittest

from cddl.hls import MediaPlaylist, UnsupportedEncryption, parse_playlist
from cddl.extractors.generic import ProgressiveFileExtractor


class HlsEncryptionPolicyTests(unittest.TestCase):
    def test_rejects_sample_aes(self):
        text = """#EXTM3U
#EXT-X-KEY:METHOD=SAMPLE-AES,URI=\"skd://example/key\"
#EXTINF:2,
segment.ts
#EXT-X-ENDLIST
"""
        with self.assertRaises(UnsupportedEncryption):
            parse_playlist(text, "https://media.example/playlist.m3u8")

    def test_rejects_non_identity_aes_key_format(self):
        text = """#EXTM3U
#EXT-X-KEY:METHOD=AES-128,URI=\"https://media.example/key\",KEYFORMAT=\"com.apple.streamingkeydelivery\"
#EXTINF:2,
segment.ts
#EXT-X-ENDLIST
"""
        with self.assertRaises(UnsupportedEncryption):
            parse_playlist(text, "https://media.example/playlist.m3u8")

    def test_rejects_drm_advertised_by_master_session_key(self):
        text = """#EXTM3U
#EXT-X-SESSION-KEY:METHOD=SAMPLE-AES,URI=\"skd://example/key\"
#EXT-X-STREAM-INF:BANDWIDTH=1200000,RESOLUTION=1280x720
variant.m3u8
"""
        with self.assertRaises(UnsupportedEncryption):
            parse_playlist(text, "https://media.example/master.m3u8")

    def test_accepts_identity_aes128_vod(self):
        text = """#EXTM3U
#EXT-X-KEY:METHOD=AES-128,URI=\"https://media.example/key\",KEYFORMAT=\"identity\"
#EXTINF:2,
segment.ts
#EXT-X-ENDLIST
"""
        result = parse_playlist(text, "https://media.example/playlist.m3u8")
        self.assertIsInstance(result, MediaPlaylist)

    def test_mp4_signed_query_is_recognized_but_dash_is_not(self):
        self.assertTrue(ProgressiveFileExtractor.matches("https://media.example/episode.mp4?sig=123"))
        self.assertFalse(ProgressiveFileExtractor.matches("https://media.example/stream.mpd"))


if __name__ == "__main__":
    unittest.main()
