import asyncio
import base64
import datetime
import hashlib
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import edge_tts
import extra_streamlit_components as stx
import streamlit as st
from cryptography.fernet import Fernet, InvalidToken
from google import genai
from faster_whisper import WhisperModel

st.set_page_config(page_title='AI KHEMRA BRO', page_icon='🎬', layout='wide', initial_sidebar_state='collapsed')

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
/* Remove Streamlit's white top bar, GitHub icon, Fork label and menu. */
[data-testid="stHeader"]{
display:none!important;
}
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
#MainMenu,
footer{
display:none!important;
}

/* White sidebar/API arrow on a black button, fixed at the top-left corner. */
[data-testid="stSidebarCollapsedControl"]{
position:fixed!important;
top:8px!important;
left:8px!important;
right:auto!important;
z-index:999999!important;
width:42px!important;
height:38px!important;
display:flex!important;
align-items:center!important;
justify-content:center!important;
}
[data-testid="stSidebarCollapsedControl"] button{
width:42px!important;
height:38px!important;
min-height:38px!important;
padding:0!important;
border-radius:11px!important;
background:#050505!important;
border:1px solid #2a2a2a!important;
box-shadow:0 3px 12px rgba(0,0,0,.45)!important;
display:flex!important;
align-items:center!important;
justify-content:center!important;
opacity:1!important;
}
[data-testid="stSidebarCollapsedControl"] button:hover{
background:#111111!important;
border-color:#ffffff!important;
}
[data-testid="stSidebarCollapsedControl"] svg{
display:block!important;
width:22px!important;
height:22px!important;
color:#ffffff!important;
fill:#ffffff!important;
stroke:#ffffff!important;
opacity:1!important;
}

/* Let the branded app header begin at the very top of the phone. */
.block-container{
padding-top:.45rem!important;
}
.hero{
margin-top:0!important;
width:100%!important;
box-sizing:border-box!important;
overflow:hidden!important;
}
.hero h1{
white-space:nowrap!important;
line-height:1.05!important;
}
.hero p{
white-space:normal!important;
overflow-wrap:anywhere!important;
}

@media(max-width:700px){
.block-container{
padding-left:.55rem!important;
padding-right:.55rem!important;
padding-top:.35rem!important;
}
.hero{
padding:28px 8px 24px!important;
border-radius:18px!important;
margin-bottom:14px!important;
}
.hero h1{
font-size:clamp(28px,9vw,42px)!important;
letter-spacing:-1px!important;
}
.hero p{
font-size:clamp(9px,2.7vw,12px)!important;
letter-spacing:.8px!important;
line-height:1.35!important;
padding:0 6px!important;
}
.section-title{font-size:26px}
[data-testid="stSidebarCollapsedControl"]{
top:6px!important;
left:6px!important;
right:auto!important;
width:40px!important;
height:36px!important;
}
[data-testid="stSidebarCollapsedControl"] button{
width:40px!important;
height:36px!important;
min-height:36px!important;
border-radius:10px!important;
}
[data-testid="stSidebarCollapsedControl"] svg{
width:21px!important;
height:21px!important;
}
}

/* Custom API button: always visible on mobile, independent of Streamlit sidebar control. */
.st-key-open_api_panel{
position:fixed!important;
top:8px!important;
left:8px!important;
z-index:1000000!important;
width:44px!important;
height:40px!important;
}
.st-key-open_api_panel .stButton{
width:44px!important;
height:40px!important;
}
.st-key-open_api_panel .stButton>button{
width:44px!important;
height:40px!important;
min-height:40px!important;
padding:0!important;
border-radius:11px!important;
background:#050505!important;
border:1px solid #3f3f46!important;
box-shadow:0 3px 12px rgba(0,0,0,.45)!important;
color:#ffffff!important;
font-size:27px!important;
font-weight:900!important;
line-height:1!important;
}
.st-key-open_api_panel .stButton>button:hover{
background:#111111!important;
border-color:#ffffff!important;
}
@media(max-width:700px){
.st-key-open_api_panel{
top:6px!important;
left:6px!important;
width:42px!important;
height:38px!important;
}
.st-key-open_api_panel .stButton,
.st-key-open_api_panel .stButton>button{
width:42px!important;
height:38px!important;
min-height:38px!important;
}
}

