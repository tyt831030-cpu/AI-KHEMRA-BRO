import asyncio
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import edge_tts
import streamlit as st
from google import genai
from faster_whisper import WhisperModel

st.set_page_config(page_title='AI KHEMRA BRO', page_icon='🎬', layout='wide', initial_sidebar_state='expanded')

st.markdown('''
<style>
.stApp{background:#080d15;color:#f8fafc}
.block-container{max-width:1180px;padding-top:1.2rem;padding-bottom:3rem}
[data-testid="stSidebar"]{background:#101a2c;border-right:1px solid #26364d}
[data-testid="stSidebar"] .block-container{padding-top:1.1rem}
.hero{border:2px solid #d900ff;border-radius:24px;padding:34px 18px;text-align:center;background:linear-gradient(145deg,#17171d,#0b1018);box-shadow:0 0 24px rgba(217,0,255,.22);margin-bottom:18px}
.hero h1{font-size:44px;margin:0 0 8px;font-weight:900}
.hero p{margin:0;color:#23c8ef;font-weight:800;letter-spacing:1.5px}
.profile-card{border:2px solid #13c9ef;border-radius:18px;padding:20px 12px;text-align:center;background:#131e31;box-shadow:0 0 16px rgba(19,201,239,.2);margin-bottom:12px}
.side-ok{background:#073d31;border:1px solid #10b981;border-radius:12px;padding:12px;margin:10px 0}
.section-title{font-size:30px;font-weight:900;margin:22px 0 10px}
.step{background:#111b2a;border:1px solid #26374f;border-radius:16px;padding:14px 16px;margin:12px 0}
.ok{background:#073d31;border:1px solid #10b981;border-radius:14px;padding:13px 15px;margin:10px 0}
.stButton>button{width:100%;min-height:48px;border:0;border-radius:11px;color:white;font-weight:850;font-size:15px;background:linear-gradient(90deg,#9b1bd1,#ec00ff)}
.stDownloadButton>button{width:100%;min-height:46px;border-radius:11px;font-weight:800}
div[data-testid="stFileUploader"]{background:#eef2f7;border-radius:12px;padding:8px}
div[data-testid="stTextArea"] textarea{background:#182438!important;color:#fff!important;border:1px solid #8290a4!important;border-radius:10px!important;font-size:16px!important;line-height:1.65!important;font-family:"Noto Sans Khmer","Khmer OS System",Arial,sans-serif!important}
button[data-baseweb="tab"]{background:#151f31;border-radius:8px 8px 0 0;padding:10px 16px}
button[data-baseweb="tab"][aria-selected="true"]{background:linear-gradient(90deg,#b000df,#f000ff);color:white}
.clear-wrap .stButton>button{background:linear-gradient(90deg,#08bce3,#12d6ef);color:#00141b;font-weight:900}
@media(max-width:700px){
.block-container{padding-left:.75rem;padding-right:.75rem}
.hero{padding:24px 10px}.hero h1{font-size:31px}.hero p{font-size:11px}
.section-title{font-size:26px}
}
</style>
''', unsafe_allow_html=True)

PISITH='km-KH-PisethNeural'
SREYMOM='km-KH-SreymomNeural'
VOICE_PROFILES={
'M':{'voice':PISITH,'rate':'+0%','pitch':'+0Hz','volume':'+0%'},
'F':{'voice':SREYMOM,'rate':'+0%','pitch':'+0Hz','volume':'+0%'},
'BOY':{'voice':PISITH,'rate':'+8%','pitch':'+24Hz','volume':'+0%'},
'GIRL':{'voice':SREYMOM,'rate':'+8%','pitch':'+28Hz','volume':'+0%'},
'OLD_M':{'voice':PISITH,'rate':'-12%','pitch':'-18Hz','volume':'-2%'},
'OLD_F':{'voice':SREYMOM,'rate':'-12%','pitch':'-15Hz','volume':'-2%'},
'M_THINK':{'voice':PISITH,'rate':'-8%','pitch':'-8Hz','volume':'-12%'},
'F_THINK':{'voice':SREYMOM,'rate':'-8%','pitch':'-6Hz','volume':'-12%'},
'NARRATOR_M':{'voice':PISITH,'rate':'-3%','pitch':'-3Hz','volume':'+0%'},
'NARRATOR_F':{'voice':SREYMOM,'rate':'-3%','pitch':'-2Hz','volume':'+0%'}}

