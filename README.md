# AI KHEMRA BRO v5.0 Production Stable

## Fixed in this build
- Navigation no longer returns to the first/home function on every Streamlit rerun.
- Saved customer login and encrypted Gemini API keys remain attached to the Access Code.
- Access Codes are not locked to one phone or browser.
- Removed the database-wide session reset that previously ran on every page refresh.
- The full interface stays visible when no Gemini API key is saved.
- Added persistent `DATA_DIR` support for Railway/Render volumes.
- Whisper defaults to the `small` model and uses tighter VAD settings to retain short Chinese speech.
- Existing SRT timestamps are kept as the source of truth for translation and dubbing.

## Required deployment settings
Set these secrets/environment variables:

- `COOKIE_SECRET`: long random secret
- `API_ENCRYPTION_KEY`: long random secret
- `LICENSE_PEPPER`: long random secret
- `ADMIN_PASSWORD`: owner password
- `DATA_DIR=/data` when a persistent volume is mounted at `/data`

Optional performance settings:

- `WHISPER_MODEL=small`
- `WHISPER_COMPUTE_TYPE=int8`
- `WHISPER_CPU_THREADS=4`

## Important production note
This package is stable for one persistent server instance. Supporting 1,000 simultaneous video-processing jobs requires external PostgreSQL/Supabase, object storage, a job queue, and multiple workers. A phone only controls the app; Whisper, translation, FFmpeg, and TTS run on the server.
