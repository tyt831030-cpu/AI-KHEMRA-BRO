AI KHEMRA BRO — Version 7.7

Supported SRT voice tags

The application now outputs and uses only these four labels:

• [M] — male dialogue
• [F] — female dialogue
• [M_THINK] — male inner thought
• [F_THINK] — female inner thought

Old labels are accepted only when opening an older SRT project. They are automatically converted to one of the four supported labels before dubbing.

Main fixes

• Removed the unsupported Gemini JSON Schema field additionalProperties that caused 400 INVALID_ARGUMENT.
• Restricted Gemini prompts and schema output to four tags only.
• Added Khmer validation so Chinese or Latin dialogue cannot silently pass into the final Khmer SRT.
• Google Translate fallback now produces [M] when Gemini is unavailable; it never copies the original Chinese line into the Khmer SRT.
• Edge TTS now maps every accepted cue to one of the four voice profiles before generating audio.
• Text-to-Speech and SRT-to-Speech menus now show only the four supported labels.

Deployment files

Use:

• app.py
• requirements.txt
• packages.txt

The existing dependency lists remain compatible.
