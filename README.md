# AI KHEMRA BRO — Whisper Timestamp Fix

This version keeps the existing UI and changes the processing pipeline:

1. FFmpeg extracts 16 kHz mono audio.
2. Faster-Whisper creates authoritative Chinese timestamps.
3. Gemini translates and assigns voice roles without changing timestamps.
4. Khmer SRT automatically fills the existing editor.
5. Analyze Inner Thoughts now really edits dialogue/tags while preserving timestamps.
6. Edge TTS creates the synchronized MP3.

Upload all files to the root of the existing GitHub repository and commit. Streamlit Cloud installs FFmpeg from `packages.txt`. The first run downloads the Whisper base model and can take longer.


## Short Dialogue & Voice Fix
- Stable speaker/role second pass
- THINK only for unheard inner monologue
- Short Khmer dialogue based on cue duration
- Natural-speed MP3 without aggressive time compression
