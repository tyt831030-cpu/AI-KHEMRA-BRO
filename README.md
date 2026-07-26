# AI KHEMRA BRO

Streamlit app with customer login and a hidden admin license dashboard.

## Included
- Customer login: name + access code
- Automatic access-code generation
- License durations: 7 days, 30 days, 365 days
- Automatic expiry checks
- Renew, block/unblock, and delete licenses
- Existing Video → Khmer SRT → MP3 features retained

## Streamlit Secrets
Add these in Streamlit Community Cloud: App settings → Secrets.

```toml
ADMIN_PASSWORD = "CHANGE_THIS_TO_YOUR_PRIVATE_PASSWORD"
COOKIE_SECRET = "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET"
```

## Admin access
Open the normal app URL and add `?admin=1` to the end.
Example: `https://your-app.streamlit.app/?admin=1`

## Important database note
The app automatically creates `licenses.db`. Local SQLite storage may reset after a Streamlit Community Cloud restart or redeploy. For permanent commercial use, migrate license records to Supabase/PostgreSQL.
