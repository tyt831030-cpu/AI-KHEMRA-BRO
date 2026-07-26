# AI KHEMRA BRO — Version 2.0

This package upgrades the existing application without redesigning its UI.

## Version 2.0 improvements

- Smarter Gemini translation with recent-dialogue continuity between batches.
- More consistent character gender, age, narrator, and inner-thought tags.
- Automatic retry for temporary Gemini 429/503/network failures.
- Repair pass now catches missing Chinese and clearly overlong dubbing lines.
- Existing mobile UI, upload, SRT editor, MP3 generation, downloads, owner panel, and customer licensing are preserved.
- Customer access codes remain reusable across phones and browsers while active and unexpired; no permanent device lock is applied.
- Each Streamlit browser session keeps a separate temporary project workspace.

## Deploy

Upload these four files to the root of the existing GitHub repository, replacing the old files:

- `app.py`
- `requirements.txt`
- `packages.txt`
- `README.md`

Keep API keys and passwords only in Streamlit Secrets. Do not commit them to GitHub.

## Required Streamlit Secrets

Keep the same secrets already used by your deployment. At minimum, configure the Gemini/API and owner/security values expected by `app.py`.


## Version 3.0 audio changes
- Locks every generated voice to the original SRT start timestamp.
- Prevents generated speakers from overlapping each other.
- Fits long lines into the available subtitle slot with controlled speed.
- Reduces breathy/airy high frequencies.
- Uses gentler per-clip processing and one final loudness master.