TRANSLATE_PROMPT = """You are an expert Chinese-drama translator and dubbing director.
The supplied cue IDs and Whisper timestamps are authoritative and MUST NOT be changed.
Use the uploaded video only to understand dialogue, visible speaker, age, gender, narration, and inner thoughts.

Return a JSON array only. Each object must contain exactly:
{"id": integer, "tag": string, "text": string}

Allowed tags:
M, F, BOY, GIRL, OLD_M, OLD_F, M_THINK, F_THINK, NARRATOR_M, NARRATOR_F

Rules:
- Return exactly one object for every supplied cue ID, in the same order.
- Translate into natural spoken Khmer suitable for Chinese drama dubbing.
- Preserve meaning, emotion, names, ranks, relationships and pronouns.
- Use M_THINK/F_THINK only for unheard inner monologue.
- Use BOY/GIRL only for children; OLD_M/OLD_F only for elderly speakers.
- Use NARRATOR_M/NARRATOR_F only for narration.
- No Chinese characters in the Khmer text.
- Never invent, merge, split, omit, or renumber cues.
- JSON only. No markdown fences or explanation.
"""

ANALYZE_PROMPT = """You are a Chinese-drama Khmer dubbing editor.
Improve the supplied Khmer SRT dialogue and classify speakers, while preserving every cue number and timestamp exactly.
Return a JSON array only with exactly:
{"id": integer, "tag": string, "text": string}

Allowed tags:
M, F, BOY, GIRL, OLD_M, OLD_F, M_THINK, F_THINK, NARRATOR_M, NARRATOR_F

Rules:
- Return exactly one object per cue ID in the same order.
- Do not alter timestamps, cue count, or cue order.
- Correct incomplete or awkward Khmer into natural spoken Khmer.
- Keep character identity consistent across nearby cues.
- Detect inner thought, narrator, adult, child, and elderly roles from context.
- Do not add explanations or markdown.
"""

@st.cache_resource(show_spinner=False)
def load_whisper_model():
    # Base + int8 is selected so it can run on Streamlit Community Cloud CPU.
    return WhisperModel("base", device="cpu", compute_type="int8")

for key,value in {
    'srt_text':'',
    'pending_srt':'',
    'audio_bytes':None,
}.items():
    if key not in st.session_state:
        st.session_state[key]=value

def clean_srt(text):
    text=re.sub(r'^```(?:srt)?\s*','',text.strip(),flags=re.I)
    return re.sub(r'\s*```$','',text).strip()

def save_upload(uploaded_file):
    """Save the received MP4 without making another full in-memory copy."""
    suffix = Path(uploaded_file.name).suffix or '.mp4'
    uploaded_file.seek(0)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        shutil.copyfileobj(uploaded_file, temp, length=1024 * 1024)
        temp.flush()
        return Path(temp.name)

def seconds_to_srt(value):
    total_ms = max(0, int(round(float(value) * 1000)))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def extract_audio(video_path, wav_path):
    result = subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(video_path),
            "-vn", "-ac", "1", "-ar", "16000",
            "-c:a", "pcm_s16le", str(wav_path),
        ],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0 or not wav_path.exists():
        raise RuntimeError(result.stderr[-1200:] or "មិនអាចទាញសំឡេងចេញពីវីដេអូបានទេ។")


