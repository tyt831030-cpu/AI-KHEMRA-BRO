"""Unit tests for filesystem-safe naming and small helpers."""
from __future__ import annotations

import unittest

from cddl.naming import episode_filename, sanitize_filename
from cddl.utils import (
    human_bytes,
    human_time,
    parse_cookie_string,
    parse_int_set,
    parse_kv_header,
)


class SanitizeTests(unittest.TestCase):
    def test_illegal_characters_replaced(self):
        self.assertEqual(sanitize_filename('a<b>c:d"e/f\\g|h?i*j'), "a_b_c_d_e_f_g_h_i_j")

    def test_cjk_is_preserved_verbatim(self):
        self.assertEqual(sanitize_filename("斗罗大陆 第1集"), "斗罗大陆 第1集")

    def test_trailing_dots_and_spaces_stripped(self):
        self.assertEqual(sanitize_filename("name.  "), "name")

    def test_reserved_windows_names(self):
        self.assertEqual(sanitize_filename("CON"), "CON_")
        # Windows treats "LPT3.txt" as the LPT3 device, so the stem is escaped.
        self.assertEqual(sanitize_filename("lpt3.txt"), "lpt3.txt_")
        self.assertEqual(sanitize_filename("剧集"), "剧集")

    def test_long_names_truncated_with_hash(self):
        name = "剧" * 200
        out = sanitize_filename(name, max_bytes=180)
        self.assertLessEqual(len(out.encode("utf-8")), 180)
        self.assertIn("~", out)
        # Deterministic for identical input
        self.assertEqual(out, sanitize_filename(name, max_bytes=180))

    def test_empty_input_falls_back(self):
        self.assertEqual(sanitize_filename("  ", fallback="untitled"), "untitled")


class EpisodeFilenameTests(unittest.TestCase):
    def test_default_template(self):
        path = episode_filename("斗罗大陆", season=1, episode=7, title="武魂觉醒")
        self.assertEqual(path, "斗罗大陆/S01E007 武魂觉醒.mp4")

    def test_custom_template(self):
        path = episode_filename("我的剧集", season=2, episode=13, template="{show}/第{episode:03d}集{title_part}.mkv")
        self.assertEqual(path, "我的剧集/第013集.mkv")

    def test_template_with_title(self):
        path = episode_filename(
            "我的剧集", season=2, episode=13, title="大结局",
            template="{show}/第{episode:03d}集{title_part}.mkv",
        )
        self.assertEqual(path, "我的剧集/第013集 大结局.mkv")

    def test_duplicate_extension_not_repeated(self):
        path = episode_filename("show", episode=1, ext=".mp4", template="{show}/ep{episode:02d}.mp4")
        self.assertEqual(path, "show/ep01.mp4")
        self.assertFalse(path.endswith(".mp4.mp4"))

    def test_show_name_sanitised(self):
        path = episode_filename("Show: The/Series", season=1, episode=1)
        self.assertEqual(path, "Show_ The_Series/S01E001.mp4")


class HelperTests(unittest.TestCase):
    def test_parse_int_set(self):
        self.assertEqual(parse_int_set("1-3,5,7-9"), [1, 2, 3, 5, 7, 8, 9])
        self.assertEqual(parse_int_set("3,1,2,1"), [3, 1, 2])

    def test_parse_kv_header(self):
        self.assertEqual(parse_kv_header("Referer: https://x/y"), ("Referer", "https://x/y"))
        with self.assertRaises(ValueError):
            parse_kv_header("nope")

    def test_parse_cookie_string(self):
        self.assertEqual(parse_cookie_string("a=1; b=2;"), {"a": "1", "b": "2"})

    def test_human_formats(self):
        self.assertEqual(human_bytes(0), "0 B")
        self.assertEqual(human_bytes(1536), "1.50 KiB")
        self.assertEqual(human_time(3725), "1h02m05s")
        self.assertEqual(human_time(65), "01m05s")
        self.assertEqual(human_time(9), "09s")


if __name__ == "__main__":
    unittest.main()
