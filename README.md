# AI KHEMRA BRO — Full UI + Private Admin

This build keeps the full original UI and features from `app(28).py` and adds private customer licensing.

## Public customer flow
- Customer enters registered name and Access Code.
- Valid, active, unexpired licenses unlock the full Video → SRT → MP3 application.
- Expired, blocked, or invalid licenses are rejected automatically.

## Private owner flow
1. On the customer login screen, tap the small `✦` control at the top-right five times.
2. Enter the owner name and password.
3. Create customer codes for 7 days, 30 days, or 365 days.
4. Renew, block/unblock, or delete customer codes.

## Streamlit Secrets (recommended)
Add these in Streamlit Cloud → App settings → Secrets:

```toml
ADMIN_USERNAME = "KHEMRA"
ADMIN_PASSWORD = "YOUR_PRIVATE_PASSWORD"
COOKIE_SECRET = "A-LONG-RANDOM-PRIVATE-SECRET"
```

The file contains the requested initial fallback credentials so it can run immediately. Using Streamlit Secrets is safer because public GitHub source can be viewed.

## Install
Upload these four files to the root of the existing GitHub repository:
- `app.py`
- `requirements.txt`
- `packages.txt`
- `README.md`

Set the Streamlit main file path to `app.py`.

## Database note
`licenses.db` is created automatically. Streamlit Community Cloud local files may reset after restart/redeploy. For long-term paid use, move licenses to Supabase/PostgreSQL.
