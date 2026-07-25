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
:root{
  --bg:#080d15;
  --panel:#111827;
  --panel2:#182438;
  --text:#f8fafc;
  --muted:#9ca3af;
  --cyan:#22d3ee;
  --pink:#d900ff;
}
.stApp{background:var(--bg);color:var(--text)}
.block-container{max-width:1180px;padding-top:.55rem;padding-bottom:3rem}
[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],
[data-testid="stStatusWidget"],#MainMenu,footer{display:none!important}

.hero{
  border:2px solid var(--pink);border-radius:24px;padding:34px 18px;
  text-align:center;background:linear-gradient(145deg,#17171d,#0b1018);
  box-shadow:0 0 24px rgba(217,0,255,.22);margin:0 0 18px;
}
.hero h1{font-size:44px;margin:0 0 8px;font-weight:900;white-space:nowrap;line-height:1.05}
.hero p{margin:0;color:#23c8ef;font-weight:800;letter-spacing:1.5px}
.section-title{font-size:30px;font-weight:900;margin:22px 0 10px}
.ok{background:#073d31;border:1px solid #10b981;border-radius:14px;padding:13px 15px;margin:10px 0}
.side-ok{background:#073d31;border:1px solid #10b981;border-radius:12px;padding:12px;margin:10px 0}
.stButton>button{
  width:100%;min-height:48px;border:0;border-radius:11px;color:white;
  font-weight:850;font-size:15px;background:linear-gradient(90deg,#9b1bd1,#ec00ff)
}
.stDownloadButton>button{width:100%;min-height:46px;border-radius:11px;font-weight:800}
div[data-testid="stFileUploader"]{background:#eef2f7;border-radius:12px;padding:8px}
div[data-testid="stTextArea"] textarea{
  background:#182438!important;color:#fff!important;border:1px solid #8290a4!important;
  border-radius:10px!important;font-size:16px!important;line-height:1.65!important;
  font-family:"Noto Sans Khmer","Khmer OS System",Arial,sans-serif!important
}
/* Beautiful mobile tab menu: all 4 tabs stay fully visible. */
div[data-baseweb="tab-list"]{
  gap:8px!important;
  background:#0f1726!important;
  border:1px solid #263349!important;
  border-radius:14px!important;
  padding:7px!important;
  overflow:visible!important;
}
button[data-baseweb="tab"]{
  background:#151f31!important;
  border:1px solid #2b3950!important;
  border-radius:10px!important;
  padding:11px 13px!important;
  min-height:46px!important;
  color:#aeb8c7!important;
  font-weight:800!important;
  justify-content:center!important;
  white-space:normal!important;
  text-align:center!important;
  line-height:1.2!important;
}
button[data-baseweb="tab"][aria-selected="true"]{
  background:linear-gradient(90deg,#a51bd4,#e800ff)!important;
  border-color:#f05cff!important;
  color:white!important;
  box-shadow:0 5px 16px rgba(217,0,255,.24)!important;
}
.clear-wrap .stButton>button{
  background:linear-gradient(90deg,#08bce3,#12d6ef);color:#00141b;font-weight:900
}

/* One stable professional menu button: white 3-line icon on black. */
.st-key-api_menu_container{
  position:fixed!important;top:7px!important;left:7px!important;
  z-index:1000000!important;width:44px!important;
}
.st-key-api_menu_container button{
  width:44px!important;height:40px!important;min-height:40px!important;
  padding:0!important;border-radius:11px!important;background:#050505!important;
  border:1px solid #3f3f46!important;box-shadow:0 3px 12px rgba(0,0,0,.45)!important;
  color:#fff!important;font-size:25px!important;font-weight:900!important;
  line-height:1!important;white-space:nowrap!important;overflow:hidden!important;
}
.st-key-api_menu_container button:hover{
  background:#111!important;border-color:#fff!important
}
div[data-baseweb="popover"]{
  z-index:1000001!important;
}
div[data-baseweb="popover"] [data-testid="stVerticalBlock"]{
  min-width:min(88vw,390px);
}

@media(max-width:700px){
  .block-container{padding-left:.55rem!important;padding-right:.55rem!important;padding-top:.35rem!important}
  .hero{padding:28px 8px 24px!important;border-radius:18px!important;margin-bottom:14px!important}
  .hero h1{font-size:clamp(28px,9vw,42px)!important;letter-spacing:-1px!important}
  .hero p{font-size:clamp(9px,2.7vw,12px)!important;letter-spacing:.8px!important;line-height:1.35!important}
  .section-title{font-size:26px}
  div[data-baseweb="tab-list"]{
    display:grid!important;
    grid-template-columns:repeat(2,minmax(0,1fr))!important;
    width:100%!important;
    gap:7px!important;
    padding:7px!important;
  }
  button[data-baseweb="tab"]{
    width:100%!important;
    min-width:0!important;
    padding:10px 5px!important;
    min-height:50px!important;
    font-size:12px!important;
  }
  button[data-baseweb="tab"] p{
    white-space:normal!important;
    overflow:visible!important;
    text-overflow:clip!important;
    text-align:center!important;
    line-height:1.25!important;
  }
  .st-key-api_menu_container{top:5px!important;left:5px!important;width:42px!important}
  .st-key-api_menu_container button{
    width:42px!important;height:38px!important;min-height:38px!important
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
    # Stable built-in fallback so an encrypted browser cookie can still be
    # decrypted after refresh, browser close, phone restart, app redeploy, or
    # server restart. For production, setting COOKIE_SECRET in Streamlit
    # Secrets remains recommended, but persistence now works out of the box.
    raw_cookie_secret = "AI-KHEMRA-BRO-PERSISTENT-PRIVATE-COOKIE-v1-2026"

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
    """Persist encrypted API keys in this browser/device until Delete is pressed."""
    cleaned = "\n".join(
        line.strip() for line in api_keys_text.splitlines() if line.strip()
    )
    try:
        if cleaned:
            cookie_manager.set(
                API_COOKIE_NAME,
                encrypt_api_keys(cleaned),
                expires_at=datetime.datetime.now() + datetime.timedelta(days=7300),
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

for key,value in {
    'srt_text':'',
    'pending_srt':'',
    'audio_bytes':None,
    'pending_editor_update':None,
    'source_video_stem':'khmer_story',
    'mp3_download_name':'khmer_story_dubbed',
}.items():
    if key not in st.session_state:
        st.session_state[key]=value

def clean_srt(text):
    text=re.sub(r'^```(?:srt)?\s*','',text.strip(),flags=re.I)
    return re.sub(r'\s*```$','',text).strip()

def safe_download_stem(value, fallback='khmer_story_dubbed'):
    """Create a safe, user-editable filename without changing the audio data."""
    name = Path(str(value or '')).stem.strip()
    name = re.sub(r'[\\/:*?"<>|]+', '_', name)
    name = re.sub(r'\s+', ' ', name).strip(' ._-')
    return (name or fallback)[:100]

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


def is_quota_error(exc):
    message = str(exc).upper()
    return (
        "429" in message
        or "RESOURCE_EXHAUSTED" in message
        or "QUOTA" in message
        or "RATE LIMIT" in message
    )


def is_invalid_key_error(exc):
    message = str(exc).upper()
    return (
        "API_KEY_INVALID" in message
        or "INVALID API KEY" in message
        or "API KEY NOT VALID" in message
        or "PERMISSION_DENIED" in message
    )


def friendly_ai_error(exc, key_count=1):
    if is_quota_error(exc):
        if key_count > 1:
            return (
                "Gemini API Keys ដែលបានដាក់សុទ្ធតែដល់កម្រិតប្រើប្រាស់។ "
                "សូមរង់ចាំ quota បើកឡើងវិញ ឬបន្ថែម API Key "
                "ពី Google Cloud Project ផ្សេងក្នុងម៉ឺនុយ ☰។"
            )
        return (
            "Gemini API Key នេះបានដល់កម្រិតប្រើប្រាស់ (429)។ "
            "សូមរង់ចាំ quota បើកឡើងវិញ ឬដាក់ API Key "
            "ពី Google Cloud Project ផ្សេងក្នុងម៉ឺនុយ ☰។"
        )
    if is_invalid_key_error(exc):
        return "Gemini API Key មិនត្រឹមត្រូវ ឬមិនមានសិទ្ធិប្រើ។ សូមដាក់សោថ្មី ហើយចុច «រក្សាទុក»។"
    message = re.sub(r"https?://\\S+", "", str(exc))
    return f"AI មិនអាចបញ្ចប់ការបកប្រែបាន៖ {message[:420]}"


def video_to_srt(video_path, api_keys, model):
    """
    Whisper creates timestamps once.
    Gemini keys rotate automatically when a key has quota/rate-limit problems.
    The normal path uses one translation pass plus targeted repair only,
    reducing Gemini requests compared with the previous three-pass workflow.
    """
    if isinstance(api_keys, str):
        api_keys = [api_keys]
    api_keys = [str(key).strip() for key in api_keys if str(key).strip()]
    if not api_keys:
        raise ValueError("មិនមាន Gemini API Key សម្រាប់ប្រើទេ។")

    with tempfile.TemporaryDirectory() as folder:
        wav_path = Path(folder) / "audio.wav"
        extract_audio(video_path, wav_path)
        cues = transcribe_with_whisper(wav_path)
        if not cues:
            raise RuntimeError("Whisper មិនរកឃើញសំឡេងនិយាយក្នុងវីដេអូនេះទេ។")

        last_error = None

        for api_key in api_keys:
            try:
                client = genai.Client(api_key=api_key)
                uploaded_video = upload_for_context(client, video_path)

                # One main translation pass. translate_cues already repairs
                # missing/Chinese cues, so the old extra full refinement pass
                # is skipped to conserve free-tier requests.
                translated = translate_cues(
                    client, model, uploaded_video, cues
                )
                translated = repair_translation_items(
                    client, model, uploaded_video, cues, translated
                )

                result = build_srt(cues, translated)
                if "-->" not in result:
                    raise RuntimeError("មិនអាចបង្កើត Khmer SRT បានទេ។")
                return result

            except Exception as exc:
                last_error = exc
                if is_quota_error(exc) or is_invalid_key_error(exc):
                    # Try the next API key saved by this user.
                    continue
                raise RuntimeError(friendly_ai_error(exc, len(api_keys))) from exc

        raise RuntimeError(friendly_ai_error(last_error, len(api_keys)))


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


def create_mp3(srt_text, progress_callback=None):
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

        total_cues = len(cues)
        if progress_callback:
            progress_callback(2, "កំពុងរៀបចំសំឡេងតួអង្គ…")

        for index, cue in enumerate(cues):
            clip = root / f'clip_{index:04d}.mp3'
            profile = VOICE_PROFILES.get(cue['tag'], VOICE_PROFILES['M'])
            run_async(synthesize(cue['text'], profile, clip))
            clips.append(clip)
            clip_durations.append(probe_audio_duration(clip))
            if progress_callback:
                percent = 5 + int(((index + 1) / total_cues) * 82)
                progress_callback(
                    min(percent, 87),
                    f"កំពុងបង្កើតសំឡេងខ្មែរ {index + 1}/{total_cues}…",
                )

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

        if progress_callback:
            progress_callback(92, "កំពុងបញ្ចូលសំឡេងទាំងអស់ជាបទ MP3 តែមួយ…")

        result = subprocess.run(command, capture_output=True, text=True, timeout=900)
        if result.returncode != 0:
            raise RuntimeError(result.stderr[-1800:] or 'FFmpeg failed.')
        if not output.exists() or output.stat().st_size < 1000:
            raise RuntimeError('MP3 ត្រូវបានបង្កើត ប៉ុន្តែមិនមានសំឡេងគ្រប់គ្រាន់។')
        if progress_callback:
            progress_callback(100, "បង្កើត MP3 រួចរាល់")
        return output.read_bytes()



# Read this browser's saved key once per Streamlit session.
if "api_keys_manager" not in st.session_state:
    st.session_state.api_keys_manager = load_private_api_keys()

# Defaults are per user/session; no user's working data is shared with another.
for state_key, default_value in {
    "target_language": "Khmer (ខ្មែរ)",
    "translation_style": "🔴 Chinese Drama Pro",
    "model_selector": "gemini-2.5-flash",
    "lite_mode": True,
    "api_saved_notice": False,
}.items():
    if state_key not in st.session_state:
        st.session_state[state_key] = default_value

with st.container(key="api_menu_container"):
    with st.popover("☰", help="API Key និងការកំណត់កម្មវិធី"):
        st.markdown("### 🔑 API Key និងការកំណត់")
        st.caption("ទូរសព្ទ/Browser នីមួយៗមាន API Key និងឯកសារផ្ទាល់ខ្លួន។")

        st.text_area(
            "Gemini API Key",
            height=120,
            placeholder="AIza...",
            key="api_keys_manager",
            help="អាចដាក់ច្រើនសោ ដោយមួយបន្ទាត់មួយសោ។ បើសោមួយ quota ពេញ App នឹងសាកសោបន្ទាប់។",
        )

        save_col, logout_col = st.columns(2)
        with save_col:
            if st.button("💾 រក្សាទុក", key="save_api_keys", use_container_width=True):
                entered_keys = [
                    line.strip()
                    for line in st.session_state.api_keys_manager.splitlines()
                    if line.strip()
                ]
                if entered_keys:
                    save_private_api_keys(st.session_state.api_keys_manager)
                    st.session_state.api_saved_notice = True
                    st.rerun()
                else:
                    st.warning("សូមបញ្ចូល API Key ជាមុន។")

        with logout_col:
            if st.button("🗑️ លុបសោ", key="remove_api_keys", use_container_width=True):
                clear_private_user_session()
                st.rerun()

        current_keys = [
            line.strip()
            for line in st.session_state.get("api_keys_manager", "").splitlines()
            if line.strip()
        ]
        if current_keys:
            st.success(f"✅ API Key ត្រៀមប្រើ៖ {len(current_keys)} • Auto rotation")
            st.caption("🔒 បានអ៊ិនគ្រីប និងរក្សាទុកជាប់សម្រាប់ Browser/ទូរសព្ទនេះ។ សោនឹងបាត់តែពេលអ្នកចុច «លុបសោ» ឬលុបទិន្នន័យ Browser ដោយខ្លួនឯង។")
        else:
            st.info("បញ្ចូល API Key រួចចុច «រក្សាទុក»។")

        st.divider()
        st.selectbox("🌍 Target Language", ["Khmer (ខ្មែរ)"], key="target_language")
        st.radio(
            "🎭 Translation Style",
            ["🔴 Chinese Drama Pro", "⚪ Whisper Timestamp Sync", "⚪ Standard"],
            key="translation_style",
        )
        st.selectbox(
            "🤖 Model",
            ["gemini-2.5-flash", "gemini-2.5-pro"],
            key="model_selector",
        )
        st.toggle("📶 4G Lite Mode", key="lite_mode")

api_keys_text = st.session_state.get("api_keys_manager", "")
valid_api_keys = [line.strip() for line in api_keys_text.splitlines() if line.strip()]
api_key = valid_api_keys[0] if valid_api_keys else ""
translation_style = st.session_state.translation_style
model = st.session_state.model_selector
lite_mode = st.session_state.lite_mode
max_mb = 60 if lite_mode else 150

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
        source_stem = safe_download_stem(Path(uploaded_video.name).stem, 'khmer_story')
        st.session_state.source_video_stem = source_stem
        if not st.session_state.get('mp3_download_name') or st.session_state.get('mp3_download_name') == 'khmer_story_dubbed':
            st.session_state.mp3_download_name = f"{source_stem}_khmer"

        # Keep the uploaded filename and file size private on-screen.
        # The file is still available internally for validation and processing.
        size_mb = uploaded_video.size / (1024 * 1024)

        if size_mb > max_mb:
            st.error(f"សូមបង្រួមវីដេអូឱ្យតិចជាង {max_mb} MB។")
        else:
            if not lite_mode and st.checkbox("▶️ Video Preview"):
                st.video(uploaded_video)

            if st.button("📝 Generate Khmer SRT", key="generate_srt"):
                if not api_key:
                    st.error("សូមចុចប៊ូតុង ☰ នៅជ្រុងខាងលើឆ្វេង បញ្ចូល API Key ហើយចុច «រក្សាទុក»។")
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
                                valid_api_keys,
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
                        progress_bar.empty()
                        progress_text.empty()
                        st.error(f"❌ {friendly_ai_error(exc, len(valid_api_keys))}")
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
                st.error("សូមចុចប៊ូតុង ☰ នៅជ្រុងខាងលើឆ្វេង បញ្ចូល API Key ហើយចុច «រក្សាទុក»។")
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

    # Before completion, show only the Generate button. After completion,
    # remove the progress/result messages and replace them with filename + Download.
    if not st.session_state.audio_bytes:
        generate_clicked = st.button(
            "🎙️ Generate Dubbed Audio (MP3)",
            key="generate_audio",
            use_container_width=False,
        )

        if generate_clicked:
            if not st.session_state.srt_text.strip():
                st.warning("សូមបង្កើត ឬបញ្ចូល SRT ជាមុន។")
            else:
                progress_bar = st.progress(0)
                progress_text = st.empty()
                started_at = time.monotonic()

                def update_audio_progress(percent, message):
                    elapsed = max(0, int(time.monotonic() - started_at))
                    minutes, seconds = divmod(elapsed, 60)
                    progress_bar.progress(max(0, min(100, int(percent))))
                    progress_text.markdown(
                        f"### ⏱️ {int(percent)}% • {minutes:02d}:{seconds:02d}<br>{message}",
                        unsafe_allow_html=True,
                    )

                try:
                    update_audio_progress(1, "កំពុងចាប់ផ្ដើមបង្កើតសំឡេង…")
                    st.session_state.audio_bytes = create_mp3(
                        st.session_state.srt_text,
                        progress_callback=update_audio_progress,
                    )
                    # Clear the processing display immediately after completion.
                    progress_bar.empty()
                    progress_text.empty()
                    if not st.session_state.get("mp3_download_name"):
                        stem = st.session_state.get("source_video_stem", "khmer_story")
                        st.session_state.mp3_download_name = f"{stem}_khmer"
                    st.rerun()
                except Exception as exc:
                    progress_bar.empty()
                    progress_text.empty()
                    st.error(f"❌ បង្កើត MP3 មិនបាន៖ {exc}")
    else:
        st.text_input(
            "✏️ ឈ្មោះឯកសារ MP3",
            key="mp3_download_name",
            placeholder="ឧទាហរណ៍៖ រឿងភាគទី១_សំឡេងខ្មែរ",
            help="អ្នកអាចកែឈ្មោះឯកសារមុនចុច Download។",
        )
        st.audio(st.session_state.audio_bytes, format="audio/mp3")
        download_stem = safe_download_stem(
            st.session_state.get("mp3_download_name"),
            fallback="khmer_story_dubbed",
        )
        st.download_button(
            "⬇️ ទាញយកសំឡេង MP3",
            st.session_state.audio_bytes,
            f"{download_stem}.mp3",
            "audio/mpeg",
            use_container_width=True,
        )

    st.markdown('<div class="clear-wrap">', unsafe_allow_html=True)
    if st.button("🗑️ សម្អាត (Clear Video Project)", key="clear_project"):
        st.session_state.srt_text = ""
        st.session_state.pending_srt = ""
        st.session_state.audio_bytes = None
        st.session_state.audio_job_pending = False
        st.session_state.pending_editor_update = ""
        st.session_state.source_video_stem = "khmer_story"
        st.session_state.mp3_download_name = "khmer_story_dubbed"
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
            st.error("សូមចុចប៊ូតុង ☰ បញ្ចូល API Key ហើយចុច «រក្សាទុក»។")
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
