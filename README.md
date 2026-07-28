# AI KHEMRA BRO v6.4 — 4 Voice Air-Clean Fix

This build keeps the existing UI and workflow, and changes only audio/tag logic.

## Fixed
- Uses only `[M]`, `[F]`, `[M_THINK]`, `[F_THINK]`.
- Inner-thought tags are used only when clearly proven; uncertain lines remain normal dialogue.
- Normal voices are softer and less dry.
- Inner-thought voices are slower, quieter, warmer, and subtly separated from normal dialogue.
- Strong high-frequency air/hiss is reduced.
- Compression and loudness processing are gentler to avoid amplifying breath noise.
- Mono MP3 output improves speech stability on phones.
- Timing, UI, login, license and API settings remain unchanged.

## Deploy
Replace the four files in the GitHub repository, then reboot/redeploy the Streamlit app.
