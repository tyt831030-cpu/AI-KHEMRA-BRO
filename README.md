# AI KHEMRA BRO v6.2

Main fix: Gemini model compatibility for Video → Whisper → Khmer SRT → MP3.

- Defaults to `gemini-3.5-flash-lite`.
- Automatic fallback to other supported Flash models.
- Keeps Chinese source transcription separate from Khmer SRT.
- MP3 generation requires valid Khmer subtitle text.

Deploy by replacing `app.py`, keeping `requirements.txt` and `packages.txt`, then redeploying the service.


## 6.3 Four-Voice Smooth Audio Fix
- Uses only [M], [F], [M_THINK], [F_THINK].
- Legacy tags are automatically mapped to the four supported tags.
- Softer neutral pitch and gentler EQ/compression.
- Longer fades and protected cue gaps reduce clicks and abrupt cuts.
- Translation prompt enforces natural spoken Khmer and locked timestamps.

## Version 6.5 Voice Lock Fix
- Locks the four supported tags: M, F, M_THINK, F_THINK.
- Corrects obvious one-line gender tag flicker between matching neighboring speakers.
- Keeps THINK as a mode of the same male/female character.
- Makes inner-thought voices slower, lighter, and quieter than normal dialogue.
- Reduces airy hiss and uneven loudness.
- Uses mono 44.1 kHz output for steadier mobile playback.
