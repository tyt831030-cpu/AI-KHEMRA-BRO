# AI KHEMRA BRO v6.3

## New professional subtitle and dubbing rules

Generated Khmer SRT now uses only four tags:

- `[M]` male audible dialogue
- `[F]` female audible dialogue
- `[M_THINK]` unheard male inner thought
- `[F_THINK]` unheard female inner thought

Translation is instructed to use natural everyday spoken Khmer, actor-appropriate pronouns, emotional depth, concise subtitle lines, unchanged cue IDs/timestamps, and SRT-ready output.

Legacy labels remain readable during MP3 generation, but every newly generated SRT is normalized to the four-tag standard.

Deploy by replacing `app.py`, `requirements.txt`, and `packages.txt`, then redeploying the service.