</style>
''', unsafe_allow_html=True)

PISITH='km-KH-PisethNeural'
SREYMOM='km-KH-SreymomNeural'
VOICE_PROFILES={
# Clear, social-media friendly levels. Pitch changes stay small to avoid robotic voices.
'M':{'voice':PISITH,'rate':'-3%','pitch':'+0Hz','volume':'+12%'},
'F':{'voice':SREYMOM,'rate':'-3%','pitch':'+0Hz','volume':'+12%'},
'BOY':{'voice':PISITH,'rate':'-1%','pitch':'+6Hz','volume':'+13%'},
'GIRL':{'voice':SREYMOM,'rate':'-1%','pitch':'+7Hz','volume':'+13%'},
'OLD_M':{'voice':PISITH,'rate':'-7%','pitch':'-5Hz','volume':'+13%'},
'OLD_F':{'voice':SREYMOM,'rate':'-7%','pitch':'-4Hz','volume':'+13%'},
'M_THINK':{'voice':PISITH,'rate':'-6%','pitch':'-2Hz','volume':'+8%'},
'F_THINK':{'voice':SREYMOM,'rate':'-6%','pitch':'-2Hz','volume':'+8%'},
'NARRATOR_M':{'voice':PISITH,'rate':'-4%','pitch':'-1Hz','volume':'+14%'},
'NARRATOR_F':{'voice':SREYMOM,'rate':'-4%','pitch':'-1Hz','volume':'+14%'}
}

TRANSLATE_PROMPT = """You are an expert Chinese-drama Khmer dubbing translator and character continuity editor.
The supplied cue IDs and Whisper timestamps are authoritative and MUST NOT be changed.
Use the uploaded video to identify the visible speaker, voice source, age, gender, narration, and inner thought.

Return a JSON array only. Each object must contain exactly:
{"id": integer, "tag": string, "text": string}

Allowed tags:
M, F, BOY, GIRL, OLD_M, OLD_F, M_THINK, F_THINK, NARRATOR_M, NARRATOR_F

SPEAKER RULES:
- Assign the tag from the person who is actually speaking, not merely the person visible on screen.
- Keep the same recurring character on the same adult/child/elderly and male/female tag across nearby cues.
- Use M or F for ordinary spoken dialogue, including calm and light scenes.
- Use M_THINK or F_THINK only when the line is an unheard inner thought or internal monologue.
- Use NARRATOR tags only for off-screen narration that is not a character thought.
- Use child and elderly tags only when clearly supported by voice and visual context.
- Do not classify a whisper, calm speech, or sad speech as inner thought unless it is not spoken aloud.

KHMER LENGTH RULES:
- Translate into short, natural spoken Khmer, not formal writing and not word-for-word translation.
- Each cue includes MAX_WORDS. The Khmer text MUST stay at or below that word limit.
- Preserve the core meaning, emotion, names, ranks, relationship, and pronouns while removing repetition and filler.
- Prefer one concise spoken sentence. Never add explanations.
- No Chinese characters in the Khmer text.

OUTPUT RULES:
- Return exactly one object for every supplied cue ID in the same order.
- Never invent, merge, split, omit, or renumber cues.
- JSON only. No markdown fences or explanation.
"""

ANALYZE_PROMPT = """You are a Chinese-drama Khmer dubbing continuity editor.
Review the supplied fixed-timestamp cues using the video context.
Return a JSON array only with exactly:
{"id": integer, "tag": string, "text": string}

Allowed tags:
M, F, BOY, GIRL, OLD_M, OLD_F, M_THINK, F_THINK, NARRATOR_M, NARRATOR_F

Rules:
- Return exactly one object per cue ID in the same order.
- Do not alter timestamps, cue count, or cue order.
- Keep recurring character identity and tag consistent across nearby cues.
- Ordinary audible dialogue must remain M or F, even when calm, soft, sad, angry, or whispering.
- Use THINK only for unheard internal monologue; use NARRATOR only for true narration.
- Use BOY/GIRL and OLD_M/OLD_F only when age is clearly supported.
- Rewrite Khmer into concise, natural spoken dialogue.
- Respect each cue's MAX_WORDS strictly so dubbing can play at a normal pace.
- Preserve meaning and emotion but remove repeated, explanatory, or unnecessary words.
- JSON only. No explanations or markdown.
"""

API_COOKIE_NAME = "ai_khemra_bro_private_api"
COOKIE_SECRET_CONFIGURED = False

try:
    raw_cookie_secret = str(st.secrets.get("COOKIE_SECRET", "")).strip()
except Exception:
    raw_cookie_secret = ""

if raw_cookie_secret:
    COOKIE_SECRET_CONFIGURED = True
else:
    # Safe isolation fallback: each live browser session gets a different key.
    # Persistence across a full server restart requires COOKIE_SECRET in Streamlit Secrets.
    if "_temporary_cookie_secret" not in st.session_state:
        st.session_state._temporary_cookie_secret = Fernet.generate_key().decode("utf-8")
    raw_cookie_secret = st.session_state._temporary_cookie_secret

fernet_key = base64.urlsafe_b64encode(hashlib.sha256(raw_cookie_secret.encode("utf-8")).digest())
api_cipher = Fernet(fernet_key)
cookie_manager = stx.CookieManager(key="ai_khemra_private_cookie_manager")


def encrypt_api_keys(api_keys_text):
    cleaned = "\n".join(
        line.strip() for line in api_keys_text.splitlines() if line.strip()
    )
    if not cleaned:
        return ""
    return api_cipher.encrypt(cleaned.encode("utf-8")).decode("utf-8")


def decrypt_api_keys(cookie_value):
    if not cookie_value:
        return ""
    try:
        return api_cipher.decrypt(str(cookie_value).encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError):
        return ""


def load_private_api_keys():
    """Read only this browser/device's encrypted API-key cookie."""
    try:
        return decrypt_api_keys(cookie_manager.get(API_COOKIE_NAME))
    except Exception:
        return ""


def save_private_api_keys(api_keys_text):
    """Save encrypted API keys only in the current browser/device."""
    cleaned = "\n".join(
        line.strip() for line in api_keys_text.splitlines() if line.strip()
    )
    try:
        if cleaned:
            cookie_manager.set(
                API_COOKIE_NAME,
                encrypt_api_keys(cleaned),
                expires_at=datetime.datetime.now() + datetime.timedelta(days=3650),
                key="save_private_api_cookie",
            )
        else:
            cookie_manager.delete(API_COOKIE_NAME, key="delete_private_api_cookie")
    except Exception:
        # Session state still keeps the key private for the active user session.
        pass


def api_keys_changed():
    save_private_api_keys(st.session_state.get("api_keys_manager", ""))


def clear_private_user_session():
    """Remove only the current user's key and working files/state."""
    try:
        cookie_manager.delete(API_COOKIE_NAME, key="logout_private_api_cookie")
    except Exception:
        pass
    for state_key in (
        "api_keys_manager",
        "srt_text",
        "pending_srt",
        "audio_bytes",
        "pending_editor_update",
        "audio_job_pending",
    ):
        if state_key in st.session_state:
            del st.session_state[state_key]


@st.cache_resource(show_spinner=False)
def load_whisper_model():
    # Base + int8 is selected so it can run on Streamlit Community Cloud CPU.
    return WhisperModel("base", device="cpu", compute_type="int8")

if "api_keys_manager" not in st.session_state:
    st.session_state.api_keys_manager = load_private_api_keys()

for key,value in {
    'srt_text':'',
    'pending_srt':'',
    'audio_bytes':None,
    'pending_editor_update':None,
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


def cue_word_limit(start, end):
    """Conservative Khmer spoken-word budget for natural dubbing speed."""
    duration = max(0.35, float(end) - float(start))
    # Roughly 2.0 short Khmer words per second, with a small minimum.
    return max(2, min(18, int(duration * 2.0 + 0.5)))


def khmer_word_count(text):
    return len([part for part in re.split(r"\s+", (text or "").strip()) if part])


def contains_cjk(text):
    return bool(re.search(r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]", text or ""))


def normalize_dialogue(text):
    text = re.sub(r"```|<[^>]+>", "", str(text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def repair_translation_items(client, model_name, uploaded_video, cues, items):
    """Retry only missing or still-Chinese cues until every cue is usable Khmer."""
    by_id = {cue["id"]: cue for cue in cues}
    for _attempt in range(3):
        bad_ids = [
            cue["id"] for cue in cues
            if cue["id"] not in items
            or not normalize_dialogue(items[cue["id"]].get("text"))
            or contains_cjk(items[cue["id"]].get("text"))
        ]
        if not bad_ids:
            return items
        for offset in range(0, len(bad_ids), 12):
            group = [by_id[i] for i in bad_ids[offset:offset + 12]]
            payload = "\n".join(
                f'ID={cue["id"]} | MAX_WORDS={cue_word_limit(cue["start"], cue["end"])} | SOURCE={cue["source"]}'
                for cue in group
            )
            prompt = TRANSLATE_PROMPT + "\nIMPORTANT: These cues failed before. Translate EVERY cue fully into Khmer. Never copy Chinese characters.\n\nCUES:\n" + payload
            contents = [uploaded_video, prompt] if uploaded_video is not None else [prompt]
            response = client.models.generate_content(model=model_name, contents=contents)
            for row in parse_json_array(response.text or ""):
                try:
                    cue_id = int(row.get("id"))
                except (TypeError, ValueError, AttributeError):
                    continue
                if cue_id not in by_id:
                    continue
                tag = str(row.get("tag", "M")).upper().strip()
                if tag not in VOICE_PROFILES:
                    tag = items.get(cue_id, {}).get("tag", "M")
                dialogue = normalize_dialogue(row.get("text"))
                if dialogue and not contains_cjk(dialogue):
                    items[cue_id] = {"tag": tag, "text": dialogue}
    bad_ids = [cue["id"] for cue in cues if cue["id"] not in items or not items[cue["id"]].get("text") or contains_cjk(items[cue["id"]].get("text"))]
    if bad_ids:
        raise RuntimeError(f"AI បកប្រែមិនទាន់អស់។ បន្ទាត់មានបញ្ហា៖ {bad_ids[:20]}")
    return items


def refine_translated_cues(client, model_name, uploaded_video, cues, translated):
    """Second pass for stable character tags and short normal-speed dialogue."""
    refined = {}
    batch_size = 35
    for offset in range(0, len(cues), batch_size):
        batch = cues[offset:offset + batch_size]
        lines = []
        for cue in batch:
            item = translated[cue["id"]]
            lines.append(
                f'ID={cue["id"]} | TIME={seconds_to_srt(cue["start"])} --> '
                f'{seconds_to_srt(cue["end"])} | MAX_WORDS={cue_word_limit(cue["start"], cue["end"])} '
                f'| CURRENT_TAG={item["tag"]} | SOURCE={cue["source"]} | KHMER={item["text"]}'
            )
        response = client.models.generate_content(
            model=model_name,
            contents=[uploaded_video, ANALYZE_PROMPT + "\n\nCUES:\n" + "\n".join(lines)],
        )
        for item in parse_json_array(response.text or ""):
            try:
                cue_id = int(item.get("id"))
            except (TypeError, ValueError, AttributeError):
                continue
            tag = str(item.get("tag", "M")).upper().strip()
            if tag not in VOICE_PROFILES:
                tag = translated.get(cue_id, {}).get("tag", "M")
            dialogue = str(item.get("text", "")).strip()
            if dialogue:
                refined[cue_id] = {"tag": tag, "text": dialogue}

    for cue in cues:
        refined.setdefault(cue["id"], translated[cue["id"]])
    return refined


def translate_cues(client, model_name, uploaded_video, cues):
    result_by_id = {}
    batch_size = 30
    for offset in range(0, len(cues), batch_size):
        batch = cues[offset:offset + batch_size]
        cue_lines = "\n".join(
            f"ID={cue['id']} | {seconds_to_srt(cue['start'])} --> "
            f"{seconds_to_srt(cue['end'])} | MAX_WORDS={cue_word_limit(cue['start'], cue['end'])} "
            f"| SOURCE={cue['source']}"
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

    return repair_translation_items(
        client, model_name, uploaded_video, cues, result_by_id
    )


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
        translated = refine_translated_cues(client, model, uploaded_video, cues, translated)
        translated = repair_translation_items(client, model, uploaded_video, cues, translated)
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
            f'ID={cue["id"]} | TIME={ms_to_srt(cue["start_ms"])} --> {ms_to_srt(cue["end_ms"])} '
            f'| MAX_WORDS={cue_word_limit(cue["start_ms"] / 1000.0, cue["end_ms"] / 1000.0)} '
            f'| TAG={cue["tag"]} | TEXT={cue["text"]}'
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

async def synthesize(text, profile, output_path):
    clean_text = normalize_dialogue(text)
    if not clean_text:
        raise ValueError('មានបន្ទាត់ SRT ទទេ។')
    last_error = None
    attempts = [
        profile,
        {**profile, 'rate': '+0%', 'pitch': '+0Hz', 'volume': '+0%'},
        {'voice': profile.get('voice', PISITH), 'rate': '+0%', 'pitch': '+0Hz', 'volume': '+0%'},
    ]
    for current in attempts:
        try:
            await edge_tts.Communicate(
                text=clean_text, voice=current['voice'], rate=current['rate'],
                pitch=current['pitch'], volume=current['volume']
            ).save(str(output_path))
            if output_path.exists() and output_path.stat().st_size > 500:
                return
        except Exception as exc:
            last_error = exc
            await asyncio.sleep(0.8)
    raise RuntimeError(f'Edge TTS មិនបានផ្ញើសំឡេង៖ {last_error or "unknown error"}')

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
    chinese_rows = [i + 1 for i, cue in enumerate(cues) if contains_cjk(cue['text'])]
    if chinese_rows:
        raise ValueError(f'SRT នៅមានអក្សរចិននៅបន្ទាត់៖ {chinese_rows[:20]}។ សូម Generate SRT ឡើងវិញ។')

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
        final_end_ms = 0
        previous_end_ms = 0

        for index, cue in enumerate(cues):
            slot_seconds = max(0.25, (cue['end'] - cue['start']) / 1000.0)
            audio_seconds = clip_durations[index]

            # Never allow two generated voices to talk over each other.
            # A cue starts at its timestamp, or immediately after the previous
            # voice finishes when the source timestamps overlap.
            start_ms = max(0, cue['start'], previous_end_ms + (40 if index else 0))

            # Fit only moderately. Extreme acceleration sounds robotic.
            speed = audio_seconds / slot_seconds
            tempo = ''
            rendered_seconds = audio_seconds
            if speed > 1.04:
                safe_speed = min(speed, 1.32)
                tempo = atempo_chain(safe_speed)
                rendered_seconds = audio_seconds / safe_speed

            label = f'a{index}'
            parts = [f'[{index}:a]asetpts=PTS-STARTPTS']
            if tempo:
                parts.append(tempo)

            # Normalize every voice clip before mixing so quiet narration and
            # thought voices remain clearly audible.
            parts.extend([
                'highpass=f=70',
                'lowpass=f=14500',
                'loudnorm=I=-16:TP=-2:LRA=7',
                'acompressor=threshold=-20dB:ratio=2.5:attack=8:release=100:makeup=2',
                'afade=t=in:st=0:d=0.025',
                f'afade=t=out:st={max(0.02, rendered_seconds-0.04):.3f}:d=0.04',
                f'adelay={start_ms}|{start_ms}[{label}]',
            ])
            filters.append(','.join(parts).replace('],', ']'))
            labels.append(f'[{label}]')

            previous_end_ms = start_ms + int(rendered_seconds * 1000)
            final_end_ms = max(final_end_ms, previous_end_ms, cue['end'])

        total = (final_end_ms + 350) / 1000.0

        # normalize=0 is crucial: default amix divides volume by the number of
        # subtitle clips and can make a long video almost inaudible.
        filters.append(
            ''.join(labels)
            + f'amix=inputs={len(labels)}:duration=longest:dropout_transition=0:normalize=0,'
              'alimiter=limit=0.92:attack=5:release=50,'
              'loudnorm=I=-14:TP=-1.5:LRA=8,'
              f'apad=whole_dur={total:.3f},atrim=0:{total:.3f}[out]'
        )

        output = root / 'khmer_dubbed.mp3'
        command.extend([
            '-filter_complex', ';'.join(filters),
            '-map', '[out]',
            '-ac', '2',
            '-ar', '48000',
            '-b:a', '192k',
            str(output),
        ])

        result = subprocess.run(command, capture_output=True, text=True, timeout=900)
        if result.returncode != 0:
            raise RuntimeError(result.stderr[-1800:] or 'FFmpeg failed.')
        if not output.exists() or output.stat().st_size < 1000:
            raise RuntimeError('MP3 ត្រូវបានបង្កើត ប៉ុន្តែមិនមានសំឡេងគ្រប់គ្រាន់។')
        return output.read_bytes()


@st.dialog("🔑 Gemini API Key")
def show_api_key_dialog():
    st.caption("API Key នេះរក្សាទុកឯកជនតែលើទូរសព្ទ/Browser របស់អ្នក។")
    st.text_area(
        "បញ្ចូល Gemini API Key",
        height=130,
        placeholder="AIza...",
        key="api_keys_manager",
        on_change=api_keys_changed,
        help="អាចដាក់ API Key មួយ ឬច្រើន ដោយមួយបន្ទាត់មួយសោ។",
    )

    current_keys = [
        line.strip()
        for line in st.session_state.get("api_keys_manager", "").splitlines()
        if line.strip()
    ]

    if current_keys:
        save_private_api_keys(st.session_state.api_keys_manager)
        st.success(f"✅ បានរក្សាទុក {len(current_keys)} API Key សម្រាប់ទូរសព្ទនេះ")
    else:
        st.warning("សូមបញ្ចូល API Key ដើម្បីប្រើការបកប្រែ។")

    if st.button("🚪 លុប API Key ចេញពីទូរសព្ទនេះ", key="dialog_logout"):
        clear_private_user_session()
        st.rerun()


if st.button("»", key="open_api_panel", help="បើកកន្លែងដាក់ API Key"):
    show_api_key_dialog()


with st.sidebar:
    st.markdown(
        '<div class="profile-card">👋 <b>AI KHEMRA BRO</b><br><small>ROLE: ADMIN</small><br><br>🗓️ PLAN: LIFETIME<br>💎 PRO</div>',
        unsafe_allow_html=True,
    )
    if st.button("🚪 ចាកចេញ (Logout)", key="logout"):
        clear_private_user_session()
        st.rerun()

    st.markdown("---")
    st.subheader("🌍 Target Language")
    st.selectbox("ជ្រើសភាសា", ["Khmer (ខ្មែរ)"], key="target_language")

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

api_keys_text = st.session_state.get("api_keys_manager", "")
valid_api_keys = [x.strip() for x in api_keys_text.splitlines() if x.strip()]
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
                    st.error("សូមចុចប៊ូតុង » នៅជ្រុងខាងលើឆ្វេង ហើយបញ្ចូល Gemini API Key ជាមុន។")
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
                        st.success("✅ Khmer SRT ready • ស្លាកតួអង្គស្ថិតស្ថេរ • ឃ្លាខ្លីសម្រាប់សំឡេងធម្មតា")

                    except Exception as exc:
                        st.error(f"❌ {exc}")
                    finally:
                        video_path.unlink(missing_ok=True)

    st.subheader("Generated SRT")
    st.caption("SRT នឹងចូលប្រអប់នេះដោយស្វ័យប្រវត្តិ ពេលដំណើរការដល់ 100%។ អ្នកអាចកែបានមុន Generate MP3។")

    pending_editor_update = st.session_state.pop("pending_editor_update", None)
    if pending_editor_update is not None:
        st.session_state.main_srt_editor = pending_editor_update
        st.session_state.srt_text = pending_editor_update

    if "main_srt_editor" not in st.session_state:
        st.session_state.main_srt_editor = st.session_state.srt_text

    st.text_area(
        "SRT Editor",
        height=360,
        label_visibility="collapsed",
        key="main_srt_editor",
    )
    st.session_state.srt_text = st.session_state.main_srt_editor

    # Keep both SRT action buttons on one row directly below the editor.
    c1, c2 = st.columns(2, gap="small")
    with c1:
        if st.button(
            "🧠 កែស្លាក និងអក្សរ SRT",
            key="analyze_thoughts",
            use_container_width=True,
        ):
            if not st.session_state.srt_text.strip():
                st.warning("សូមបង្កើត ឬបញ្ចូល SRT ជាមុន។")
            elif not api_key:
                st.error("សូមចុចប៊ូតុង » នៅជ្រុងខាងលើឆ្វេង ហើយបញ្ចូល Gemini API Key ជាមុន។")
            else:
                analysis_video_path = None
                try:
                    if uploaded_video is not None:
                        analysis_video_path = save_upload(uploaded_video)
                    with st.spinner("កំពុងរក្សាតួអង្គ កែស្លាកគិតក្នុងចិត្ត និងកាត់ឃ្លាឱ្យខ្លីតាមពេលវេលា…"):
                        analyzed_srt = analyze_inner_thoughts(
                            st.session_state.srt_text,
                            api_key,
                            model,
                            analysis_video_path,
                        )
                    st.session_state.srt_text = analyzed_srt
                    st.session_state.pending_editor_update = analyzed_srt
                    st.session_state.audio_bytes = None
                    st.rerun()
                except Exception as exc:
                    st.error(f"❌ {exc}")
                finally:
                    if analysis_video_path is not None:
                        analysis_video_path.unlink(missing_ok=True)
    with c2:
        if st.session_state.srt_text:
            st.download_button(
                "⬇️ ដោនឡូត SRT",
                st.session_state.srt_text.encode("utf-8"),
                "khmer_story.srt",
                "application/x-subrip",
                use_container_width=True,
            )
        else:
            st.button(
                "⬇️ ដោនឡូត SRT",
                disabled=True,
                key="download_srt_disabled",
                use_container_width=True,
            )

    st.markdown('<div class="section-title">2️⃣ AI Dubbing (Edge TTS Studio)</div>', unsafe_allow_html=True)

    # Use a queued action instead of running the long MP3 task inside the
    # button callback. This prevents mobile Streamlit from temporarily drawing
    # old/duplicate buttons while the page is busy.
    if "audio_job_pending" not in st.session_state:
        st.session_state.audio_job_pending = False

    generate_clicked = st.button(
        "🎙️ Generate Dubbed Audio (MP3)",
        key="generate_audio",
        disabled=st.session_state.audio_job_pending,
    )

    if generate_clicked:
        if not st.session_state.srt_text.strip():
            st.warning("សូមបង្កើត ឬបញ្ចូល SRT ជាមុន។")
        else:
            st.session_state.audio_job_pending = True
            st.rerun()

    if st.session_state.audio_job_pending:
        audio_status = st.status(
            "🎙️ កំពុងបង្កើតសំឡេងខ្មែរ… សូមកុំចុចប៊ូតុងផ្សេង",
            expanded=True,
        )
        try:
            audio_status.write("កំពុងរៀបចំសំឡេងតួអង្គ និងពេលវេលា…")
            st.session_state.audio_bytes = create_mp3(st.session_state.srt_text)
            st.session_state.audio_job_pending = False
            audio_status.update(
                label="✅ បង្កើត MP3 រួចរាល់",
                state="complete",
                expanded=False,
            )
            st.rerun()
        except Exception as exc:
            st.session_state.audio_job_pending = False
            audio_status.update(
                label="❌ បង្កើត MP3 មិនបាន",
                state="error",
                expanded=True,
            )
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
        st.session_state.audio_job_pending = False
        st.session_state.pending_editor_update = ""
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
                st.session_state.pending_editor_update = st.session_state.srt_text
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
