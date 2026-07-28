# AI KHEMRA BRO v7.3 — Khmer-Only + Faster Processing

Use exactly four files in the GitHub repository root:

- app.py
- requirements.txt
- packages.txt
- README.md

## Fixed

- Rejects Thai subtitles completely.
- Rejects Chinese, Vietnamese, English, and Latin-letter dialogue.
- Requires real Cambodian Khmer Unicode before SRT can be generated.
- Automatically retries only the incorrect subtitle lines.
- Prevents wrong-language text from being placed in the final SRT.
- Reduces Whisper CPU processing time by using beam_size=5 and best_of=3.
- Keeps FFmpeg and clear-audio fixes from v7.2.

## Install

Replace the old four files in GitHub, then:

Streamlit → Manage app → Reboot app

After reboot, upload the video again and press Generate Khmer SRT.

## Version 7.6 update
- Gemini structured JSON subtitle output
- 10-line translation chunks with 1:1 ID preservation
- automatic API-key and Gemini model fallback
- targeted retry for missing subtitle lines
- optional deep-translator fallback when Gemini quota is exhausted
- Khmer-only validation; Chinese source text is never copied into final Khmer SRT
- speaker-tag voice profiles and updated MP3 cleanup filter
