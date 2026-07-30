# AI KHEMRA BRO v7.0 Professional

Mobile-first Streamlit application for Chinese-video transcription, natural Khmer subtitle translation, and synchronized Khmer MP3 dubbing.

## v7.0 production foundation

- Private per-customer/per-session workspaces under `DATA_DIR/workspaces`
- Persistent SQLite job registry with queued/processing/completed/failed states
- One active heavy job per customer by default
- Automatic cleanup of old private workspaces
- Strict Khmer-only SRT validation before download/dubbing
- Source-language SRT is kept separate when Gemini translation fails
- Chinese text is never inserted into the Khmer editor as a fallback
- Stronger audible separation between normal speech and inner-thought voices
- Persistent output copies: `source.srt`, `khmer.srt`, and `khmer_dubbed.mp3`
- Railway Volume support through `DATA_DIR=/data`

## Railway variables

Set these variables before public release:

- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `COOKIE_SECRET` (long random value)
- `LICENSE_PEPPER` (long random value)
- `DATA_DIR=/data`
- `MAX_ACTIVE_JOBS_PER_USER=1`
- `WORKSPACE_RETENTION_HOURS=48`

Mount a Railway Volume at `/data`.

## Start

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port ${PORT:-8501}
```

## Important capacity note

This release isolates user files and records jobs safely. For hundreds of simultaneous long video jobs, deploy separate queue/worker services and object storage before opening unrestricted public access.
