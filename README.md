# AI KHEMRA BRO v6.4.2 AUDITED

## Railway deployment
1. Upload every file in this folder to the root of one GitHub repository.
2. Create a Railway service from that repository. Railway will detect `Dockerfile`.
3. Add a Railway Volume mounted at `/data` so customer codes and saved API keys survive redeploys.
4. Add Variables: `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `COOKIE_SECRET`, `LICENSE_PEPPER`, and `DATA_DIR=/data`.
5. Generate a public domain and deploy.

## Required variables
- `ADMIN_USERNAME=KHEMRA`
- `ADMIN_PASSWORD=<your private owner password>`
- `COOKIE_SECRET=<random string at least 32 characters>`
- `LICENSE_PEPPER=<different random string at least 32 characters>`
- `DATA_DIR=/data`

Pipeline: MP4 upload → FFmpeg → Faster-Whisper → Gemini Khmer SRT → SRT editor → Edge-TTS → FFmpeg MP3.

Generated subtitles use only `[M]`, `[F]`, `[M_THINK]`, and `[F_THINK]`.

## Audit fixes in v6.4.2
- Corrected JSON code-fence parsing.
- Corrected URL cleanup in user-facing AI errors.
- Allowed the configured six Gemini retry attempts instead of silently limiting them to four.
- Corrected underscore handling and length consistency for manual Access Codes.
- Normalized old SRT tags to the four current output tags.
- Preferred current GA Gemini Flash models while retaining active fallbacks.
- Added Streamlit upload/message limits and a Docker health check.


## v6.4.2
- Added the six strict Khmer spoken-dialogue and four-tag dubbing rules directly to the Gemini translation prompt.
