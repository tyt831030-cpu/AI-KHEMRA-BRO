# AI KHEMRA BRO — Version 7\.9

## Files

- `app.py` — Main Streamlit application
- `requirements.txt` — Python dependencies
- `packages.txt` — System dependency \(`ffmpeg`\)
- `README.md` — Deployment notes

## Fixes in Version 7\.9

1. Added `import json` to the main import section\.
2. Removed the duplicate local `import json` from `parse_json_array()`\.
3. Confirmed `initialize_license_database()` runs after its function definition\.
4. Confirmed the admin “សម្អាត Session ចាស់” button calls `st.rerun()` correctly\.
5. Kept the four supported audio tags only:
  - `[M]`
  - `[F]`
  - `[M_THINK]`
  - `[F_THINK]`

## Railway start command

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port $PORT
```
