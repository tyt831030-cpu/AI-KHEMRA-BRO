# AI KHEMRA BRO — Video Downloader

Streamlit app ជាភាសាខ្មែរ សម្រាប់ទាញយក HLS VOD ឬ MP4 ដែលអ្នកប្រើមានសិទ្ធិទាញយក។ ទំព័រមានតែ video downloader — គ្មានការបកប្រែ, voice, AI dubbing, access-code ឬ login gate។

## Run locally

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

ត្រូវមាន `ffmpeg` នៅក្នុង PATH (`packages.txt` សម្រាប់ Streamlit Community Cloud)។

## Supported sources and limits

- Direct public `.m3u8` HLS VOD and direct MP4 URLs; MP4 is the only browser output.
- Standard identity AES-128 HLS is supported; DRM, SAMPLE-AES, live playlists and private-app APIs are not.
- URL redirects and DNS resolutions are rechecked to block private/loopback destinations; external requests use bounded retries and time/byte budgets.
- Maximum network budget: 512 MiB or 25 minutes; maximum browser MP4: 350 MiB; HLS: 10,000 segments and 4 hours; maximum 2 concurrent jobs.
- Per-job files are temporary and removed after the output bytes are prepared. Streamlit keeps the capped output bytes in that visitor's session for its download button.
- Only submit video URLs and use the site for material you are legally authorized to download.

## Tests

```bash
python -m unittest discover -s tests -t . -v
```

The downloader engine in `cddl/` is MIT-licensed; see `cddl/LICENSE`.
