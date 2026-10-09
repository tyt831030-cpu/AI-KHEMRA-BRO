"""AI KHEMRA BRO — video-only Streamlit downloader."""
from __future__ import annotations

import streamlit as st

from cddl.utils import human_bytes, human_time
from safe_downloader import download_video, public_error_message

st.set_page_config(
    page_title="AI KHEMRA BRO · Video Download",
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
      --ink: #f7f8fc; --muted: #a7b1c1; --navy: #070d16;
      --panel: #0d1521; --line: #263648; --cyan: #28d7e7;
      --gold: #ffc928; --orange: #ff812b;
    }
    html, body, [class*="css"], [data-testid="stAppViewContainer"] {
      font-family: system-ui, "Noto Sans Khmer", "Khmer Sangam MN", sans-serif;
      color: var(--ink);
    }
    .stApp {
      background:
        radial-gradient(ellipse at 8% 0%, #13354470 0, transparent 38%),
        radial-gradient(ellipse at 96% 2%, #17314c78 0, transparent 35%),
        var(--navy);
      color: var(--ink);
    }
    .block-container { max-width: 800px; padding-top: 1.25rem; padding-bottom: 3rem; }
    header[data-testid="stHeader"] { background: #070d16; }
    .brand-panel {
      display: flex; align-items: center; gap: 16px; padding: 21px 22px;
      border: 1px solid var(--cyan); border-radius: 24px;
      background: linear-gradient(135deg, #101925, #0a111b);
      box-shadow: 0 0 24px #28d7e71d, inset 0 0 18px #28d7e709;
      margin-bottom: 1.45rem;
    }
    .brand-mark {
      display: grid; place-items: center; flex: 0 0 54px; height: 54px;
      border-radius: 18px; color: white; font-size: 25px; font-weight: 800;
      background: linear-gradient(135deg, var(--orange), var(--gold) 54%, var(--cyan));
      box-shadow: 0 7px 20px #ff812b36;
    }
    .brand-name { color: #fff; font-size: 1.22rem; font-weight: 850; letter-spacing: .035em; }
    .brand-sub { color: var(--cyan); font-size: .74rem; font-weight: 750; letter-spacing: .13em; margin-top: 4px; }
    h1, h2, h3 { color: #fff !important; letter-spacing: -.025em; }
    .intro { color: var(--muted); line-height: 1.8; margin: .3rem 0 1.2rem; }
    .eyebrow { color: var(--gold); font-size: .8rem; font-weight: 800; letter-spacing: .08em; margin-bottom: .65rem; }
    [data-testid="stForm"] {
      border: 1px solid var(--line); border-radius: 20px; background: #0b131e;
      padding: 20px 22px; box-shadow: 0 10px 32px #0005;
    }
    [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input,
    [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
      background: #f6f7fa !important; color: #131722 !important; border-radius: 11px !important;
    }
    [data-testid="stTextInput"] label, [data-testid="stNumberInput"] label,
    [data-testid="stSelectbox"] label, [data-testid="stCheckbox"] label { color: var(--ink) !important; }
    .stButton button[kind="primary"], .stDownloadButton button {
      border: 0; border-radius: 12px; min-height: 48px; font-weight: 800;
      color: #11151c; background: linear-gradient(100deg, var(--gold), #ffaf18);
      box-shadow: 0 7px 20px #ffc92824;
    }
    .stButton button[kind="primary"]:hover, .stDownloadButton button:hover {
      color: #11151c; filter: brightness(1.05); border: 0;
    }
    div[data-testid="stMetric"] { background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: 13px; }
    div[data-testid="stMetricLabel"] { color: var(--muted); }
    [data-testid="stAlert"] { border-radius: 12px; }
    hr { border-color: #263648; }
    footer { visibility: hidden; }
    @media (max-width: 600px) {
      .block-container { padding-left: .8rem; padding-right: .8rem; }
      .brand-panel { padding: 17px 15px; border-radius: 19px; }
      .brand-mark { flex-basis: 48px; height: 48px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="brand-panel"><div class="brand-mark">▶</div>'
    '<div><div class="brand-name">AI KHEMRA BRO</div>'
    '<div class="brand-sub">VIDEO DOWNLOADER</div></div></div>',
    unsafe_allow_html=True,
)
st.title("ទាញយកវីដេអូរឿង")
st.markdown(
    '<p class="intro">ទំព័រនេះមានតែមុខងារទាញយកវីដេអូ—មិនត្រូវការលេខកូដចូល ឬគណនីទេ។ '
    'បញ្ចូលតំណ HLS (.m3u8) ឬតំណ MP4 ផ្ទាល់ដែលអ្នកមានសិទ្ធិប្រើប្រាស់។</p>',
    unsafe_allow_html=True,
)

with st.expander("ព័ត៌មានអំពីប្រភពដែលគាំទ្រ", expanded=False):
    st.markdown(
        """
        - គាំទ្រ HLS VOD ដែលបានបញ្ចប់ (`.m3u8`) និងតំណ MP4 ផ្ទាល់ពី host សាធារណៈ។
        - គាំទ្រ AES-128 ស្តង់ដាររបស់ HLS ប៉ុន្តែមិនដោះ DRM (Widevine, FairPlay,
          PlayReady, SAMPLE-AES) ឬឆ្លងកាត់ paywall/login ទេ។
        - មិនភ្ជាប់ API ឯកជនទៅកម្មវិធីផ្សេងទេ។ សូមទាញយកតែវីដេអូដែលអ្នកមានសិទ្ធិ។
        - កំណត់សុវត្ថិភាព៖ network សរុប 512 MiB/25 នាទី, ឯកសារសម្រាប់ browser មិនលើស 350 MiB,
          HLS មិនលើស 10,000 segments ឬ 4 ម៉ោង; មានការទាញយកសកម្មអតិបរមា 2។
        """
    )

with st.form("video_download_form", clear_on_submit=False, border=True):
    st.markdown('<div class="eyebrow">01 · តំណ និងព័ត៌មានភាគ</div>', unsafe_allow_html=True)
    url = st.text_input(
        "តំណ HLS / MP4",
        placeholder="https://host.example/episode.m3u8",
        max_chars=2048,
    )
    show = st.text_input("ឈ្មោះរឿង", placeholder="ឧ. រឿងរបស់ខ្ញុំ", max_chars=120)
    col_a, col_b = st.columns(2)
    with col_a:
        season = st.number_input("រដូវកាល", min_value=1, max_value=99, value=1, step=1)
        episode = st.number_input("លេខភាគ", min_value=1, max_value=9999, value=1, step=1)
    with col_b:
        episode_title = st.text_input("ចំណងជើងភាគ (ជាជម្រើស)", max_chars=120)
        quality_label = st.selectbox("គុណភាព HLS", ["ល្អបំផុត", "1080p", "720p", "480p", "360p"], index=2)
    rights_confirmed = st.checkbox(
        "ខ្ញុំមានសិទ្ធិទាញយក និងរក្សាទុកវីដេអូនេះ ហើយមិនស្នើឲ្យរំលង DRM ឬការការពារសិទ្ធិទេ។"
    )
    submitted = st.form_submit_button("ពិនិត្យ និងទាញយកវីដេអូ", type="primary", use_container_width=True)

if submitted:
    st.session_state.pop("video_download_bytes", None)
    st.session_state.pop("video_download_summary", None)
    if not rights_confirmed:
        st.error("សូមបញ្ជាក់សិទ្ធិប្រើប្រាស់មុនបន្ត។")
    elif not url.strip():
        st.error("សូមបញ្ចូលតំណប្រភព។")
    elif not show.strip():
        st.error("សូមបញ្ចូលឈ្មោះរឿង។")
    else:
        quality_value: str | int = "best" if quality_label == "ល្អបំផុត" else int(quality_label.removesuffix("p"))
        status = st.status("កំពុងពិនិត្យតំណ និងទាញយក… សូមរង់ចាំ", expanded=True)
        try:
            payload, summary = download_video(
                url.strip(),
                show=show.strip(),
                season=int(season),
                episode=int(episode),
                title=episode_title.strip(),
                quality=quality_value,
            )
            st.session_state["video_download_bytes"] = payload
            st.session_state["video_download_summary"] = summary
            status.update(label="ទាញយករួចរាល់", state="complete", expanded=False)
        except Exception as exc:
            status.update(label="ការទាញយកមិនបានសម្រេច", state="error", expanded=False)
            st.error(public_error_message(exc))

summary = st.session_state.get("video_download_summary")
payload = st.session_state.get("video_download_bytes")
if summary and payload:
    st.markdown("---")
    st.markdown('<div class="eyebrow">02 · វីដេអូរួចរាល់</div>', unsafe_allow_html=True)
    left, middle, right = st.columns(3)
    left.metric("ឯកសារ", str(summary["file"]))
    middle.metric("ទំហំ", human_bytes(int(summary["bytes"])))
    right.metric("រយៈពេល", human_time(float(summary["duration"])))
    st.download_button(
        label=f"ទាញយក {summary['file']}",
        data=payload,
        file_name=str(summary["file"]),
        mime="video/mp4",
        key="download_video_mp4",
        use_container_width=True,
    )
    st.caption("ឯកសារបណ្តោះអាសន្នលើ server ត្រូវបានសម្អាតក្រោយរៀបចំការទាញយក; browser រក្សាទុក file ដែលអ្នកជ្រើសទាញយក។")

st.markdown("---")
st.caption("សម្រាប់តំណ HLS/MP4 សាធារណៈដែលអ្នកមានសិទ្ធិប្រើ · មិនដោះ DRM · មិនមានប្រព័ន្ធបកប្រែ")
