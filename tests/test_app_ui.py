import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


class DownloadOnlyUiTests(unittest.TestCase):
    def test_hls_loopback_url_is_rejected_in_the_ui(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(timeout=30)
        app.text_input[0].set_value("http://127.0.0.1:8502/test.m3u8")
        app.text_input[1].set_value("Smoke")
        app.checkbox[0].check()
        app.button[0].click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertTrue(any("private/local network" in item.value for item in app.error))

    def test_download_page_has_no_login_or_translation_controls(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(timeout=30)
        self.assertFalse(app.exception, "Streamlit app raised an exception")
        self.assertEqual([item.value for item in app.title], ["ទាញយកវីដេអូរឿង"])
        self.assertEqual(len(app.text_input), 3)
        self.assertEqual(len(app.number_input), 2)
        self.assertEqual(len(app.selectbox), 1)
        self.assertEqual(len(app.checkbox), 1)
        self.assertEqual(len(app.button), 1)
        widgets = [*app.text_input, *app.number_input, *app.selectbox, *app.checkbox, *app.button]
        labels = [item.label for item in widgets]
        joined = " ".join(labels).lower()
        self.assertNotIn("access code", joined)
        self.assertNotIn("password", joined)
        self.assertNotIn("translate", joined)
        self.assertNotIn("បកប្រែ", joined)


if __name__ == "__main__":
    unittest.main()
