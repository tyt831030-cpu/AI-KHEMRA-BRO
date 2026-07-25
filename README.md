# AI KHEMRA BRO — Low RAM Video Processing

- Streams the uploaded file to disk without an extra full Python byte copy.
- Creates a temporary 480p / 12fps / low-bitrate proxy for processing.
- Extracts mono 16 kHz FLAC instead of a large PCM WAV.
- Uses the smaller proxy for Gemini context upload.
- Temporary proxy/audio files are removed automatically.
