# AI KHEMRA BRO v6.0

## Main update
- Owner manually creates every Access Code.
- No automatic Access Code generation.
- One valid code can log in from iPhone, Android, tablet, or browser.
- No device binding and no single-device lock.
- Each browser session has a private temporary workspace for Video, SRT, WAV, and MP3.
- Existing Upload → Whisper → Khmer SRT → MP3 workflow is preserved.

## Deploy
Upload these files to the existing project and replace the old files:
- app.py
- requirements.txt
- packages.txt

Then redeploy/restart the service.

## Persistent storage note
For production, mount a persistent volume for `licenses.db`; otherwise redeploying on an ephemeral host can erase customer codes.
