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


## Latest update
- Preserves the existing application UI and workflow.
- Improves the translation prompt for natural, emotional spoken Khmer dubbing.
- Removes device and single-session locking.
- A valid access code can be reused after logout, browser close, phone restart, and on different phones.
- Customer name is optional at login; the valid access code is the credential.


## Session isolation update
- Separate private workspace per browser session.
- Upload/SRT/MP3/Clear Project do not affect other users.
- Access codes remain reusable on all phones and browsers.
- Fixed MP3 filename StreamlitAPIException.
- SQLite WAL enabled for safer concurrent access.
