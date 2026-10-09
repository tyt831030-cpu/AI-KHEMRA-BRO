# AI KHEMRA BRO — Episode Video Downloader

Streamlit application in Khmer: paste a public series-page URL, discover episode links exposed in server-rendered HTML, inspect episode titles and same-site thumbnails, then prepare a direct episode MP4 download or a ZIP of all supported episodes. Translation, voice generation, access-code, and login features are not included.

## Run locally

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

`ffmpeg` must be available on `PATH` (`packages.txt` configures it on Streamlit Community Cloud).

## Supported sources and limits

- Episode lists must be visible in public HTML links; episode pages must expose a direct public HLS VOD (`.m3u8`) or MP4 URL in HTML video/source tags or Open Graph metadata.
- The finder does not run page JavaScript, log in, call undocumented/private APIs, bypass paywalls, or defeat DRM. Dynamic player sites may be reported unsupported; provide a lawful public sample URL to add a source-specific supported parser.
- Standard identity AES-128 HLS is supported; DRM, SAMPLE-AES, live playlists and private-app APIs are not.
- URL redirects and DNS resolutions are rechecked to block private/loopback destinations; source inspection has a 32 MiB / 90 second budget and at most 100 episode pages.
- A single download is limited to 512 MiB or 25 minutes of network time and 350 MiB of browser output; HLS is limited to 10,000 segments and 4 hours.
- A ZIP of supported episodes shares the 512 MiB / 25 minute network budget and is limited to 350 MiB total.
- Per-job files are temporary and removed after output bytes are prepared. Streamlit holds capped output bytes in the visitor session for its download button.
- Only submit material you are legally authorized to download.

## Tests

```bash
python -m unittest discover -s tests -t . -v
```

The downloader engine in `cddl/` is MIT-licensed; see `cddl/LICENSE`.
