# AI KHEMRA BRO — Clean Multi-User Release

## Main workflow
1. Upload Chinese video.
2. Faster-Whisper extracts speech and authoritative timestamps.
3. Gemini translates only the dialogue and assigns speaker roles.
4. Khmer SRT fills the editor automatically.
5. Edit/analyze SRT.
6. Edge TTS creates a synchronized Khmer MP3.
7. Download SRT and MP3.

## API menu
- Tap the black **☰** button at the top-left.
- Paste the user's own Gemini API key.
- Tap **រក្សាទុក**.
- Each phone/browser has its own session, API key, upload, SRT and MP3.

## Deploy on Streamlit Community Cloud
Upload these files to the repository root:
- `app.py`
- `requirements.txt`
- `packages.txt`
- `.streamlit/secrets.toml.example`

In Streamlit Cloud → App settings → Secrets, add:

```toml
COOKIE_SECRET = "a-long-random-private-secret"
```

Do not commit the real secret or any Gemini API key to GitHub.

## Notes
- The first run may take longer while Faster-Whisper downloads its model.
- Large videos and many simultaneous users require stronger paid hosting.
- Automatic speaker age/gender/thought detection is AI-assisted and may still need human review.


## Updated working release
- The ☰ API menu is clearly visible in white on black.
- Multiple API keys are supported, one per line.
- Quota or invalid-key failures automatically try the next key.
- The main video workflow uses fewer Gemini calls to conserve free-tier quota.
- Google raw JSON errors are replaced by short Khmer explanations.
- A 429 error cannot be bypassed by code; wait for quota reset or use a key from another Google Cloud project.
