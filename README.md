# AI KHEMRA BRO — Version 7\.4\.1 Hotfix

This hotfix fixes the red\-screen crash caused by the missing Python `json` import\.

## Files

- `app.py` — corrected application
- `requirements.txt` — Python dependencies
- `packages.txt` — FFmpeg and GNU OpenMP runtime

## Streamlit Cloud

1. Replace the old files with these files\.
2. Reboot the app\.
3. If deployment still fails during Faster\-Whisper installation, delete and redeploy the app using Python 3\.11 in Advanced settings\.

## Required secrets

Configure your Gemini API key and administrator secrets in Streamlit Secrets as needed\.
