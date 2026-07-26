# AI KHEMRA BRO

This build keeps the existing application UI and workflow and fixes the security gate so the site can start immediately.

## Owner login

- Username: `KHEMRA`
- Bootstrap password: `0719067125`
- Open owner login by pressing the small `✦` button five times.

For production, override the bootstrap credentials in Streamlit Community Cloud:

```toml
ADMIN_USERNAME = "KHEMRA"
ADMIN_PASSWORD = "YOUR_PRIVATE_PASSWORD"
LICENSE_PEPPER = "LONG_RANDOM_SECRET"
COOKIE_SECRET = "LONG_RANDOM_SECRET"
```

## Files

- `app.py`
- `requirements.txt`
- `packages.txt`
- `README.md`

## Workflow

Upload Video → Translate → Edit SRT → Generate Khmer MP3 → Download
