AI KHEMRA BRO — Version 7.8

Core workflow

Upload video → Whisper timestamps → Khmer translation → editable Khmer SRT → Edge TTS MP3.

Voice labels

Only these four labels are accepted:

• [M] male dialogue
• [F] female dialogue
• [M_THINK] male inner thought
• [F_THINK] female inner thought

Old labels are normalized internally to one of the four labels. Edge TTS removes labels before synthesis.

Version 7.8 fixes

• Removed Gemini response_schema to prevent 400 INVALID_ARGUMENT schema errors.
• On Gemini 429 quota errors, missing batches automatically use Google Translate fallback.
• Chinese source text is never inserted into the Khmer editor after translation failure.
• MP3 generation refuses SRT containing Chinese or Thai characters.
• Raw Gemini exception payloads are replaced with short Khmer messages.
• Uses only stable fallback model names configured in the application.

Railway

The repository root should contain:

• app.py
• requirements.txt
• packages.txt
• README.md

Start command:

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port $PORT
```