def transcribe_with_whisper(wav_path):
    model = load_whisper_model()
    segments, _ = model.transcribe(
        str(wav_path),
        language="zh",
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 250},
        condition_on_previous_text=True,
        word_timestamps=False,
    )
    cues = []
    last_end = 0.0
    for segment in segments:
        source = (segment.text or "").strip()
        if not source:
            continue
        start = max(0.0, float(segment.start))
        end = max(start + 0.18, float(segment.end))
        # Remove tiny ASR overlaps while keeping the real Whisper timing.
        if start < last_end and (last_end - start) < 0.35:
            start = last_end
        if end <= start:
            end = start + 0.35
        cues.append({
            "id": len(cues) + 1,
            "start": start,
            "end": end,
            "source": source,
        })
        last_end = end
    if not cues:
        raise RuntimeError("Whisper មិនបានរកឃើញសន្ទនាក្នុងវីដេអូនេះទេ។")
    return cues


def upload_for_context(client, video_path):
    uploaded = client.files.upload(file=str(video_path))
    for _ in range(120):
        state = getattr(getattr(uploaded, "state", None), "name", "")
        if state != "PROCESSING":
            break
        time.sleep(2)
        uploaded = client.files.get(name=uploaded.name)
    if getattr(getattr(uploaded, "state", None), "name", "") == "FAILED":
        raise RuntimeError("AI មិនអាចអានវីដេអូនេះបានទេ។")
    return uploaded


def parse_json_array(raw_text):
    import json
    cleaned = (raw_text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\\s*", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\\s*```$", "", cleaned)
    left, right = cleaned.find("["), cleaned.rfind("]")
    if left == -1 or right == -1 or right <= left:
        raise ValueError("AI មិនបានត្រឡប់ JSON ត្រឹមត្រូវ។")
    value = json.loads(cleaned[left:right + 1])
    if not isinstance(value, list):
        raise ValueError("AI JSON មិនមែនជាបញ្ជី។")
    return value


def translate_cues(client, model_name, uploaded_video, cues):
    result_by_id = {}
    batch_size = 30
    for offset in range(0, len(cues), batch_size):
        batch = cues[offset:offset + batch_size]
        cue_lines = "\n".join(
            f"ID={cue['id']} | {seconds_to_srt(cue['start'])} --> "
            f"{seconds_to_srt(cue['end'])} | SOURCE={cue['source']}"
            for cue in batch
        )
        response = client.models.generate_content(
            model=model_name,
            contents=[uploaded_video, TRANSLATE_PROMPT + "\n\nCUES:\n" + cue_lines],
        )
        items = parse_json_array(response.text or "")
        for item in items:
            try:
                cue_id = int(item.get("id"))
            except (TypeError, ValueError, AttributeError):
                continue
            tag = str(item.get("tag", "M")).upper().strip()
            if tag not in VOICE_PROFILES:
                tag = "M"
            translated = str(item.get("text", "")).strip()
            if translated:
                result_by_id[cue_id] = {"tag": tag, "text": translated}

    missing = [cue["id"] for cue in cues if cue["id"] not in result_by_id]
    if missing:
        raise RuntimeError(
            "AI បកប្រែមិនអស់គ្រប់បន្ទាត់។ សូមចុច Generate ម្តងទៀត។ "
            f"បាត់បន្ទាត់៖ {missing[:12]}"
        )
    return result_by_id


def build_srt(cues, translated):
    blocks = []
    for cue in cues:
        item = translated[cue["id"]]
        blocks.append(
            f'{cue["id"]}\n'
            f'{seconds_to_srt(cue["start"])} --> {seconds_to_srt(cue["end"])}\n'
            f'[{item["tag"]}] {item["text"]}'
        )
    return "\n\n".join(blocks)


def video_to_srt(video_path, api_key, model):
    """Whisper owns timestamps; Gemini only translates and labels each fixed cue."""
    with tempfile.TemporaryDirectory() as folder:
        wav_path = Path(folder) / "audio.wav"
        extract_audio(video_path, wav_path)
        cues = transcribe_with_whisper(wav_path)

        client = genai.Client(api_key=api_key)
        uploaded_video = upload_for_context(client, video_path)
        translated = translate_cues(client, model, uploaded_video, cues)
        result = build_srt(cues, translated)
        if "-->" not in result:
            raise RuntimeError("មិនអាចបង្កើត Khmer SRT បានទេ។")
        return result


