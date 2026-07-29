# AI KHEMRA BRO v6.2

Main fix: Gemini model compatibility for Video → Whisper → Khmer SRT → MP3.

- Defaults to `gemini-3.5-flash-lite`.
- Automatic fallback to other supported Flash models.
- Keeps Chinese source transcription separate from Khmer SRT.
- MP3 generation requires valid Khmer subtitle text.

Deploy by replacing `app.py`, keeping `requirements.txt` and `packages.txt`, then redeploying the service.
