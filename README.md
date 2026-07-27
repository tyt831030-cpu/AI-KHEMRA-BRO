# AI KHEMRA BRO v5.4 — Khmer SRT Fixed

Replace the old `app.py`, `requirements.txt`, and `packages.txt`, then redeploy.

## Main fix
- Extracts 16 kHz audio with FFmpeg.
- Creates word timestamps with Faster-Whisper.
- Sends only subtitle text to Gemini, not the whole video.
- Uses larger translation batches to reduce API requests and 429 errors.
- Tries Gemini 2.5 Flash-Lite, then Gemini 2.5 Flash.
- Preserves Whisper timestamps and returns editable Khmer SRT.

A 429 error still means the Google project has no available quota. The app can reduce requests and rotate saved keys/models, but cannot create quota.
