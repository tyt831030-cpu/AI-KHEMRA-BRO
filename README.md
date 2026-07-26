# AI KHEMRA BRO v4.4 Stable Multi-User

## What was fixed
- Fixed missing `json` import used by saved-login cookies.
- Removed the database-wide session reset that ran on every Streamlit rerun.
- Added a persistent `DATA_DIR` option for Railway/Render mounted volumes.
- Added safer SQLite WAL settings and cross-thread access support.
- Added a clear database startup error instead of a blank iPhone screen.
- Added iPhone/Safari viewport and overscroll safeguards.
- Access Codes are not tied to one phone. A valid active code can be used on another phone.
- API keys remain encrypted and attached to the Access Code in the account database.

## Deploy files
Upload these files to the same repository root:
- `app.py`
- `requirements.txt`
- `packages.txt`

## Recommended secrets
```toml
COOKIE_SECRET = "use-a-long-random-secret"
LICENSE_PEPPER = "use-another-long-random-secret"
ADMIN_USERNAME = "KHEMRA"
ADMIN_PASSWORD = "change-this-password"
```

## Persistent database
For Railway/Render, mount a persistent volume and set:

```bash
DATA_DIR=/data
```

Without a persistent volume, a local SQLite database can disappear after a redeploy.

## Capacity note
This release is a stable multi-user baseline, but 1,000 simultaneous video jobs cannot be guaranteed by one Streamlit instance. Whisper, FFmpeg and TTS run on the server, not on each user's phone. For heavy concurrency, use multiple workers, a queue, object storage, and PostgreSQL/Supabase.
