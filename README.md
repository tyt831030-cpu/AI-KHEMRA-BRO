# AI KHEMRA BRO v6.3 — Unlocked Fix

## ការកែសំខាន់
- ដោះ Customer Access Code / Login Lock ចេញ។
- កម្មវិធីអាចបើកចូលផ្ទាល់បាន។
- Gemini API Key ត្រូវការតែពេលប្រើ AI បកប្រែប៉ុណ្ណោះ។
- API Key អាចបញ្ចូលក្នុងប៊ូតុង ☰ ហើយរក្សាទុកបាន។
- SRT ថ្មីប្រើតែ `[M]`, `[F]`, `[M_THINK]`, `[F_THINK]`។
- កំណត់ Gemini model លំនាំដើមជា `gemini-flash-latest` ដើម្បីកាត់បន្ថយកំហុស model 404។

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```

Railway/Nixpacks ត្រូវមាន FFmpeg តាម `packages.txt`។

## v7.2 scanned fixes
- Railway environment variables are read before Streamlit secrets.
- No hard-coded admin password; set `ADMIN_PASSWORD` in Railway.
- Failed Gemini translation never copies Chinese Source SRT into the Khmer editor.
- Final Khmer and MP3 validation rejects Chinese/non-Khmer cues.
- THINK voice settings remain distinct during Edge-TTS retries.
- One active device/browser session is enforced per Access Code.
- SQLite database and user workspaces use `DATA_DIR` (set `/data` on Railway).
- Duplicate `video_to_srt` implementation removed.

Railway variables required: `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `COOKIE_SECRET`, `LICENSE_PEPPER`, `DATA_DIR=/data`.
Mount a Railway Volume at `/data`.