def srt_to_structured_cues(srt_text):
    parsed = parse_srt(srt_text)
    return [
        {
            "id": index,
            "start_ms": cue["start"],
            "end_ms": cue["end"],
            "tag": cue["tag"],
            "text": cue["text"],
        }
        for index, cue in enumerate(parsed, start=1)
    ]


def ms_to_srt(value):
    return seconds_to_srt(value / 1000.0)


def analyze_inner_thoughts(srt_text, api_key, model_name, video_path=None):
    cues = srt_to_structured_cues(srt_text)
    if not cues:
        raise ValueError("រកមិនឃើញ SRT ត្រឹមត្រូវទេ។")
    client = genai.Client(api_key=api_key)
    context = upload_for_context(client, video_path) if video_path else None
    updated = {}
    batch_size = 35
    for offset in range(0, len(cues), batch_size):
        batch = cues[offset:offset + batch_size]
        payload = "\n".join(
            f'ID={cue["id"]} | TAG={cue["tag"]} | TEXT={cue["text"]}'
            for cue in batch
        )
        contents = [ANALYZE_PROMPT + "\n\nCUES:\n" + payload]
        if context is not None:
            contents.insert(0, context)
        response = client.models.generate_content(model=model_name, contents=contents)
        for item in parse_json_array(response.text or ""):
            try:
                cue_id = int(item.get("id"))
            except (TypeError, ValueError, AttributeError):
                continue
            tag = str(item.get("tag", "M")).upper().strip()
            if tag not in VOICE_PROFILES:
                tag = "M"
            dialogue = str(item.get("text", "")).strip()
            if dialogue:
                updated[cue_id] = {"tag": tag, "text": dialogue}

    blocks = []
    for cue in cues:
        item = updated.get(cue["id"], {"tag": cue["tag"], "text": cue["text"]})
        blocks.append(
            f'{cue["id"]}\n{ms_to_srt(cue["start_ms"])} --> {ms_to_srt(cue["end_ms"])}\n'
            f'[{item["tag"]}] {item["text"]}'
        )
    return "\n\n".join(blocks)

def parse_srt(srt_text):
    time_re=re.compile(r'(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})')
    tag_re=re.compile(r'^\[(M|F|BOY|GIRL|OLD_M|OLD_F|M_THINK|F_THINK|NARRATOR_M|NARRATOR_F)\]\s*',re.I)
    def to_ms(v):
        h,m,s,ms=map(int,v); return ((h*60+m)*60+s)*1000+ms
    cues=[]
    for block in re.split(r'\n\s*\n',srt_text.strip()):
        lines=[x.strip() for x in block.splitlines() if x.strip()]
        idx=next((i for i,x in enumerate(lines) if '-->' in x),None)
        if idx is None or idx+1>=len(lines): continue
        match=time_re.search(lines[idx])
        if not match: continue
        dialogue=' '.join(lines[idx+1:]).strip(); tag_match=tag_re.match(dialogue)
        tag=tag_match.group(1).upper() if tag_match else 'M'
        if tag_match: dialogue=dialogue[tag_match.end():].strip()
        if dialogue:
            start_ms=to_ms(match.groups()[:4]); end_ms=to_ms(match.groups()[4:])
            if end_ms <= start_ms: end_ms = start_ms + 350
            cues.append({'start':start_ms,'end':end_ms,'tag':tag,'text':dialogue})
    return cues

def run_async(coro):
    loop=asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop); return loop.run_until_complete(coro)
    finally:
        loop.close(); asyncio.set_event_loop(None)

async def synthesize(text,profile,output_path):
    await edge_tts.Communicate(text=text,voice=profile['voice'],rate=profile['rate'],pitch=profile['pitch'],volume=profile['volume']).save(str(output_path))

