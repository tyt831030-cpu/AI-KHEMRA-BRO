# AI KHEMRA BRO v7.0 — Character & Audio Lock

## New features

- Character Identity Lock for stable speaker labels across nearby cues.
- Clear age/voice groups: BOY, GIRL, M_YOUNG, F_YOUNG, M_ADULT, F_ADULT, M_OLD, F_OLD.
- Separate inner-thought and narrator tags.
- Stronger natural spoken Khmer translation rules.
- Crowd-scene speaker rules to reduce label confusion and duplicated dialogue.
- Subtitle quality checker for Chinese leakage, invalid timing, overlaps, invalid tags, and lines likely to be cut.
- Smoother MP3 processing with softer fades, smaller protected gaps, improved loudness stability, and a higher safe tempo ceiling to reduce hard-cut endings.

## Install

1. Rename `AI_KHEMRA_BRO_v7.0_CHARACTER_AUDIO_LOCK.py` to `app.py`.
2. Replace the old `app.py`, `requirements.txt`, `packages.txt`, and README in the hosting project.
3. Keep your existing Streamlit Secrets/API keys unchanged.
4. Redeploy or restart the service.

## Start command

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port $PORT
```
