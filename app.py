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

PROMPT='''You are an expert Chinese-drama subtitle translator and dubbing director.

Analyze BOTH the audio and visible character context in the uploaded video.
Return valid Khmer SRT only.

TIMING RULES:
1. Each timestamp must begin when the spoken line begins and end when it ends.
2. Do not overlap neighboring cues unless two characters truly speak at the same time.
3. Do not skip whispers, short replies, cries, or inner thoughts.
4. Keep cue order strictly chronological.
5. Use SRT time format exactly: 00:00:00,000 --> 00:00:03,000.

KHMER RULES:
6. Translate into natural spoken Khmer for Chinese drama dubbing.
7. Preserve names, rank, age, relationship, emotion, and pronouns consistently.
8. No Chinese characters in the Khmer dialogue.

SPEAKER RULES:
9. Add exactly one tag at the beginning of every subtitle dialogue.
10. Keep the same character tag consistent across nearby cues.
11. Inner monologue or unheard thought must use M_THINK or F_THINK.
12. A visible speaking child must use BOY or GIRL.
13. An elderly speaker must use OLD_M or OLD_F.
14. Normal adult dialogue must use M or F.
15. Narration must use NARRATOR_M or NARRATOR_F.

Allowed tags only:
[M] [F] [BOY] [GIRL] [OLD_M] [OLD_F]
[M_THINK] [F_THINK] [NARRATOR_M] [NARRATOR_F]

OUTPUT RULES:
16. Output SRT only.
17. No markdown fences and no explanation.
'''

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

def video_to_srt(video_path,api_key,model):
    client=genai.Client(api_key=api_key)
    uploaded=client.files.upload(file=str(video_path))
    for _ in range(90):
        state=getattr(getattr(uploaded,'state',None),'name','')
        if state!='PROCESSING': break
        time.sleep(2); uploaded=client.files.get(name=uploaded.name)
    if getattr(getattr(uploaded,'state',None),'name','')=='FAILED': raise RuntimeError('AI មិនអាចដំណើរការវីដេអូនេះបានទេ។')
    response=client.models.generate_content(model=model,contents=[uploaded,PROMPT])
    result=clean_srt(response.text or '')
    if '-->' not in result: raise RuntimeError('AI មិនបានបង្កើត SRT ត្រឹមត្រូវទេ។')
    return result

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
        if dialogue: cues.append({'start':to_ms(match.groups()[:4]),'end':to_ms(match.groups()[4:]),'tag':tag,'text':dialogue})
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
        ["🔴 Chinese Drama Pro", "⚪ 100% Audio Sync", "⚪ Standard"],
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
                        st.success("✅ Khmer SRT ready")

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
            else:
                st.info("✅ SRT ត្រៀមរួចសម្រាប់ស្លាក [M_THINK] និង [F_THINK]។")
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
            client = genai.Client(api_key=api_key)
            prompt = PROMPT + "\nKeep all original numbering and timestamps unchanged.\nSOURCE:\n" + source_srt
            try:
                with st.spinner("កំពុងបកប្រែ…"):
                    response = client.models.generate_content(model=model, contents=prompt)
                    st.session_state.srt_text = clean_srt(response.text or "")
                st.success("✅ បកប្រែរួចរាល់។")
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
