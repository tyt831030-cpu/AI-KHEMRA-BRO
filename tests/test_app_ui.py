import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


class DownloadOnlyUiTests(unittest.TestCase):
    def test_page_has_one_series_url_field_and_search_button(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(timeout=30)
        self.assertFalse(app.exception, "Streamlit app raised an exception")
        self.assertEqual([item.value for item in app.title], ["ស្វែងរក និងទាញយកភាគរឿង"])
        self.assertEqual(len(app.text_input), 1)
        self.assertEqual(app.text_input[0].label, "តំណរឿង")
        self.assertEqual(len(app.number_input), 0)
        self.assertEqual(len(app.selectbox), 0)
        self.assertEqual(len(app.checkbox), 0)
        self.assertEqual(len(app.button), 1)
        self.assertEqual(app.button[0].label, "ស្វែងរកភាគទាំងអស់")

    def test_page_has_no_access_code_password_or_translation_controls(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(timeout=30)
        self.assertFalse(app.exception, "Streamlit app raised an exception")
        widgets = [*app.text_input, *app.button]
        joined = " ".join(item.label for item in widgets).lower()
        self.assertNotIn("access code", joined)
        self.assertNotIn("password", joined)
        self.assertNotIn("translate", joined)
        self.assertNotIn("បកប្រែ", joined)
        self.assertIn("ស្វែងរកភាគទាំងអស់", joined)


if __name__ == "__main__":
    unittest.main()