def probe_audio_duration(path):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-500:] or "FFprobe failed.")
    return max(0.01, float(result.stdout.strip()))


def atempo_chain(speed):
    """Build a valid FFmpeg atempo chain for speed factors above 1."""
    factors = []
    remaining = max(1.0, float(speed))
    while remaining > 2.0:
        factors.append(2.0)
        remaining /= 2.0
    if remaining > 1.001:
        factors.append(remaining)
    return ",".join(f"atempo={value:.5f}" for value in factors)


def create_mp3(srt_text):
    cues = parse_srt(srt_text)
    if not cues:
        raise ValueError('រកមិនឃើញ SRT និង timestamp ត្រឹមត្រូវទេ។')

    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        clips = []
        clip_durations = []

        for index, cue in enumerate(cues):
            clip = root / f'clip_{index:04d}.mp3'
            profile = VOICE_PROFILES.get(cue['tag'], VOICE_PROFILES['M'])
            run_async(synthesize(cue['text'], profile, clip))
            clips.append(clip)
            clip_durations.append(probe_audio_duration(clip))

        command = ['ffmpeg', '-y']
        for clip in clips:
            command.extend(['-i', str(clip)])

        filters = []
        labels = []

        for index, cue in enumerate(cues):
            slot_seconds = max(0.12, (cue['end'] - cue['start']) / 1000)
            original_seconds = clip_durations[index]
            delay = max(0, cue['start'])
            label = f'a{index}'

            chain = [f'[{index}:a]', 'asetpts=PTS-STARTPTS']

            # Speed up only when the generated speech is longer than its SRT slot.
            # This avoids cutting off the end of sentences.
            speed = original_seconds / slot_seconds
            if speed > 1.03:
                tempo = atempo_chain(speed)
                if tempo:
                    chain.append(tempo)

            chain.extend([
                f'atrim=0:{slot_seconds:.3f}',
                f'apad=whole_dur={slot_seconds:.3f}',
                f'atrim=0:{slot_seconds:.3f}',
                f'adelay={delay}|{delay}[{label}]',
            ])

            filters.append(','.join(chain).replace('],', ']'))
            labels.append(f'[{label}]')

        total = (max(c['end'] for c in cues) + 500) / 1000
        filters.append(
            ''.join(labels)
            + f'amix=inputs={len(labels)}:duration=longest:dropout_transition=0,'
              f'apad=whole_dur={total:.3f},atrim=0:{total:.3f}[out]'
        )

        output = root / 'khmer_dubbed.mp3'
        command.extend([
            '-filter_complex', ';'.join(filters),
            '-map', '[out]',
            '-ac', '2',
            '-ar', '44100',
            '-b:a', '128k',
            str(output),
        ])

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr[-1500:] or 'FFmpeg failed.')

        return output.read_bytes()


