# AI KHEMRA BRO v9.0

## Main fix

- The app no longer places Chinese/Source SRT inside the Khmer SRT editor when Gemini translation fails.
- Source SRT is saved separately and can be downloaded with **Download Source SRT**.
- MP3 generation is locked until every subtitle cue contains valid Khmer-only dialogue.
- Mixed Latin, Chinese, or Thai dialogue is rejected before Edge TTS runs.
- Gemini model choices were cleaned to supported fallback names: `gemini-2.5-flash-lite`, `gemini-2.5-flash`, and `gemini-flash-latest`.
- Keeps Whisper timestamps, API-key rotation, encrypted saved keys, licensing, mobile UI, and FFmpeg audio workflow.

## Repository files

Upload these four files to the repository root:

- `app.py`
- `requirements.txt`
- `packages.txt`
- `README.md`

Then reboot/redeploy the Streamlit or Railway service.

## Required server secret

Keep your existing owner/admin and encryption secrets. Each customer enters their own Gemini API key in the app Settings menu.

## Correct workflow

1. Upload video.
2. Press **Generate Khmer SRT**.
3. When Gemini succeeds, valid Khmer SRT appears in the editor.
4. Edit the Khmer text if needed.
5. Press **Generate Dubbed Audio (MP3)**.

When translation fails, the app shows a warning and offers the Source SRT separately. It does not pretend the Chinese transcript is Khmer.
