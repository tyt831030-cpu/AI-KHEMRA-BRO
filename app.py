"""AI KHEMRA BRO — public-page episode finder and video-only downloader."""
from __future__ import annotations

import hashlib
from typing import Any

import streamlit as st

from cddl.utils import human_bytes, human_time
from episode_archive import build_episode_archive
from episode_discovery import DiscoveryError, discover_episodes
from safe_downloader import (
    download_video,
    public_error_message,
)

st.set_page_config(
    page_title="AI KHEMRA BRO · Episode Downloader",
    page_icon="▶️",
    layout="centered",
    initial_sidebar_state="collapsed",
)
st.markdown('<meta name="robots" content="noindex, nofollow, noarchive">', unsafe_allow_html=True)

st.markdown(
    """
    <style>
    :root {
      color-scheme: dark;
      --ink:#f7f8fc; --muted:#a7b1c1; --navy:#070d16;
      --panel:#0d1521; --line:#263648; --cyan:#28d7e7;
      --gold:#ffc928; --orange:#ff812b;
    }
    html,body,[class*="css"],[data-testid="stAppViewContainer"] {
      font-family:system-ui,"Noto Sans Khmer","Khmer Sangam MN",sans-serif;
      color:var(--ink);
    }
    .stApp {
      background:radial-gradient(ellipse at 8% 0%,#13354470 0,transparent 38%),
        radial-gradient(ellipse at 96% 2%,#17314c78 0,transparent 35%),var(--navy);
      color:var(--ink);
    }
    .block-container {max-width:820px;padding-top:1.25rem;padding-bottom:3rem;}
    header[data-testid="stHeader"] {background:#070d16;}
    .brand-panel {
      display:flex;align-items:center;gap:16px;padding:19px 21px;
      border:1px solid var(--cyan);border-radius:22px;
      background:linear-gradient(135deg,#101925,#0a111b);
      box-shadow:0 0 24px #28d7e71d,inset 0 0 18px #28d7e709;margin-bottom:1.4rem;
    }
    .brand-mark {
      display:grid;place-items:center;flex:0 0 52px;height:52px;border-radius:17px;
      color:white;font-size:24px;font-weight:800;
      background:linear-gradient(135deg,var(--orange),var(--gold) 54%,var(--cyan));
      box-shadow:0 7px 20px #ff812b36;
    }
    .brand-name {color:#fff;font-size:1.2rem;font-weight:850;letter-spacing:.035em;}
    .brand-sub {color:var(--cyan);font-size:.72rem;font-weight:750;letter-spacing:.13em;margin-top:4px;}
    h1,h2,h3 {color:#fff !important;letter-spacing:-.025em;}
    .intro {color:var(--muted);line-height:1.8;margin:.25rem 0 1.1rem;}
    .eyebrow {color:var(--gold);font-size:.8rem;font-weight:800;letter-spacing:.08em;margin-bottom:.6rem;}
    [data-testid="stForm"],div[data-testid="stVerticalBlockBorderWrapper"] {
      border-color:var(--line);border-radius:18px;background:#0b131e;
    }
    [data-testid="stTextInput"] input {
      background:#f6f7fa !important;color:#131722 !important;border-radius:11px !important;
    }
    [data-testid="stTextInput"] label {color:var(--ink) !important;}
    button[kind="primary"],[data-testid="stFormSubmitButton"] button,.stDownloadButton button {
      border:0 !important;border-radius:12px;min-height:46px;font-weight:800;color:#11151c !important;
      background:linear-gradient(100deg,var(--gold),#ffaf18) !important;box-shadow:0 7px 20px #ffc92824;
    }
    button[kind="primary"]:hover,[data-testid="stFormSubmitButton"] button:hover,.stDownloadButton button:hover {color:#11151c !important;filter:brightness(1.05);border:0 !important;}
    div[data-testid="stMetric"] {background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:13px;}
    div[data-testid="stMetricLabel"] {color:var(--muted);}
    [data-testid="stAlert"] {border-radius:12px;}
    hr {border-color:#263648;}
    footer {visibility:hidden;}
    @media(max-width:600px) {
      .block-container {padding-left:.8rem;padding-right:.8rem;}
      .brand-panel {padding:16px 14px;border-radius:18px;}
      .brand-mark {flex-basis:46px;height:46px;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="brand-panel"><div class="brand-mark">▶</div>'
    '<div><div class="brand-name">AI KHEMRA BRO</div>'
    '<div class="brand-sub">EPISODE VIDEO DOWNLOADER</div></div></div>',
    unsafe_allow_html=True,
)
st.title("ស្វែងរក និងទាញយកភាគរឿង")
st.markdown(
    '<p class="intro">បិទភ្ជាប់តំណទំព័រដែលបង្ហាញបញ្ជីភាគជាសាធារណៈ ឬតំណ HLS (.m3u8) / MP4 ផ្ទាល់។ '
    'បន្ទាប់ពីស្វែងរក ចុច “រៀបចំ MP4 ភាគនេះ” រួចចុច “ទាញយកឯកសារ MP4” ដើម្បីរក្សាទុក។ '
    'អាចរៀបចំ ZIP បាន ប្រសិនបើប្រភពបង្ហាញ direct link គ្រប់ភាគ។</p>',
    unsafe_allow_html=True,
)
st.caption("បើតំណបង្ហាញតែប៊ូតុង “បើកក្នុង app” ហើយមិនមាន public episode/video link ទេ វាមិនអាចទាញយកពីទំព័រនោះបានទេ។")


def _clear_downloads() -> None:
    for key in list(st.session_state):
        if key.startswith("prepared_episode_") or key in {"prepared_archive", "prepared_archive_name"}:
            st.session_state.pop(key, None)


def _episode_key(episode: dict[str, Any]) -> str:
    identity = str(episode.get("page_url") or episode.get("media_url") or episode.get("number"))
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:14]


with st.form("series_search_form", clear_on_submit=False, border=True):
    st.markdown('<div class="eyebrow">01 · តំណទំព័ររឿង</div>', unsafe_allow_html=True)
    source_url = st.text_input(
        "តំណរឿង",
        placeholder="https://source.example/series/...",
        max_chars=2048,
        label_visibility="collapsed",
    )
    search_clicked = st.form_submit_button("ស្វែងរកភាគទាំងអស់", type="primary", use_container_width=True)

if search_clicked:
    _clear_downloads()
    st.session_state.pop("discovery_result", None)
    if not source_url.strip():
        st.error("សូមបញ្ចូលតំណទំព័ររឿង។")
    else:
        status = st.status("កំពុងស្វែងរកភាគដែលបង្ហាញជាសាធារណៈ…", expanded=False)
        try:
            result = discover_episodes(source_url.strip())
            st.session_state["discovery_result"] = {
                "series_title": result.series_title,
                "episodes": [episode.to_dict() for episode in result.episodes],
                "truncated": result.truncated,
            }
            status.update(label="ស្វែងរករួចរាល់", state="complete", expanded=False)
        except DiscoveryError as exc:
            status.update(label="មិនអាចស្វែងរកភាគបាន", state="error", expanded=False)
            st.error(str(exc))
        except Exception as exc:
            status.update(label="មិនអាចស្វែងរកភាគបាន", state="error", expanded=False)
            st.error(public_error_message(exc))

result_state = st.session_state.get("discovery_result")
if result_state:
    series_title = " ".join(str(result_state.get("series_title") or "រឿង").split())[:160]
    episodes = list(result_state.get("episodes") or [])
    st.markdown("---")
    st.text(series_title)
    st.metric("ចំនួនភាគដែលរកឃើញ", len(episodes))
    if result_state.get("truncated"):
        st.warning("បញ្ជីប្រភពមានលើសចំនួនដែល app អាចពិនិត្យក្នុងមួយលើក; លទ្ធផលអាចមិនទាន់ដល់ភាគចុងក្រោយទេ។")

    all_supported = len(episodes) > 1 and all(bool(item.get("media_url")) for item in episodes)
    archive_bytes = st.session_state.get("prepared_archive")
    archive_name = st.session_state.get("prepared_archive_name")
    if all_supported:
        if st.button("រៀបចំទាញយកគ្រប់ភាគជា ZIP", type="primary", use_container_width=True, key="prepare_all"):
            _clear_downloads()
            progress = st.status(f"កំពុងទាញយក {len(episodes)} ភាគតាមលំដាប់…", expanded=True)
            try:
                archive_bytes, archive_name = build_episode_archive(episodes, series_title)
                st.session_state["prepared_archive"] = archive_bytes
                st.session_state["prepared_archive_name"] = archive_name
                progress.update(label="ZIP រួចរាល់", state="complete", expanded=False)
            except Exception as exc:
                st.session_state.pop("prepared_archive", None)
                st.session_state.pop("prepared_archive_name", None)
                progress.update(label="មិនអាចរៀបចំ ZIP បាន", state="error", expanded=False)
                st.error(public_error_message(exc))
        archive_bytes = st.session_state.get("prepared_archive")
        archive_name = st.session_state.get("prepared_archive_name")
        if archive_bytes and archive_name:
            st.download_button(
                "ទាញយកឯកសារ ZIP",
                data=archive_bytes,
                file_name=str(archive_name),
                mime="application/zip",
                key="save_episode_archive",
                use_container_width=True,
            )
    elif len(episodes) > 1:
        st.info("ប្រភពបានបង្ហាញបញ្ជីភាគ ប៉ុន្តែមិនបានបង្ហាញ direct video link សម្រាប់គ្រប់ភាគទេ; អាចទាញយកតែភាគដែលមាន link ដែលគាំទ្រ។")

    for episode_data in episodes:
        number = int(episode_data["number"])
        title = " ".join(str(episode_data.get("title") or f"ភាគ {number}").split())[:200]
        page_url = str(episode_data.get("page_url") or "")
        media_url = episode_data.get("media_url")
        thumbnail_bytes = episode_data.get("thumbnail_bytes")
        key = _episode_key(episode_data)
        with st.container(border=True):
            image_col, details_col = st.columns([1, 3], vertical_alignment="center")
            if thumbnail_bytes:
                try:
                    image_col.image(thumbnail_bytes, width=140)
                except Exception:
                    image_col.markdown("▶")
            else:
                image_col.markdown("▶")
            details_col.text(f"ភាគ {number} · {title}")
            if media_url:
                if details_col.button("រៀបចំ MP4 ភាគនេះ", key=f"prepare_episode_{key}", use_container_width=True):
                    for state_key in list(st.session_state):
                        if state_key.startswith("prepared_episode_"):
                            st.session_state.pop(state_key, None)
                    st.session_state.pop("prepared_archive", None)
                    st.session_state.pop("prepared_archive_name", None)
                    status = st.status(f"កំពុងរៀបចំភាគ {number}…", expanded=False)
                    try:
                        payload, summary = download_video(
                            str(media_url),
                            show=series_title,
                            season=1,
                            episode=number,
                            title=title,
                            quality="best",
                        )
                        st.session_state[f"prepared_episode_{key}"] = {
                            "data": payload,
                            "file": str(summary["file"]),
                            "bytes": int(summary["bytes"]),
                            "duration": float(summary["duration"]),
                        }
                        status.update(label="ភាគរួចរាល់", state="complete", expanded=False)
                    except Exception as exc:
                        status.update(label="ទាញយកភាគមិនបានសម្រេច", state="error", expanded=False)
                        st.error(public_error_message(exc))
                prepared = st.session_state.get(f"prepared_episode_{key}")
                if prepared:
                    details_col.caption(f"{human_bytes(int(prepared['bytes']))} · {human_time(float(prepared['duration']))}")
                    details_col.download_button(
                        "ទាញយកឯកសារ MP4",
                        data=prepared["data"],
                        file_name=str(prepared["file"]),
                        mime="video/mp4",
                        key=f"save_episode_{key}",
                        use_container_width=True,
                    )
            else:
                details_col.button("មិនមាន direct video link ដែលគាំទ្រ", key=f"unsupported_{key}", disabled=True, use_container_width=True)

st.markdown("---")
st.caption("រកតែ episode links និង HLS/MP4 ដែលបង្ហាញជាសាធារណៈក្នុង HTML · មិន login · មិនហៅ private API · មិនដោះ DRM · ទាញយកតែអ្វីដែលអ្នកមានសិទ្ធិប្រើ។")
st.caption("ទំហំ ZIP សរុបមិនលើស 350 MiB; ការទាញយកទាំងអស់រួមគ្នាកំណត់ network 512 MiB/25 នាទី។")