with st.sidebar:
    st.markdown(
        '<div class="profile-card">👋 <b>AI KHEMRA BRO</b><br><small>ROLE: ADMIN</small><br><br>🗓️ PLAN: LIFETIME<br>💎 PRO</div>',
        unsafe_allow_html=True,
    )
    st.button("🚪 ចាកចេញ (Logout)", key="logout")

    st.markdown("---")
    st.subheader("🌍 Target Language")
    st.selectbox("ជ្រើសភាសា", ["Khmer (ខ្មែរ)"], key="target_language")

    st.markdown("---")
    st.subheader("🔑 API Keys Manager")
    api_keys_text = st.text_area(
        "Paste Gemini API Keys (One per line)",
        height=130,
        placeholder="AIza...\nAIza...",
        key="api_keys_manager",
    )
    valid_api_keys = [x.strip() for x in api_keys_text.splitlines() if x.strip()]
    if valid_api_keys:
        st.markdown(
            f'<div class="side-ok">✅ រកឃើញ {len(valid_api_keys)} Keys</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.subheader("🎭 Translation Style")
    translation_style = st.radio(
        "ជ្រើសរបៀបបកប្រែ",
        ["🔴 Chinese Drama Pro", "⚪ Whisper Timestamp Sync", "⚪ Standard"],
        key="translation_style",
    )

    st.markdown("---")
    model = st.selectbox(
        "Model",
        ["gemini-2.5-flash", "gemini-2.5-pro"],
        key="model_selector",
    )
    lite_mode = st.toggle("📶 4G Lite Mode", value=True)
    max_mb = 60 if lite_mode else 150
    st.caption(f"ណែនាំវីដេអូមិនលើស {max_mb} MB")

api_key = valid_api_keys[0] if valid_api_keys else ""

st.markdown(
    '<div class="hero"><h1>AI KHEMRA BRO</h1><p>GLOBAL AI DUBBING & SUBTITLING WORKSTATION</p></div>',
    unsafe_allow_html=True,
)

tab_video, tab_translate, tab_srt_speech, tab_text_speech = st.tabs(
    ["🎬 Video → SRT", "📝 AI Subtitle Translator", "📜 SRT → Speech", "🎙️ Text → Speech"]
)

with tab_video:
    st.markdown('<div class="section-title">1️⃣ Generate Subtitles (Khmer ខ្មែរ)</div>', unsafe_allow_html=True)

    uploaded_video = st.file_uploader(
        "Upload Video",
        type=["mp4", "mov", "mkv", "webm"],
        help="MP4 ត្រូវបានណែនាំសម្រាប់ 4G និងទូរស័ព្ទ។",
        key="main_video_upload",
    )

    if uploaded_video is not None:
        size_mb = uploaded_video.size / (1024 * 1024)
        st.markdown(
            f'<div class="ok">✅ {uploaded_video.name}<br>📦 {size_mb:.1f} MB</div>',
            unsafe_allow_html=True,
        )

        if size_mb > max_mb:
            st.error(f"សូមបង្រួមវីដេអូឱ្យតិចជាង {max_mb} MB។")
        else:
            if not lite_mode and st.checkbox("▶️ Video Preview"):
                st.video(uploaded_video)

            if st.button("📝 Generate Khmer SRT", key="generate_srt"):
                if not api_key:
                    st.error("សូមបញ្ចូល Gemini API Key នៅ Sidebar ជាមុន។")
                else:
                    video_path = save_upload(uploaded_video)
                    try:
                        progress_bar = st.progress(1)
                        progress_text = st.empty()
                        started_at = time.time()

                        # Run the AI task in another thread so the page can keep
                        # updating the percentage and elapsed time.
                        with ThreadPoolExecutor(max_workers=1) as executor:
                            future = executor.submit(
                                video_to_srt,
                                video_path,
                                api_key,
                                model,
                            )

                            # Estimate only; the real finish time depends on 4G,
                            # video duration, Gemini processing and server load.
                            estimated_seconds = max(45.0, min(600.0, 35.0 + (size_mb * 5.0)))

                            while not future.done():
                                elapsed = time.time() - started_at
                                percent = min(
                                    95,
                                    max(1, int((elapsed / estimated_seconds) * 95)),
                                )
                                minutes = int(elapsed // 60)
                                seconds = int(elapsed % 60)

                                progress_bar.progress(percent)
                                progress_text.markdown(
                                    f"### ⏱️ {percent}%  •  "
                                    f"{minutes:02d}:{seconds:02d}"
                                )
                                time.sleep(0.5)

                            generated_srt = future.result()

                        # Automatically place the completed Khmer SRT into the
                        # existing editor when progress reaches 100%.
                        st.session_state.srt_text = generated_srt
                        st.session_state.main_srt_editor = generated_srt
                        st.session_state.pending_srt = ""
                        st.session_state.audio_bytes = None
                        elapsed = time.time() - started_at
                        minutes = int(elapsed // 60)
                        seconds = int(elapsed % 60)

                        progress_bar.progress(100)
                        progress_text.markdown(
                            f"### ✅ 100%  •  {minutes:02d}:{seconds:02d}"
                        )
                        st.success("✅ Khmer SRT ready • Timestamp ពិតពី Whisper")

                    except Exception as exc:
                        st.error(f"❌ {exc}")
                    finally:
                        video_path.unlink(missing_ok=True)

    st.subheader("Generated SRT")
    st.caption("SRT នឹងចូលប្រអប់នេះដោយស្វ័យប្រវត្តិ ពេលដំណើរការដល់ 100%។ អ្នកអាចកែបានមុន Generate MP3។")

    if "main_srt_editor" not in st.session_state:
        st.session_state.main_srt_editor = st.session_state.srt_text

    st.text_area(
        "SRT Editor",
        height=360,
        label_visibility="collapsed",
        key="main_srt_editor",
    )
    st.session_state.srt_text = st.session_state.main_srt_editor

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("🧠 វិភាគការគិតក្នុងចិត្ត (Analyze Inner Thoughts)", key="analyze_thoughts"):
            if not st.session_state.srt_text.strip():
                st.warning("សូមបង្កើត ឬបញ្ចូល SRT ជាមុន។")
            elif not api_key:
                st.error("សូមបញ្ចូល Gemini API Key នៅ Sidebar ជាមុន។")
            else:
                analysis_video_path = None
                try:
                    if uploaded_video is not None:
                        analysis_video_path = save_upload(uploaded_video)
                    with st.spinner("កំពុងកែសន្ទនា និងវិភាគ ប្រុស/ស្រី/ក្មេង/ចាស់/ការគិតក្នុងចិត្ត…"):
                        analyzed_srt = analyze_inner_thoughts(
                            st.session_state.srt_text,
                            api_key,
                            model,
                            analysis_video_path,
                        )
                    st.session_state.srt_text = analyzed_srt
                    st.session_state.main_srt_editor = analyzed_srt
                    st.session_state.audio_bytes = None
                    st.success("✅ វិភាគ និងកែសម្រួល SRT រួចរាល់។ Timestamp ត្រូវបានរក្សាដដែល។")
                    st.rerun()
                except Exception as exc:
                    st.error(f"❌ {exc}")
                finally:
                    if analysis_video_path is not None:
                        analysis_video_path.unlink(missing_ok=True)
    with c2:
        if st.session_state.srt_text:
            st.download_button(
                "⬇️ Download SRT",
                st.session_state.srt_text.encode("utf-8"),
                "khmer_story.srt",
                "application/x-subrip",
            )

    st.markdown('<div class="section-title">2️⃣ AI Dubbing (Edge TTS Studio)</div>', unsafe_allow_html=True)

    if st.button("🎙️ Generate Dubbed Audio (MP3)", key="generate_audio"):
        if not st.session_state.srt_text.strip():
            st.warning("សូមបង្កើត ឬបញ្ចូល SRT ជាមុន។")
        else:
            try:
                with st.spinner("កំពុងបង្កើតសំឡេង Piseth, Sreymom និងតួអង្គ…"):
                    st.session_state.audio_bytes = create_mp3(st.session_state.srt_text)
                st.success("✅ បង្កើត MP3 រួចរាល់។")
            except Exception as exc:
                st.error(f"❌ {exc}")

    if st.session_state.audio_bytes:
        st.audio(st.session_state.audio_bytes, format="audio/mp3")
        st.download_button(
            "⬇️ Download Dubbed MP3",
            st.session_state.audio_bytes,
            "khmer_story_dubbed.mp3",
            "audio/mpeg",
        )

    st.markdown('<div class="clear-wrap">', unsafe_allow_html=True)
    if st.button("🗑️ សម្អាត (Clear Video Project)", key="clear_project"):
        st.session_state.srt_text = ""
        st.session_state.pending_srt = ""
        st.session_state.audio_bytes = None
        st.session_state.main_srt_editor = ""
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

with tab_translate:
    st.header("AI Subtitle Translator")
    st.info("បិទភ្ជាប់ Chinese SRT ហើយបកប្រែទៅ Khmer SRT។")
    source_srt = st.text_area("Chinese SRT", height=300, key="translator_source")
    if st.button("🌐 Translate to Khmer", key="translate_btn"):
        if not source_srt.strip():
            st.warning("សូមបញ្ចូល Chinese SRT។")
        elif not api_key:
            st.error("សូមបញ្ចូល Gemini API Key នៅ Sidebar។")
        else:
            try:
                source_cues = srt_to_structured_cues(source_srt)
                if not source_cues:
                    raise ValueError("Chinese SRT មិនត្រឹមត្រូវ។")
                client = genai.Client(api_key=api_key)
                translated_map = {}
                for offset in range(0, len(source_cues), 35):
                    batch = source_cues[offset:offset + 35]
                    payload = "\n".join(
                        f'ID={cue["id"]} | SOURCE={cue["text"]}' for cue in batch
                    )
                    response = client.models.generate_content(
                        model=model,
                        contents=TRANSLATE_PROMPT + "\n\nCUES:\n" + payload,
                    )
                    for item in parse_json_array(response.text or ""):
                        cue_id = int(item.get("id"))
                        tag = str(item.get("tag", "M")).upper()
                        if tag not in VOICE_PROFILES:
                            tag = "M"
                        translated_map[cue_id] = {"tag": tag, "text": str(item.get("text", "")).strip()}
                blocks = []
                for cue in source_cues:
                    item = translated_map.get(cue["id"])
                    if not item or not item["text"]:
                        raise RuntimeError(f'បកប្រែមិនអស់បន្ទាត់ {cue["id"]}')
                    blocks.append(
                        f'{cue["id"]}\n{ms_to_srt(cue["start_ms"])} --> {ms_to_srt(cue["end_ms"])}\n'
                        f'[{item["tag"]}] {item["text"]}'
                    )
                st.session_state.srt_text = "\n\n".join(blocks)
                st.session_state.main_srt_editor = st.session_state.srt_text
                st.success("✅ បកប្រែរួចរាល់ និងរក្សា Timestamp ដើម។")
            except Exception as exc:
                st.error(f"❌ {exc}")

with tab_srt_speech:
    st.header("SRT → Speech")
    speech_srt = st.text_area(
        "Khmer SRT with [M] [F] [BOY] [GIRL] [OLD_M] [OLD_F] [M_THINK] [F_THINK]",
        height=360,
        key="speech_srt_input",
    )
    if st.button("🎧 Create MP3", key="srt_to_speech_btn"):
        if not speech_srt.strip():
            st.warning("សូមបញ្ចូល Khmer SRT។")
        else:
            try:
                with st.spinner("កំពុងបង្កើតសំឡេង…"):
                    st.session_state.audio_bytes = create_mp3(speech_srt)
                st.success("✅ បង្កើត MP3 រួចរាល់។")
            except Exception as exc:
                st.error(f"❌ {exc}")

with tab_text_speech:
    st.header("Text → Speech")
    plain_text = st.text_area("Khmer Text", height=260, key="plain_text_input")
    voice_choice = st.selectbox(
        "Voice",
        ["M", "F", "BOY", "GIRL", "OLD_M", "OLD_F", "M_THINK", "F_THINK"],
        key="plain_voice",
    )
    if st.button("🔊 Generate Voice", key="plain_voice_btn"):
        if not plain_text.strip():
            st.warning("សូមបញ្ចូលអត្ថបទខ្មែរ។")
        else:
            try:
                with tempfile.TemporaryDirectory() as folder:
                    output = Path(folder) / "speech.mp3"
                    run_async(synthesize(plain_text.strip(), VOICE_PROFILES[voice_choice], output))
                    st.session_state.audio_bytes = output.read_bytes()
                st.success("✅ បង្កើតសំឡេងរួចរាល់។")
            except Exception as exc:
                st.error(f"❌ {exc}")

st.caption("AI-KHEMRA-BRO • Chinese Story Translation • Mobile-first")
