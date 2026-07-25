import asyncio
import base64
import datetime
import hashlib
import hmac
import json
import os
import secrets as pysecrets
import sqlite3
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
  --cyan:#38bdf8;
  --ocean:#0284c7;
  --ocean2:#22d3ee;
  --pink:#38bdf8;
}
.stApp{background:var(--bg);color:var(--text)}
.block-container{max-width:1180px;padding-top:.55rem;padding-bottom:3rem}
[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],
[data-testid="stStatusWidget"],#MainMenu,footer{display:none!important}

.hero{
  border:2px solid var(--ocean2);border-radius:24px;padding:34px 18px;
  text-align:center;background:linear-gradient(145deg,#17171d,#0b1018);
  box-shadow:0 0 24px rgba(34,211,238,.24);margin:0 0 18px;
}
.hero h1{font-size:44px;margin:0 0 8px;font-weight:900;white-space:nowrap;line-height:1.05}
.hero p{margin:0;color:#23c8ef;font-weight:800;letter-spacing:1.5px}
.section-title{font-size:30px;font-weight:900;margin:22px 0 10px}
.ok{background:#073d31;border:1px solid #10b981;border-radius:14px;padding:13px 15px;margin:10px 0}
.side-ok{background:#073d31;border:1px solid #10b981;border-radius:12px;padding:12px;margin:10px 0}
.stButton>button{
  width:100%;min-height:48px;border:0;border-radius:11px;color:white;
  font-weight:850;font-size:15px;background:linear-gradient(90deg,#0284c7,#22d3ee)
}
.stButton>button:hover,.stDownloadButton>button:hover{
  filter:brightness(1.08);transform:translateY(-1px);border-color:#a5f3fc!important;
}
.stDownloadButton>button{width:100%;min-height:46px;border:0!important;border-radius:11px!important;font-weight:850!important;color:white!important;background:linear-gradient(90deg,#0284c7,#22d3ee)!important;box-shadow:0 6px 18px rgba(2,132,199,.22)!important}
.st-key-generate_srt, .st-key-generate_srt > div, .st-key-generate_srt button{width:100%!important;max-width:100%!important;display:block!important;box-sizing:border-box!important}
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
  background:linear-gradient(90deg,#0284c7,#22d3ee)!important;
  border-color:#67e8f9!important;
  color:white!important;
  box-shadow:0 5px 16px rgba(2,132,199,.28)!important;
}
.clear-wrap .stButton>button{
  background:linear-gradient(90deg,#0369a1,#22d3ee);color:#ffffff;font-weight:900
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

/* One locked split control: a single 100% bar divided 50% / 50%. */
html, body, [data-testid="stAppViewContainer"], .stApp{
  overflow-x:hidden!important;
  width:100%!important;
  max-width:100vw!important;
}
.block-container{
  width:100%!important;
  max-width:1180px!important;
  box-sizing:border-box!important;
  overflow-x:hidden!important;
}
.st-key-srt_actions{
  width:100%!important;
  max-width:100%!important;
  overflow:hidden!important;
  margin:8px 0 0!important;
  padding:0!important;
  border-radius:13px!important;
  background:#0ea5e9!important;
  box-sizing:border-box!important;
}
.st-key-srt_actions div[data-testid="stHorizontalBlock"]{
  display:grid!important;
  grid-template-columns:minmax(0,1fr) minmax(0,1fr)!important;
  column-gap:1px!important;
  row-gap:0!important;
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  margin:0!important;
  padding:0!important;
  overflow:hidden!important;
  align-items:stretch!important;
  box-sizing:border-box!important;
}
.st-key-srt_actions div[data-testid="column"],
.st-key-srt_actions div[data-testid="stColumn"]{
  flex:none!important;
  width:100%!important;
  min-width:0!important;
  max-width:100%!important;
  margin:0!important;
  padding:0!important;
  overflow:hidden!important;
  box-sizing:border-box!important;
}
.st-key-srt_actions div[data-testid="column"] > div,
.st-key-srt_actions div[data-testid="stColumn"] > div,
.st-key-srt_actions .stButton,
.st-key-srt_actions .stDownloadButton{
  width:100%!important;
  min-width:0!important;
  max-width:100%!important;
  height:100%!important;
  margin:0!important;
  padding:0!important;
  box-sizing:border-box!important;
}
.st-key-srt_actions button{
  width:100%!important;
  min-width:0!important;
  max-width:100%!important;
  min-height:52px!important;
  height:52px!important;
  margin:0!important;
  padding:5px 3px!important;
  border:0!important;
  border-radius:0!important;
  white-space:nowrap!important;
  overflow:hidden!important;
  text-overflow:ellipsis!important;
  line-height:1.05!important;
  font-size:clamp(10px,3vw,16px)!important;
  box-sizing:border-box!important;
  background:linear-gradient(90deg,#0284c7,#22d3ee)!important;
}
.st-key-srt_actions div[data-testid="column"]:first-child button,
.st-key-srt_actions div[data-testid="stColumn"]:first-child button{
  border-radius:12px 0 0 12px!important;
}
.st-key-srt_actions div[data-testid="column"]:last-child button,
.st-key-srt_actions div[data-testid="stColumn"]:last-child button{
  border-radius:0 12px 12px 0!important;
}
@media(max-width:430px){
  [data-testid="stMainBlockContainer"], .block-container{
    width:100%!important;
    max-width:100%!important;
    min-width:0!important;
    overflow-x:hidden!important;
  }
  .st-key-srt_actions{
    width:100%!important;
    max-width:100%!important;
    min-width:0!important;
  }
  .st-key-srt_actions button{
    height:48px!important;
    min-height:48px!important;
    font-size:11px!important;
    padding:4px 2px!important;
  }
}
@media (orientation:landscape) and (max-height:600px){
  .st-key-srt_actions button{height:46px!important;min-height:46px!important;font-size:12px!important}
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

TRANSLATE_PROMPT = """You are an expert Khmer movie subtitler, Chinese-drama translator, dubbing script writer, and character-continuity editor.
The supplied cue IDs and Whisper timestamps are authoritative and MUST NOT be changed.
Use the uploaded video to identify the actual speaker, voice source, age, gender, social rank, relationship, narration, and inner thought.

Return a JSON array only. Each object must contain exactly:
{"id": integer, "tag": string, "text": string}

Allowed tags:
M, F, BOY, GIRL, OLD_M, OLD_F, M_THINK, F_THINK, NARRATOR_M, NARRATOR_F

SPEAKER AND CHARACTER RULES:
- Assign the tag to the person who is actually speaking, not merely the person visible on screen.
- Keep each recurring character on a consistent gender/age/role tag across nearby cues.
- Use M or F for normal audible dialogue, including calm, sad, angry, soft, romantic, or whispered speech.
- Use M_THINK or F_THINK only for an unheard inner thought or internal monologue.
- Use NARRATOR tags only for true off-screen narration, not for a character's thought.
- Use BOY/GIRL and OLD_M/OLD_F only when the voice or visual context clearly supports it.

PROFESSIONAL KHMER TRANSLATION RULES:
- Translate into natural spoken Khmer used by Cambodian people in real daily conversation.
- Never translate word-for-word and never produce stiff, dry, book-like Khmer.
- Preserve the original meaning, intention, emotion, humor, threat, sarcasm, romance, fear, grief, status, and relationship.
- You may reorder, shorten, combine wording inside the same cue, or add a tiny natural connector when needed, but never change the meaning.
- Choose pronouns and forms of address that fit age, gender, rank, relationship, and scene context, such as: បង/អូន, ខ្ញុំ/លោក, ឯង/អញ, ពួកម៉ាក, សម្លាញ់, លោកគ្រូ, សិស្ស, ព្រះអង្គ, អធិរាជ, ម្ចាស់, មេទ័ព, លោកតា, លោកយាយ.
- Use natural Khmer emotion particles only when suitable, for example: ណា, ណ៎, ចា៎, ចុះ, អញ្ចឹង, ហ្នឹង, មែនទេ, វើយ, ហ្មង, ហាស, អូហ៍.
- Do not overuse slang, insults, or particles. Match the actor's personality and the scene.
- For historical, cultivation, martial-arts, palace, fantasy, or modern-drama terms, choose Khmer wording that viewers understand while keeping names and ranks consistent.
- If a source phrase contains an idiom, joke, hidden meaning, or wordplay, recreate the intended effect naturally in Khmer instead of translating the literal words.
- Do not leave Chinese characters, pinyin, English explanation, translator notes, or brackets inside the Khmer dialogue.

EMOTION AND DUBBING RULES:
- Write each line so that Khmer AI speech sounds smooth, emotional, and easy to pronounce.
- Use punctuation naturally to guide pauses and breathing, but avoid excessive punctuation.
- Make angry lines firm, sad lines gentle, romantic lines warm, fearful lines urgent, and comic lines lively.
- Avoid awkward repeated words, robotic phrasing, and long formal constructions.

SUBTITLE LENGTH RULES:
- Each cue includes MAX_WORDS. The Khmer text MUST stay at or below that word limit.
- Prefer one short, clear spoken sentence per cue.
- Keep the core meaning and emotional force while removing unnecessary repetition and filler.
- Never merge, split, omit, or renumber cues.

OUTPUT RULES:
- Return exactly one object for every supplied cue ID, in the same order.
- Every text value must be fluent Khmer suitable for professional movie subtitles and dubbing.
- JSON only. No markdown fences, headings, comments, or explanation.
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
- Rewrite Khmer into fluent, natural spoken Cambodian dialogue suitable for professional movie dubbing; never use stiff word-for-word phrasing.
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

# Public contact links shown on the login page and inside the app.
FACEBOOK_URL = "https://www.facebook.com/share/1Ehf5Fo8Ma/?mibextid=wwXIfr"
TELEGRAM_URL = "https://t.me/KHEAMRA"
AUTH_COOKIE_NAME = "ai_khemra_bro_access"
ACCESS_DB_PATH = Path(os.getenv("ACCESS_DB_PATH", "data/access_codes.db"))


def _db_connection():
    ACCESS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(ACCESS_DB_PATH), timeout=20)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA busy_timeout=20000")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS access_codes (
            code TEXT PRIMARY KEY,
            note TEXT NOT NULL DEFAULT '',
            created_at INTEGER NOT NULL,
            expires_at INTEGER,
            active INTEGER NOT NULL DEFAULT 1,
            max_devices INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS access_devices (
            code TEXT NOT NULL,
            device_id TEXT NOT NULL,
            first_seen INTEGER NOT NULL,
            last_seen INTEGER NOT NULL,
            PRIMARY KEY (code, device_id),
            FOREIGN KEY(code) REFERENCES access_codes(code) ON DELETE CASCADE
        )
        """
    )
    connection.commit()
    return connection


def _configured_admin():
    try:
        username = str(st.secrets.get("ADMIN_USERNAME", "kheamra")).strip()
        password = str(st.secrets.get("ADMIN_PASSWORD", "Khemra@2026"))
    except Exception:
        username, password = "kheamra", "Khemra@2026"
    return username or "kheamra", password or "Khemra@2026"


def _normalize_access_code(value):
    return re.sub(r"[^A-Z0-9-]", "", str(value or "").upper().strip())


def _new_access_code():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    chunks = ["".join(pysecrets.choice(alphabet) for _ in range(4)) for _ in range(3)]
    return "KHBR-" + "-".join(chunks)


def _create_access_code(days, note, max_devices):
    now = int(time.time())
    expires_at = None if int(days) == 0 else now + int(days) * 86400
    with _db_connection() as db:
        for _ in range(20):
            code = _new_access_code()
            try:
                db.execute(
                    "INSERT INTO access_codes(code,note,created_at,expires_at,active,max_devices) VALUES(?,?,?,?,1,?)",
                    (code, str(note or "").strip(), now, expires_at, max(1, int(max_devices))),
                )
                db.commit()
                return code
            except sqlite3.IntegrityError:
                continue
    raise RuntimeError("មិនអាចបង្កើត Access Code ថ្មីបានទេ។")


def _validate_access_code(code, device_id):
    code = _normalize_access_code(code)
    now = int(time.time())
    if not code or not device_id:
        return False, "Access Code មិនត្រឹមត្រូវ។", None
    with _db_connection() as db:
        row = db.execute("SELECT * FROM access_codes WHERE code=?", (code,)).fetchone()
        if row is None:
            return False, "Access Code មិនត្រឹមត្រូវ។", None
        if not int(row["active"]):
            return False, "Access Code នេះត្រូវបានបិទ។", None
        if row["expires_at"] is not None and int(row["expires_at"]) <= now:
            return False, "Access Code នេះបានផុតកំណត់។", None
        known = db.execute(
            "SELECT 1 FROM access_devices WHERE code=? AND device_id=?",
            (code, device_id),
        ).fetchone()
        if known is None:
            count = db.execute(
                "SELECT COUNT(*) AS total FROM access_devices WHERE code=?", (code,)
            ).fetchone()["total"]
            if int(count) >= int(row["max_devices"]):
                return False, "Access Code នេះបានប្រើដល់ចំនួនឧបករណ៍កំណត់ហើយ។", None
            db.execute(
                "INSERT INTO access_devices(code,device_id,first_seen,last_seen) VALUES(?,?,?,?)",
                (code, device_id, now, now),
            )
        else:
            db.execute(
                "UPDATE access_devices SET last_seen=? WHERE code=? AND device_id=?",
                (now, code, device_id),
            )
        db.commit()
        return True, "", row


def _make_auth_token(code, device_id, expires_at):
    expiry = int(expires_at) if expires_at else int(time.time()) + 3650 * 86400
    payload = {"role": "user", "code": code, "device": device_id, "exp": expiry}
    return api_cipher.encrypt(json.dumps(payload).encode("utf-8")).decode("utf-8")


def _read_auth_token(token):
    if not token:
        return None
    try:
        data = json.loads(api_cipher.decrypt(str(token).encode("utf-8")).decode("utf-8"))
        if data.get("role") != "user" or int(data.get("exp", 0)) <= int(time.time()):
            return None
        valid, _, _ = _validate_access_code(data.get("code"), data.get("device"))
        return data if valid else None
    except Exception:
        return None


def _save_auth_cookie(code, device_id, expires_at):
    try:
        expiry_dt = datetime.datetime.fromtimestamp(int(expires_at)) if expires_at else datetime.datetime.now() + datetime.timedelta(days=3650)
        cookie_manager.set(
            AUTH_COOKIE_NAME,
            _make_auth_token(code, device_id, expires_at),
            expires_at=expiry_dt,
            key="save_access_cookie",
        )
    except Exception:
        pass


def _logout_auth():
    st.session_state.authenticated = False
    st.session_state.pop("access_code", None)
    try:
        cookie_manager.delete(AUTH_COOKIE_NAME, key="delete_access_cookie")
    except Exception:
        pass


def render_contact_buttons(prefix="public"):
    left, right = st.columns(2)
    with left:
        st.link_button("📘 Facebook", FACEBOOK_URL, use_container_width=True)
    with right:
        st.link_button("✈️ Telegram", TELEGRAM_URL, use_container_width=True)


def _format_expiry(timestamp):
    if timestamp is None:
        return "មិនផុតកំណត់"
    return datetime.datetime.fromtimestamp(int(timestamp)).strftime("%Y-%m-%d %H:%M")


def render_admin_panel():
    st.markdown(
        '<div class="hero"><h1>AI KHEMRA BRO</h1><p>ADMIN ACCESS CODE MANAGER</p></div>',
        unsafe_allow_html=True,
    )
    if not st.session_state.get("admin_authenticated"):
        with st.form("admin_login_form"):
            username = st.text_input("Admin Username")
            password = st.text_input("Admin Password", type="password")
            submitted = st.form_submit_button("👑 Admin Login", use_container_width=True)
        if submitted:
            expected_user, expected_password = _configured_admin()
            if hmac.compare_digest(username.strip(), expected_user) and hmac.compare_digest(password, expected_password):
                st.session_state.admin_authenticated = True
                st.rerun()
            st.error("❌ Admin Username ឬ Password មិនត្រឹមត្រូវ។")
        st.link_button("⬅️ ត្រឡប់ទៅ User Login", "?", use_container_width=True)
        st.stop()

    top1, top2 = st.columns(2)
    with top1:
        st.link_button("👤 បើកទំព័រ User", "?", use_container_width=True)
    with top2:
        if st.button("🚪 Admin Logout", use_container_width=True):
            st.session_state.admin_authenticated = False
            st.rerun()

    st.markdown("### ➕ បង្កើត Access Code ថ្មី")
    with st.form("create_access_code_form"):
        duration_label = st.selectbox("រយៈពេល", ["7 ថ្ងៃ", "30 ថ្ងៃ", "90 ថ្ងៃ", "365 ថ្ងៃ", "មិនផុតកំណត់"])
        max_devices = st.number_input("ចំនួនឧបករណ៍អនុញ្ញាត", min_value=1, max_value=20, value=1, step=1)
        note = st.text_input("ឈ្មោះអតិថិជន / កំណត់ចំណាំ")
        create_clicked = st.form_submit_button("🔑 Generate Access Code", use_container_width=True)
    if create_clicked:
        days_map = {"7 ថ្ងៃ": 7, "30 ថ្ងៃ": 30, "90 ថ្ងៃ": 90, "365 ថ្ងៃ": 365, "មិនផុតកំណត់": 0}
        code = _create_access_code(days_map[duration_label], note, max_devices)
        st.session_state.last_created_code = code
    if st.session_state.get("last_created_code"):
        st.success("✅ Access Code ថ្មី")
        st.code(st.session_state.last_created_code, language=None)

    st.markdown("### 👥 បញ្ជី Access Code")
    with _db_connection() as db:
        rows = db.execute(
            """
            SELECT c.*, COUNT(d.device_id) AS devices
            FROM access_codes c
            LEFT JOIN access_devices d ON d.code=c.code
            GROUP BY c.code
            ORDER BY c.created_at DESC
            """
        ).fetchall()
    if not rows:
        st.info("មិនទាន់មាន Access Code ទេ។")
    for row in rows:
        status = "🟢 សកម្ម" if int(row["active"]) else "🔴 បានបិទ"
        expired = row["expires_at"] is not None and int(row["expires_at"]) <= int(time.time())
        if expired:
            status = "⌛ ផុតកំណត់"
        with st.expander(f'{row["code"]} • {status}'):
            st.write(f'**អតិថិជន:** {row["note"] or "—"}')
            st.write(f'**ផុតកំណត់:** {_format_expiry(row["expires_at"])}')
            st.write(f'**ឧបករណ៍:** {row["devices"]}/{row["max_devices"]}')
            c1, c2, c3 = st.columns(3)
            with c1:
                label = "🔒 បិទ" if int(row["active"]) else "🔓 បើក"
                if st.button(label, key=f'toggle_{row["code"]}', use_container_width=True):
                    with _db_connection() as db:
                        db.execute("UPDATE access_codes SET active=? WHERE code=?", (0 if int(row["active"]) else 1, row["code"]))
                        db.commit()
                    st.rerun()
            with c2:
                if st.button("📱 Reset Device", key=f'reset_{row["code"]}', use_container_width=True):
                    with _db_connection() as db:
                        db.execute("DELETE FROM access_devices WHERE code=?", (row["code"],))
                        db.commit()
                    st.rerun()
            with c3:
                if st.button("🗑️ លុប", key=f'delete_{row["code"]}', use_container_width=True):
                    with _db_connection() as db:
                        db.execute("DELETE FROM access_devices WHERE code=?", (row["code"],))
                        db.execute("DELETE FROM access_codes WHERE code=?", (row["code"],))
                        db.commit()
                    st.rerun()
    st.caption("Admin Link: បន្ថែម ?admin=1 នៅខាងចុងលីងកម្មវិធី។")
    st.stop()


def require_login():
    """Require a valid customer access code, or show the admin manager at ?admin=1."""
    try:
        admin_mode = str(st.query_params.get("admin", "")).lower() in {"1", "true", "yes"}
    except Exception:
        admin_mode = False
    if admin_mode:
        render_admin_panel()

    if "device_id" not in st.session_state:
        st.session_state.device_id = pysecrets.token_urlsafe(24)

    if "authenticated" not in st.session_state:
        token_data = None
        try:
            token_data = _read_auth_token(cookie_manager.get(AUTH_COOKIE_NAME))
        except Exception:
            token_data = None
        st.session_state.authenticated = bool(token_data)
        if token_data:
            st.session_state.device_id = token_data["device"]
            st.session_state.access_code = token_data["code"]

    if st.session_state.authenticated:
        valid, _, _ = _validate_access_code(
            st.session_state.get("access_code"), st.session_state.get("device_id")
        )
        if valid:
            return
        _logout_auth()

    st.markdown(
        '<div class="hero"><h1>AI KHEMRA BRO</h1>'
        '<p>GLOBAL AI DUBBING & SUBTITLING WORKSTATION</p>'
        '<div style="margin-top:16px;color:#d8f7ff;font-size:16px;font-weight:700">'
        'ទាក់ទងម្ចាស់កម្មវិធី ដើម្បីទទួល Access Code</div></div>',
        unsafe_allow_html=True,
    )
    render_contact_buttons("login")

    st.markdown('<div class="section-title">🔑 បញ្ចូល Access Code</div>', unsafe_allow_html=True)
    with st.form("access_code_login_form", clear_on_submit=False):
        access_code = st.text_input("Access Code", placeholder="KHBR-XXXX-XXXX-XXXX")
        submitted = st.form_submit_button("ចូលប្រើកម្មវិធី", use_container_width=True)

    if submitted:
        valid, message, row = _validate_access_code(access_code, st.session_state.device_id)
        if valid:
            normalized = _normalize_access_code(access_code)
            st.session_state.authenticated = True
            st.session_state.access_code = normalized
            _save_auth_cookie(normalized, st.session_state.device_id, row["expires_at"])
            st.rerun()
        else:
            st.error(f"❌ {message}")

    st.link_button("👑 Admin", "?admin=1", use_container_width=True)
    st.caption("អ្នកមិនទាន់បញ្ចូល Access Code ត្រឹមត្រូវ មិនអាចប្រើមុខងារបកប្រែ SRT ឬ MP3 បានទេ។")
    st.stop()


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
    'video_uploader_version':0,
    'project_temp_files':[],
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


def optimize_video_for_processing(source_path, output_path):
    """Create a small 480p proxy to reduce server RAM, disk and Gemini upload size."""
    result = subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(source_path),
            "-map", "0:v:0", "-map", "0:a:0?",
            "-vf", "scale='min(480,iw)':-2,fps=12",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "32",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ac", "1", "-ar", "16000", "-b:a", "32k",
            "-movflags", "+faststart",
            str(output_path),
        ],
        capture_output=True,
        text=True,
        timeout=900,
    )
    if result.returncode != 0 or not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError(result.stderr[-1200:] or "មិនអាចបង្រួមវីដេអូបានទេ។")
    return output_path


def extract_audio(video_path, audio_path):
    """Extract compact mono 16 kHz FLAC instead of a large uncompressed WAV."""
    result = subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(video_path),
            "-vn", "-ac", "1", "-ar", "16000",
            "-c:a", "flac", "-compression_level", "8", str(audio_path),
        ],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0 or not audio_path.exists():
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
        folder_path = Path(folder)
        proxy_path = folder_path / "video_proxy_480p.mp4"
        audio_path = folder_path / "audio_16k.flac"

        # Convert the large MP4 into a small processing copy. The original file
        # is used only as a fallback when FFmpeg cannot create the proxy.
        processing_video = Path(video_path)
        try:
            processing_video = optimize_video_for_processing(video_path, proxy_path)
        except Exception:
            processing_video = Path(video_path)

        extract_audio(processing_video, audio_path)
        cues = transcribe_with_whisper(audio_path)
        if not cues:
            raise RuntimeError("Whisper មិនរកឃើញសំឡេងនិយាយក្នុងវីដេអូនេះទេ។")

        last_error = None

        for api_key in api_keys:
            try:
                client = genai.Client(api_key=api_key)
                uploaded_video = upload_for_context(client, processing_video)

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



require_login()

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

        if st.button("🚪 ចាកចេញពីគណនី", key="logout_account", use_container_width=True):
            _logout_auth()
            st.rerun()

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
render_contact_buttons("inside")

tab_video, tab_translate, tab_srt_speech, tab_text_speech = st.tabs(
    ["🎬 Video → SRT", "📝 AI Subtitle Translator", "📜 SRT → Speech", "🎙️ Text → Speech"]
)

with tab_video:
    st.markdown('<div class="section-title">1️⃣ Generate Subtitles (Khmer ខ្មែរ)</div>', unsafe_allow_html=True)

    uploaded_video = st.file_uploader(
        "Upload Video",
        type=["mp4", "mov", "mkv", "webm"],
        help="MP4 ត្រូវបានណែនាំ។ App នឹងបង្រួមវីដេអូទៅ 480p ដោយស្វ័យប្រវត្តិ ដើម្បីកាត់បន្ថយ RAM និងល្បឿនដំណើរការ។",
        key=f"main_video_upload_{st.session_state.video_uploader_version}",
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

            if st.button("📝 Generate Khmer SRT", key="generate_srt", use_container_width=True):
                if not api_key:
                    st.error("សូមចុចប៊ូតុង ☰ នៅជ្រុងខាងលើឆ្វេង បញ្ចូល API Key ហើយចុច «រក្សាទុក»។")
                else:
                    video_path = save_upload(uploaded_video)
                    st.session_state.project_temp_files.append(str(video_path))
                    try:
                        progress_bar = st.progress(1)
                        progress_text = st.empty()
                        started_at = time.time()
                        progress_text.markdown("🎞️ កំពុងបង្រួមវីដេអូសម្រាប់ទាញសំឡេង…")

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

                        # Completion indicators are temporary. Remove them immediately
                        # so the finished SRT editor becomes the only visible result.
                        progress_bar.empty()
                        progress_text.empty()
                        st.rerun()

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

    # Keep both SRT action buttons on one row directly below the editor,
    # including portrait and landscape mobile screens.
    with st.container(key="srt_actions"):
        c1, c2 = st.columns([1, 1], gap=None)
        with c1:
            if st.button(
                "🧠 កែ SRT",
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
                    "⬇️ ទាញ SRT",
                    st.session_state.srt_text.encode("utf-8"),
                    "khmer_story.srt",
                    "application/x-subrip",
                    use_container_width=True,
                )
            else:
                st.button(
                    "⬇️ ទាញ SRT",
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
        # Delete only this user's temporary files. API keys/cookies are kept.
        for temp_name in st.session_state.get("project_temp_files", []):
            try:
                temp_path = Path(temp_name)
                if temp_path.exists() and temp_path.is_file():
                    temp_path.unlink()
            except OSError:
                pass

        st.session_state.project_temp_files = []
        st.session_state.srt_text = ""
        st.session_state.pending_srt = ""
        st.session_state.audio_bytes = None
        st.session_state.audio_job_pending = False
        st.session_state.pending_editor_update = ""
        st.session_state.source_video_stem = "khmer_story"
        st.session_state.mp3_download_name = "khmer_story_dubbed"

        # Give file_uploader a brand-new widget key so the selected video
        # disappears immediately on iPhone, Android and desktop browsers.
        st.session_state.video_uploader_version = (
            int(st.session_state.get("video_uploader_version", 0)) + 1
        )
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
