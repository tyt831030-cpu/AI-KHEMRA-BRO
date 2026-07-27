# AI KHEMRA BRO v7.2 — Streamlit Build & Clear Audio Fix

Use exactly these four files in the root of the GitHub repository:

- app.py
- requirements.txt
- packages.txt
- README.md

## Fixed

1. Fixed:
   `run_ffmpeg() got an unexpected keyword argument 'capture_output'`

2. The video flow can now continue:
   Upload → FFmpeg audio extraction → Whisper → Khmer SRT → MP3.

3. Improved Khmer voice clarity:
   - less low-frequency heaviness
   - clearer consonants
   - preserved high-frequency detail
   - gentler compression
   - 48 kHz stereo, 192 kbps MP3
   - final loudness target: -16 LUFS, true peak -1.5 dB

## Deploy

Replace the four old files in GitHub, then open Streamlit:

Manage app → Reboot app

Do not upload Dockerfile to Streamlit Community Cloud.
