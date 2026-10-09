import subprocess
import unittest
from unittest.mock import patch

from cddl.muxer import MuxError, _run, probe_duration


class MuxTimeoutTests(unittest.TestCase):
    def test_ffmpeg_timeout_becomes_mux_error(self):
        timeout = subprocess.TimeoutExpired("ffmpeg", 2)
        with patch("cddl.muxer.subprocess.run", side_effect=timeout):
            with self.assertRaises(MuxError):
                _run(["ffmpeg", "-i", "input.ts", "output.mp4"], quiet=True, timeout=2)

    def test_ffprobe_timeout_returns_no_duration(self):
        timeout = subprocess.TimeoutExpired("ffprobe", 10)
        with patch("cddl.muxer.ffprobe_path", return_value="/usr/bin/ffprobe"):
            with patch("cddl.muxer.subprocess.run", side_effect=timeout):
                self.assertIsNone(probe_duration("input.mp4"))


if __name__ == "__main__":
    unittest.main()
