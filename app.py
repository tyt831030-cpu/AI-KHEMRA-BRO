import asyncio
import base64
import datetime
import hashlib
import hmac
import re
import secrets
import sqlite3
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import edge_tts
import extra_streamlit_components as stx
import streamlit as st
from cryptography.fernet import Fernet, InvalidToken
from google import genai
from faster_whisper import WhisperModel

APP_VERSION = "6.2"

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

/* Discreet owner trigger. It looks like a decorative UI element. */
.st-key-owner_trigger_container{
  position:fixed!important;top:8px!important;right:8px!important;
  z-index:1000000!important;width:42px!important;
}
.st-key-owner_trigger_container button{
  width:42px!important;height:38px!important;min-height:38px!important;
  padding:0!important;border-radius:12px!important;
  background:rgba(8,13,21,.82)!important;border:1px solid #203247!important;
  color:#38bdf8!important;font-size:19px!important;line-height:1!important;
  box-shadow:0 3px 14px rgba(0,0,0,.38)!important;
}
.st-key-owner_trigger_container button:hover{
  background:#0f172a!important;border-color:#22d3ee!important;
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


/* ───────────── Login screen v3.0 — mobile layout matching the approved sample ───────────── */
.st-key-public_login_wrap{
  width:min(100%,760px)!important;
  margin:0 auto!important;
}
.st-key-public_login_wrap [data-testid="stMarkdownContainer"] h3{
  color:#ffc400!important;
  font-size:clamp(28px,7vw,43px)!important;
  font-weight:950!important;
  margin:18px 0 12px!important;
  line-height:1.2!important;
}
.st-key-customer_login_box{
  border:1px solid #1f2937!important;
  border-radius:16px!important;
  padding:18px 20px 16px!important;
  background:rgba(7,12,20,.42)!important;
}
.st-key-customer_login_box label,
.st-key-customer_login_box label p{
  color:#ffb000!important;
  font-weight:850!important;
  font-size:17px!important;
}
.st-key-customer_login_box input{
  min-height:58px!important;
  border-radius:12px!important;
  background:#f3f4f6!important;
  color:#20242e!important;
  border:1px solid #d1d5db!important;
  font-size:18px!important;
}
.st-key-customer_login_box input::placeholder{
  color:#8b8f99!important;
  opacity:1!important;
}
.st-key-customer_login_box [data-testid="stFormSubmitButton"] button{
  min-height:58px!important;
  margin-top:10px!important;
  border-radius:12px!important;
  border:1px solid #ffd84d!important;
  background:linear-gradient(90deg,#ffab00 0%,#ffd600 100%)!important;
  color:#ffffff!important;
  font-weight:950!important;
  font-size:18px!important;
  text-shadow:0 1px 2px rgba(0,0,0,.28)!important;
  box-shadow:0 8px 22px rgba(255,179,0,.20)!important;
}
.st-key-customer_login_box [data-testid="stFormSubmitButton"] button p{
  color:#ffffff!important;
  font-weight:950!important;
}
.social-split{
  width:100%;
  display:grid;
  grid-template-columns:minmax(0,1fr) minmax(0,1fr);
  gap:1px;
  padding:7px;
  margin:12px 0 0;
  border:2px solid #f5b400;
  border-radius:16px;
  overflow:hidden;
  background:#f5b400;
  box-sizing:border-box;
}
.social-split a{
  min-width:0;
  min-height:76px;
  display:flex;
  align-items:center;
  justify-content:center;
  gap:12px;
  color:#fff!important;
  text-decoration:none!important;
  font-size:clamp(16px,4vw,25px);
  font-weight:900;
  line-height:1;
  box-sizing:border-box;
  -webkit-tap-highlight-color:transparent;
}
.social-split a:first-child{
  border-radius:10px 0 0 10px;
  background:linear-gradient(135deg,#1265e8,#2f8df5);
}
.social-split a:last-child{
  border-radius:0 10px 10px 0;
  background:linear-gradient(135deg,#1aaee8,#36c9ef);
}
.social-split a:active{filter:brightness(.92);transform:scale(.995)}
.social-icon{
  width:42px;height:42px;flex:0 0 42px;
  display:inline-flex;align-items:center;justify-content:center;
  border-radius:50%;background:#fff;color:#1877f2;
  font-size:29px;font-weight:950;font-family:Arial,sans-serif;
}
.social-split a:last-child .social-icon{
  color:#229ed9;font-size:24px;transform:rotate(-8deg);
}
.login-help{
  margin:20px 2px 0;
  color:#a7adb7;
  font-size:clamp(15px,3.8vw,20px);
  line-height:1.65;
}
.login-help strong{color:#ffc400}
@media(max-width:700px){
  .st-key-public_login_wrap{width:100%!important}
  .st-key-customer_login_box{padding:16px 14px 14px!important}
  .social-split{padding:5px;border-radius:14px}
  .social-split a{min-height:64px;gap:8px}
  .social-icon{width:37px;height:37px;flex-basis:37px;font-size:25px}
}

</style>
''', unsafe_allow_html=True)

PISITH='km-KH-PisethNeural'
SREYMOM='km-KH-SreymomNeural'
VOICE_PROFILES={
# Warm, natural profiles. Large pitch boosts make Khmer Neural voices thin/airy,
# so age differences use mostly rate and only a very small pitch movement.
'BOY':{'voice':PISITH,'rate':'+4%','pitch':'+2Hz','volume':'+5%'},
'GIRL':{'voice':SREYMOM,'rate':'+4%','pitch':'+3Hz','volume':'+5%'},
'M_YOUNG':{'voice':PISITH,'rate':'+1%','pitch':'+0Hz','volume':'+6%'},
'F_YOUNG':{'voice':SREYMOM,'rate':'+1%','pitch':'+1Hz','volume':'+6%'},
'M_ADULT':{'voice':PISITH,'rate':'-3%','pitch':'-3Hz','volume':'+7%'},
'F_ADULT':{'voice':SREYMOM,'rate':'-2%','pitch':'-1Hz','volume':'+7%'},
'M_OLD':{'voice':PISITH,'rate':'-11%','pitch':'-8Hz','volume':'+8%'},
'F_OLD':{'voice':SREYMOM,'rate':'-10%','pitch':'-6Hz','volume':'+8%'},
'M_THINK':{'voice':PISITH,'rate':'-7%','pitch':'-4Hz','volume':'+5%'},
'F_THINK':{'voice':SREYMOM,'rate':'-7%','pitch':'-3Hz','volume':'+5%'},
'NARRATOR_M':{'voice':PISITH,'rate':'-7%','pitch':'-6Hz','volume':'+8%'},
'NARRATOR_F':{'voice':SREYMOM,'rate':'-6%','pitch':'-4Hz','volume':'+8%'},
# Backward-compatible labels for older SRT files.
'M':{'voice':PISITH,'rate':'-3%','pitch':'-2Hz','volume':'+7%'},
'F':{'voice':SREYMOM,'rate':'-3%','pitch':'-1Hz','volume':'+7%'},
'OLD_M':{'voice':PISITH,'rate':'-8%','pitch':'-5Hz','volume':'+8%'},
'OLD_F':{'voice':SREYMOM,'rate':'-8%','pitch':'-3Hz','volume':'+8%'}
}

# Smooth-dubbing controls: gentle fades remove clicks/cuts when speaker labels change.
VOICE_FADE_IN_SECONDS = 0.045
VOICE_FADE_OUT_SECONDS = 0.070
MIN_VOICE_GAP_MS = 12
MAX_TEMPO_SPEED = 1.65

TRANSLATE_PROMPT = """You are an expert Khmer movie subtitler, Chinese-drama translator, dubbing script writer, and character-continuity editor.
The supplied cue IDs and Whisper timestamps are authoritative and MUST NOT be changed.
Use the uploaded video to identify the actual speaker, voice source, age, gender, social rank, relationship, narration, and inner thought.

Return a JSON array only. Each object must contain exactly:
{"id": integer, "tag": string, "text": string}

Allowed tags:
BOY, GIRL, M_YOUNG, F_YOUNG, M_ADULT, F_ADULT, M_OLD, F_OLD, M_THINK, F_THINK, NARRATOR_M, NARRATOR_F

SPEAKER AND CHARACTER RULES:
- Assign the tag to the person who is actually speaking, not merely the person visible on screen.
- Dialogue from a distant, off-camera, quiet, echoing, or partially covered speaker is still real dialogue. Translate it normally and completely; never shorten or omit it merely because the speaker sounds far away.
- Do not change meaning, pronouns, or speaker identity because a voice is louder, quieter, nearer, farther, muffled, or reverberant.
- Keep each recurring character on a consistent gender/age/role tag across nearby cues. Never switch a character's label merely because the emotion, volume, camera angle, or speaking style changes.
- Before assigning a new tag, compare with the preceding and following cues. Change the tag only when the actual speaker changes or clear video/audio evidence proves a different age/gender/role.
- Use BOY/GIRL for children, M_YOUNG/F_YOUNG for teenagers or young adults, M_ADULT/F_ADULT for ordinary adults, and M_OLD/F_OLD for elderly speakers.
- Choose age from the actual voice and visible character context; do not guess an elderly or child label from clothing alone.
- Use M_THINK or F_THINK only for an unheard inner thought or internal monologue.
- Use NARRATOR tags only for true off-screen narration, not for a character's thought.
- Use BOY/GIRL and M_OLD/F_OLD only when age is clearly supported; otherwise prefer M_YOUNG/F_YOUNG or M_ADULT/F_ADULT.

PROFESSIONAL KHMER TRANSLATION RULES:
- Translate into smooth, natural spoken Khmer that Cambodian people actually use in everyday conversation and movie dialogue.
- Never translate word-for-word. First understand the whole meaning, situation, relationship, and emotion, then rewrite it naturally in Khmer.
- Avoid formal, book-like, bureaucratic, robotic, dry, or machine-translated Khmer unless the character and scene truly require formal speech.
- Prefer short, familiar, easy-to-understand Khmer expressions. The sentence should sound natural when spoken aloud, not merely look grammatically correct in writing.
- Preserve the original meaning, intention, emotion, humor, threat, sarcasm, romance, fear, grief, status, and relationship.
- You may reorder wording inside the same cue and replace unnatural literal phrases with familiar Khmer speech, but you MUST preserve every audible idea, response, interjection, negation, name, number, command, and emotional particle. Never invent information or change the meaning.
- Do NOT delete short words, filler sounds, reactions, repeated words, names, negations, or tiny replies when they are audible in the source. Translate natural reactions such as 嗯, 啊, 哦, 喂, 哎, 好, 不, 是, 什么 into suitable spoken Khmer such as អឺ, អា៎, អូ, ហេ៎, អុញ, បាន, ទេ, មែន, អី—according to context.
- Use conversational sentence order and natural responses such as “អញ្ចឹងមែន?”, “បានហើយ”, “មិនអីទេ”, “តើមានរឿងអី?”, or similar only when they accurately match the source meaning and scene.
- Choose pronouns and forms of address that fit age, gender, rank, relationship, and scene context, such as: បង/អូន, ខ្ញុំ/លោក, ឯង/អញ, ពួកម៉ាក, សម្លាញ់, លោកគ្រូ, សិស្ស, ព្រះអង្គ, អធិរាជ, ម្ចាស់, មេទ័ព, លោកតា, លោកយាយ.
- Use natural Khmer emotion particles only when suitable, for example: ណា, ណ៎, ចា៎, ចុះ, អញ្ចឹង, ហ្នឹង, មែនទេ, វើយ, ហ្មង, ហាស, អូហ៍.
- FACEBOOK-SAFE LANGUAGE MODE IS ALWAYS ON: do not output profanity, obscene expressions, sexual insults, degrading slurs, hateful language, direct humiliation, or unnecessarily graphic wording.
- When the source contains rude or offensive speech, keep the intention and emotion but replace it with a clean, natural Khmer expression suitable for a general Facebook audience. For example, use context-appropriate clean phrases such as «មនុស្សអាក្រក់», «ឈប់និយាយទៅ», «កុំធ្វើបែបនេះ», «គួរឱ្យខឹងមែន», or «ចេញទៅ» instead of reproducing vulgar wording.
- Do not sanitize so aggressively that the plot meaning disappears. Preserve whether the speaker is angry, threatening, mocking, shocked, or rejecting someone, but express it without offensive vocabulary.
- Never create insults that were not present in the source. Never target protected characteristics, disability, appearance, family members, or private sexual matters.
- Do not overuse slang, insults, or particles. Match the actor's personality and the scene while keeping the wording clean enough for a broad Facebook audience.
- For historical, cultivation, martial-arts, palace, fantasy, or modern-drama terms, choose Khmer wording that viewers understand while keeping names and ranks consistent.
- If a source phrase contains an idiom, joke, hidden meaning, or wordplay, recreate the intended effect naturally in Khmer instead of translating the literal words.
- Do not leave Chinese characters, pinyin, English explanation, translator notes, or brackets inside the Khmer dialogue.

EMOTION AND DUBBING RULES:
- Write each line so that Khmer AI speech sounds smooth, emotional, and easy to pronounce.
- Use punctuation naturally to guide pauses, breathing, and rising/falling intonation, but avoid excessive punctuation.
- End questions with ? and emotional exclamations with ! only when justified; use Khmer commas or ellipses sparingly for gentle pauses so TTS does not sound flat or abruptly cut.
- Make angry lines firm, sad lines gentle, romantic lines warm, fearful lines urgent, and comic lines lively.
- Avoid awkward repeated words, robotic phrasing, and long formal constructions.

KHMER DUBBING QUALITY RULES:
- Translate as if you are writing dialogue for a professional Khmer TV dubbing studio.
- Every sentence must sound like a real Cambodian person speaking naturally.
- Prefer intended meaning and emotion over literal wording.
- Rewrite sentence structure whenever necessary so it flows naturally in Khmer.
- Keep emotion and character continuity flowing from one subtitle to the next.
- Never produce robotic, dry, textbook, or machine-translated Khmer.
- Use familiar daily Khmer expressions only when they fit the character and situation.
- If the source is emotional, make the Khmer line emotionally convincing without changing its meaning.
- Avoid repeating the same words in consecutive subtitles unless the repetition is intentional.
- If a direct translation sounds unnatural, reshape it into natural Khmer conversation.
- Make every subtitle easy for Khmer AI voices to pronounce with natural rhythm and breathing.
- The final dialogue should sound as if it was originally written and performed in Khmer.
- Before returning each subtitle, silently ask: “Would a Cambodian naturally say this in a real conversation or movie?” If not, rewrite it.

STRICT TIMING AND SUBTITLE LENGTH RULES:
- The supplied start and end timestamp of every cue is locked. Never move dialogue earlier or later, never borrow time from another cue, and never merge or split cues.
- Each cue includes MAX_WORDS. The Khmer text MUST stay at or below that word limit so the generated voice can finish inside its own timestamp.
- Start speaking at the cue start and finish before the cue end. Do not let one character's voice overlap the next cue unless the original timestamps themselves overlap.
- Shorten only by choosing concise natural Khmer wording; never delete a meaning-bearing word, negation, name, number, command, response, or audible reaction.
- Cut and reshape the translation so it fits the subtitle time and can be spoken comfortably before the cue ends.
- Prefer one short, clear, natural spoken sentence per cue.
- Keep the complete meaning and emotional force. Never remove an audible word merely because it is short, repeated, a filler, a reaction, or difficult to fit. Use concise Khmer wording while preserving it.
- Do not make a line unnaturally incomplete merely to shorten it; choose a shorter natural Khmer expression instead.
- Never merge, split, omit, summarize away, or renumber cues. Every supplied cue must contain spoken Khmer text unless the source cue is truly silent/non-speech.

MANDATORY NO-SKIP RULES:
- Translate 100% of the audible speech in every cue, including one-word replies and tiny sounds.
- Never return an empty text value for a cue containing speech.
- Preserve negatives such as “not/no/don’t”, names, numbers, titles, greetings, calls, sighs, surprise, agreement, disagreement, and repeated emphasis.
- Do not summarize two clauses into one if that removes information.
- If the source is very short, return a correspondingly short Khmer utterance rather than deleting it.
- Recheck each cue against SOURCE before output: every audible element must be represented in Khmer.
- Final safety check for every cue: remove or rewrite any vulgar, obscene, hateful, sexually insulting, or degrading word into clean natural Khmer while preserving the scene's meaning and emotion.
- Final timing check for every cue: wording must be speakable within that cue's exact duration without rushing, dragging, starting early, or finishing late.

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
BOY, GIRL, M_YOUNG, F_YOUNG, M_ADULT, F_ADULT, M_OLD, F_OLD, M_THINK, F_THINK, NARRATOR_M, NARRATOR_F

Rules:
- Return exactly one object per cue ID in the same order.
- Do not alter timestamps, cue count, or cue order.
- Keep recurring character identity and tag consistent across nearby cues.
- Ordinary audible dialogue must use the correct age-and-gender label, even when calm, soft, sad, angry, or whispering.
- Use THINK only for unheard internal monologue; use NARRATOR only for true narration.
- Use BOY/GIRL and M_OLD/F_OLD only when age is clearly supported; use M_YOUNG/F_YOUNG for young speakers and M_ADULT/F_ADULT for adults.
- Rewrite Khmer into fluent, natural everyday Cambodian dialogue suitable for professional movie dubbing; never use stiff word-for-word or book-like phrasing.
- Read each Khmer line as spoken dialogue: if a Cambodian would not normally say it that way, rewrite it using shorter and more familiar wording.
- Respect each cue's MAX_WORDS strictly so dubbing can play at a normal pace.
- Preserve every spoken meaning, including short replies, particles, hesitation sounds, repeated words, names, negations, and small expressions. Never delete a cue or omit a spoken word merely to shorten it; shorten only by natural Khmer rephrasing without information loss.
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


def _current_customer_code():
    """Return the authenticated customer's normalized access code."""
    try:
        return normalize_access_code(st.session_state.get("customer_code", ""))
    except Exception:
        return str(st.session_state.get("customer_code", "") or "").strip().upper()


def _load_api_keys_from_account():
    """Load encrypted API keys from the persistent customer account database."""
    code = _current_customer_code()
    if not code:
        return ""
    try:
        with license_connection() as connection:
            row = connection.execute(
                "SELECT saved_api_keys_encrypted FROM licenses "
                "WHERE access_code_hash=? OR access_code_display=?",
                (_hash_code(code), code),
            ).fetchone()
        if not row:
            return ""
        return decrypt_api_keys(row["saved_api_keys_encrypted"] or "")
    except Exception:
        return ""


def _save_api_keys_to_account(api_keys_text):
    """Save encrypted API keys against the signed-in account, not only Safari."""
    code = _current_customer_code()
    if not code:
        return False
    cleaned = "\n".join(
        line.strip() for line in str(api_keys_text or "").splitlines() if line.strip()
    )
    encrypted = encrypt_api_keys(cleaned) if cleaned else ""
    try:
        with license_connection() as connection:
            connection.execute(
                "UPDATE licenses SET saved_api_keys_encrypted=? "
                "WHERE access_code_hash=? OR access_code_display=?",
                (encrypted, _hash_code(code), code),
            )
            connection.commit()
        return True
    except Exception:
        return False


def load_private_api_keys():
    """Load from the account database first; Safari cookie is only a fallback."""
    account_keys = _load_api_keys_from_account()
    if account_keys:
        return account_keys
    try:
        browser_keys = decrypt_api_keys(cookie_manager.get(API_COOKIE_NAME))
    except Exception:
        browser_keys = ""
    # Migrate an old browser-only saved key into the signed-in account.
    if browser_keys:
        _save_api_keys_to_account(browser_keys)
    return browser_keys


def save_private_api_keys(api_keys_text):
    """Persist keys in the customer account DB and also keep a browser fallback."""
    cleaned = "\n".join(
        line.strip() for line in str(api_keys_text or "").splitlines() if line.strip()
    )
    saved_to_account = _save_api_keys_to_account(cleaned)
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
        pass
    return saved_to_account


def delete_private_api_keys():
    """Delete the key only when the user explicitly presses Delete Key."""
    _save_api_keys_to_account("")
    try:
        cookie_manager.delete(API_COOKIE_NAME, key="delete_private_api_cookie_explicit")
    except Exception:
        pass

def api_keys_changed():
    save_private_api_keys(st.session_state.get("api_keys_manager", ""))


def clear_private_user_session(delete_saved_api=False):
    """Clear temporary work. Saved API key is removed only by the Delete button."""
    if delete_saved_api:
        delete_private_api_keys()
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


def _new_project_workspace():
    """Create a private workspace for this Streamlit browser session only."""
    session_id = uuid.uuid4().hex
    workspace = Path(tempfile.gettempdir()) / "ai_khemra_bro_sessions" / session_id
    workspace.mkdir(parents=True, exist_ok=True)
    return session_id, workspace


def _ensure_project_workspace():
    session_id = st.session_state.get("project_session_id")
    workspace_value = st.session_state.get("project_workspace")
    if not session_id or not workspace_value:
        session_id, workspace = _new_project_workspace()
        st.session_state.project_session_id = session_id
        st.session_state.project_workspace = str(workspace)
        return workspace
    workspace = Path(workspace_value)
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def _reset_project_workspace():
    """Delete and recreate only the current user's workspace."""
    old_value = st.session_state.get("project_workspace")
    if old_value:
        shutil.rmtree(old_value, ignore_errors=True)
    session_id, workspace = _new_project_workspace()
    st.session_state.project_session_id = session_id
    st.session_state.project_workspace = str(workspace)
    return workspace


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
    'project_session_id':'',
    'project_workspace':'',
    'mp3_filename_widget':'khmer_story_dubbed',
    'source_srt_text':'',
    'speech_tab_audio_bytes':None,
    'text_tab_audio_bytes':None,
}.items():
    if key not in st.session_state:
        st.session_state[key]=value

_ensure_project_workspace()

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
    """Save this upload inside the current user's private session folder."""
    suffix = Path(uploaded_file.name).suffix.lower() or ".mp4"
    workspace = _ensure_project_workspace()
    destination = workspace / f"upload_{uuid.uuid4().hex}{suffix}"
    uploaded_file.seek(0)
    with destination.open("wb") as temp:
        shutil.copyfileobj(uploaded_file, temp, length=1024 * 1024)
        temp.flush()
    return destination

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
    """Prepare speech for ASR while preserving both near and distant voices."""
    # Dynamic normalization raises quiet/distant dialogue without crushing nearby
    # speakers. Gentle denoise removes steady background hiss while retaining speech.
    audio_filter = (
        "highpass=f=70,lowpass=f=7800,"
        "afftdn=nf=-28:tn=1,"
        "dynaudnorm=f=250:g=9:p=0.95:m=12,"
        "acompressor=threshold=-30dB:ratio=2.2:attack=12:release=180:makeup=1.35,"
        "alimiter=limit=0.97"
    )
    result = subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(video_path),
            "-vn", "-ac", "1", "-ar", "16000",
            "-af", audio_filter,
            "-c:a", "flac", "-compression_level", "8", str(audio_path),
        ],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0 or not audio_path.exists():
        raise RuntimeError(result.stderr[-1200:] or "មិនអាចទាញសំឡេងចេញពីវីដេអូបានទេ។")


def _standardize_whisper_segments(segments):
    """Split ASR output into readable, timing-accurate subtitle cues."""
    cues = []
    max_duration = 5.5
    max_chars = 34
    punctuation = set("。！？!?；;，,")

    def emit(words):
        if not words:
            return
        text = "".join((getattr(w, "word", "") or "") for w in words).strip()
        if not text:
            return
        start = max(0.0, float(getattr(words[0], "start", 0.0) or 0.0))
        end = max(start + 0.20, float(getattr(words[-1], "end", start + 0.20) or start + 0.20))
        cues.append({"id": len(cues) + 1, "start": start, "end": end, "source": text})

    for segment in segments:
        words = [w for w in (getattr(segment, "words", None) or []) if (getattr(w, "word", "") or "").strip()]
        if not words:
            text = (getattr(segment, "text", "") or "").strip()
            if text:
                start = max(0.0, float(segment.start))
                end = max(start + 0.20, float(segment.end))
                cues.append({"id": len(cues) + 1, "start": start, "end": end, "source": text})
            continue

        current = []
        for word in words:
            if current:
                gap = max(0.0, float(word.start or 0.0) - float(current[-1].end or 0.0))
                duration = float(current[-1].end or 0.0) - float(current[0].start or 0.0)
                chars = len("".join((getattr(w, "word", "") or "") for w in current))
                if gap >= 0.55 or duration >= max_duration or chars >= max_chars:
                    emit(current)
                    current = []
            current.append(word)
            token = (getattr(word, "word", "") or "").strip()
            duration = float(word.end or 0.0) - float(current[0].start or 0.0)
            if token and token[-1] in punctuation and duration >= 0.65:
                emit(current)
                current = []
        emit(current)

    # Remove only tiny accidental overlaps; never push a cue far from the speech.
    previous_end = 0.0
    for cue in cues:
        if cue["start"] < previous_end and previous_end - cue["start"] <= 0.12:
            cue["start"] = previous_end
        if cue["end"] <= cue["start"]:
            cue["end"] = cue["start"] + 0.25
        previous_end = cue["end"]
    for index, cue in enumerate(cues, 1):
        cue["id"] = index
    return cues


def transcribe_with_whisper(wav_path):
    model = load_whisper_model()
    segments, _ = model.transcribe(
        str(wav_path),
        language="zh",
        beam_size=10,
        best_of=5,
        vad_filter=True,
        vad_parameters={
            "min_silence_duration_ms": 220,
            "min_speech_duration_ms": 45,
            "speech_pad_ms": 380,
        },
        condition_on_previous_text=True,
        word_timestamps=True,
        no_speech_threshold=0.65,
        log_prob_threshold=-1.5,
        compression_ratio_threshold=2.6,
    )
    cues = _standardize_whisper_segments(list(segments))
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
    """Khmer spoken-word budget that fits normal dialogue speed."""
    duration = max(0.35, float(end) - float(start))
    # About 3 Khmer spoken units per second, with a small allowance for short replies.
    # Meaning-bearing words may not be removed; the translator must use concise wording.
    return max(2, min(22, int(duration * 3.0 + 1.0)))


def khmer_word_count(text):
    return len([part for part in re.split(r"\s+", (text or "").strip()) if part])


def contains_cjk(text):
    return bool(re.search(r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]", text or ""))


def normalize_dialogue(text):
    text = re.sub(r"```|<[^>]+>", "", str(text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def gemini_generate_with_retry(client, model_name, contents, attempts=4):
    """Call Gemini with bounded retry for temporary network/rate-limit failures."""
    last_error = None
    for attempt in range(max(1, attempts)):
        try:
            return client.models.generate_content(model=model_name, contents=contents)
        except Exception as exc:
            last_error = exc
            message = str(exc).upper()
            retryable = any(token in message for token in (
                "429", "RESOURCE_EXHAUSTED", "RATE LIMIT", "503", "UNAVAILABLE",
                "TIMEOUT", "DEADLINE_EXCEEDED", "INTERNAL"
            ))
            if not retryable or attempt >= attempts - 1:
                raise
            time.sleep(min(8.0, 1.2 * (2 ** attempt)))
    raise last_error


def translation_needs_repair(cue, item):
    """Reject missing, Chinese, or clearly overlong dubbing lines."""
    if not item:
        return True
    dialogue = normalize_dialogue(item.get("text"))
    if not dialogue or contains_cjk(dialogue):
        return True
    # A tiny tolerance avoids needless API calls for Khmer tokenization quirks.
    return khmer_word_count(dialogue) > cue_word_limit(cue["start"], cue["end"]) + 2


def repair_translation_items(client, model_name, uploaded_video, cues, items):
    """Retry only missing or still-Chinese cues until every cue is usable Khmer."""
    by_id = {cue["id"]: cue for cue in cues}
    for _attempt in range(3):
        bad_ids = [
            cue["id"] for cue in cues
            if translation_needs_repair(cue, items.get(cue["id"]))
        ]
        if not bad_ids:
            return items
        for offset in range(0, len(bad_ids), 12):
            group = [by_id[i] for i in bad_ids[offset:offset + 12]]
            payload = "\n".join(
                f'ID={cue["id"]} | MAX_WORDS={cue_word_limit(cue["start"], cue["end"])} | SOURCE={cue["source"]}'
                for cue in group
            )
            prompt = TRANSLATE_PROMPT + "\nIMPORTANT: These cues failed before. Translate EVERY audible word, tiny response, negation, name, number, filler, and emotional reaction fully into natural Khmer. Never omit or summarize any element. Never copy Chinese characters.\n\nCUES:\n" + payload
            contents = [uploaded_video, prompt] if uploaded_video is not None else [prompt]
            response = gemini_generate_with_retry(client, model_name, contents)
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
    bad_ids = [
        cue["id"] for cue in cues
        if translation_needs_repair(cue, items.get(cue["id"]))
    ]
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
        response = gemini_generate_with_retry(
            client, model_name,
            [uploaded_video, ANALYZE_PROMPT + "\n\nCUES:\n" + "\n".join(lines)],
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
    """Translate in sequential batches while carrying recent character context."""
    result_by_id = {}
    batch_size = 24
    context_size = 6

    for offset in range(0, len(cues), batch_size):
        batch = cues[offset:offset + batch_size]

        previous_context = []
        for previous in cues[max(0, offset - context_size):offset]:
            translated = result_by_id.get(previous["id"])
            if translated:
                previous_context.append(
                    f'ID={previous["id"]} | TAG={translated["tag"]} '
                    f'| SOURCE={previous["source"]} | KHMER={translated["text"]}'
                )

        cue_lines = "\n".join(
            f"ID={cue['id']} | {seconds_to_srt(cue['start'])} --> "
            f"{seconds_to_srt(cue['end'])} | MAX_WORDS={cue_word_limit(cue['start'], cue['end'])} "
            f"| SOURCE={cue['source']}"
            for cue in batch
        )

        context_block = ""
        if previous_context:
            context_block = (
                "\n\nRECENT CONTINUITY CONTEXT (reference only; do not return these IDs):\n"
                + "\n".join(previous_context)
            )

        prompt = (
            TRANSLATE_PROMPT
            + context_block
            + "\n\nNEW CUES TO RETURN:\n"
            + cue_lines
        )
        response = gemini_generate_with_retry(
            client, model_name, [uploaded_video, prompt]
        )
        items = parse_json_array(response.text or "")
        for item in items:
            try:
                cue_id = int(item.get("id"))
            except (TypeError, ValueError, AttributeError):
                continue
            if cue_id not in {cue["id"] for cue in batch}:
                continue
            tag = str(item.get("tag", "M")).upper().strip()
            if tag not in VOICE_PROFILES:
                tag = "M_ADULT"
            translated = normalize_dialogue(item.get("text", ""))
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



# ---------------------------------------------------------------------------
# v5.5 resilient SRT workflow
# ---------------------------------------------------------------------------
def build_source_srt(cues):
    """Build a standards-compliant source-language SRT from Whisper cues.

    This is always available even when Gemini has no quota, so the user never
    loses the transcription work and can still download or translate it later.
    """
    blocks = []
    for index, cue in enumerate(cues, start=1):
        text = normalize_dialogue(cue.get("source", ""))
        if not text:
            continue
        blocks.append(
            f"{index}\n{seconds_to_srt(cue['start'])} --> {seconds_to_srt(cue['end'])}\n{text}"
        )
    return "\n\n".join(blocks).strip()


def transcribe_video_to_source_srt(video_path):
    """FFmpeg + Whisper only. No Gemini key is required."""
    with tempfile.TemporaryDirectory() as folder:
        audio_path = Path(folder) / "audio_16k.flac"
        extract_audio(Path(video_path), audio_path)
        cues = transcribe_with_whisper(audio_path)
        source_srt = build_source_srt(cues)
        if not source_srt or "-->" not in source_srt:
            raise RuntimeError("មិនអាចបង្កើត Source SRT ពីវីដេអូបានទេ។")
        return cues, source_srt

# ---------------------------------------------------------------------------
# v5.4 reliable Khmer SRT pipeline
# ---------------------------------------------------------------------------
def _candidate_gemini_models(selected_model):
    """Return production-safe Gemini text models in fallback order.

    The former 2.5-only list caused 404 errors for some new API projects.
    Stable Gemini 3 models are preferred, followed by the rolling Flash alias
    and finally 2.5 compatibility models for older projects.
    """
    ordered = [
        str(selected_model or "").strip(),
        "gemini-3.5-flash-lite",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-flash-latest",
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
    ]
    result = []
    for name in ordered:
        name = str(name or "").strip()
        if name and name not in result:
            result.append(name)
    return result


def _translate_batch_text_only(client, model_name, batch, previous_context=""):
    """Translate Whisper text only. This avoids costly video upload requests."""
    cue_lines = "\n".join(
        f'ID={cue["id"]} | TIME={seconds_to_srt(cue["start"])} --> '
        f'{seconds_to_srt(cue["end"])} | SOURCE={cue["source"]}'
        for cue in batch
    )
    prompt = f"""
You are the Khmer subtitle translation engine for AI KHEMRA BRO.
Translate every SOURCE line into natural spoken Khmer for movie dubbing.

STRICT RULES:
1. Return JSON array only. No markdown and no explanation.
2. Return every input ID exactly once and in the same order.
3. Never change, merge, split, or invent IDs.
4. Do not omit short replies, names, numbers, negations, fillers, cries, or reactions.
5. Output Khmer only in text. Do not leave Chinese, Thai, Vietnamese, or English dialogue.
6. Keep each line concise enough for its timestamp, but preserve the full meaning.
7. Select one tag: M_ADULT, F_ADULT, M_OLD, F_OLD, BOY, GIRL,
   M_THINK, F_THINK, NARRATOR_M, NARRATOR_F.
8. JSON format: [{{"id":1,"tag":"M_ADULT","text":"..."}}]

RECENT CONTEXT:
{previous_context or '(none)'}

CUES:
{cue_lines}
""".strip()
    response = gemini_generate_with_retry(client, model_name, [prompt], attempts=3)
    rows = parse_json_array(response.text or "")
    allowed_ids = {cue["id"] for cue in batch}
    parsed = {}
    for row in rows:
        try:
            cue_id = int(row.get("id"))
        except (TypeError, ValueError, AttributeError):
            continue
        if cue_id not in allowed_ids:
            continue
        tag = str(row.get("tag", "M_ADULT")).upper().strip()
        if tag not in VOICE_PROFILES:
            tag = "M_ADULT"
        dialogue = normalize_dialogue(row.get("text", ""))
        if dialogue and not contains_cjk(dialogue):
            parsed[cue_id] = {"tag": tag, "text": dialogue}
    return parsed


def translate_cues_text_only(client, model_name, cues):
    """Low-request translation path designed for free-tier Gemini keys."""
    translated = {}
    # Larger batches reduce request count and 429 failures.
    batch_size = 45
    for offset in range(0, len(cues), batch_size):
        batch = cues[offset:offset + batch_size]
        context_rows = []
        for cue in cues[max(0, offset - 5):offset]:
            item = translated.get(cue["id"])
            if item:
                context_rows.append(
                    f'ID={cue["id"]} TAG={item["tag"]} SOURCE={cue["source"]} KHMER={item["text"]}'
                )
        parsed = _translate_batch_text_only(
            client, model_name, batch, "\n".join(context_rows)
        )
        translated.update(parsed)

        missing = [cue for cue in batch if cue["id"] not in translated]
        if missing:
            # One compact repair request, only for missing lines.
            repaired = _translate_batch_text_only(client, model_name, missing)
            translated.update(repaired)

        still_missing = [cue["id"] for cue in batch if cue["id"] not in translated]
        if still_missing:
            raise RuntimeError(
                "AI មិនបានត្រឡប់បន្ទាត់ SRT គ្រប់គ្រាន់៖ "
                + ", ".join(map(str, still_missing[:20]))
            )
    return translated


def video_to_srt(video_path, api_keys, model, prepared_cues=None):
    """
    Reliable v5.5 path:
    FFmpeg -> Whisper timestamps -> text-only Gemini translation -> Khmer SRT.
    When prepared_cues are supplied, Whisper is not run a second time.
    """
    if isinstance(api_keys, str):
        api_keys = [api_keys]
    api_keys = [str(key).strip() for key in api_keys if str(key).strip()]
    if not api_keys:
        raise ValueError("មិនមាន Gemini API Key សម្រាប់ប្រើទេ។")

    if prepared_cues is None:
        with tempfile.TemporaryDirectory() as folder:
            audio_path = Path(folder) / "audio_16k.flac"
            extract_audio(Path(video_path), audio_path)
            cues = transcribe_with_whisper(audio_path)
    else:
        cues = prepared_cues
    if not cues:
        raise RuntimeError("Whisper មិនរកឃើញសំឡេងនិយាយក្នុងវីដេអូនេះទេ។")

    last_error = None
    for api_key_value in api_keys:
        client = genai.Client(api_key=api_key_value)
        for model_name in _candidate_gemini_models(model):
            try:
                translated = translate_cues_text_only(client, model_name, cues)
                result = build_srt(cues, translated)
                if not result.strip() or "-->" not in result:
                    raise RuntimeError("មិនអាចបង្កើត Khmer SRT បានទេ។")
                return result
            except Exception as exc:
                last_error = exc
                message = str(exc).upper()
                # Try the next model for quota/model availability problems.
                if (
                    is_quota_error(exc)
                    or is_invalid_key_error(exc)
                    or "NOT_FOUND" in message
                    or "MODEL" in message and "NOT" in message
                    or "UNAVAILABLE" in message
                    or "503" in message
                ):
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
        response = gemini_generate_with_retry(client, model_name, contents)
        for item in parse_json_array(response.text or ""):
            try:
                cue_id = int(item.get("id"))
            except (TypeError, ValueError, AttributeError):
                continue
            tag = str(item.get("tag", "M")).upper().strip()
            if tag not in VOICE_PROFILES:
                tag = "M_ADULT"
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
    tag_re=re.compile(r'^\[(BOY|GIRL|M_YOUNG|F_YOUNG|M_ADULT|F_ADULT|M_OLD|F_OLD|M_THINK|F_THINK|NARRATOR_M|NARRATOR_F|M|F|OLD_M|OLD_F)\]\s*',re.I)
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
        tag=tag_match.group(1).upper() if tag_match else 'M_ADULT'
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

def prepare_tts_text(text):
    """Prepare conversational Khmer for smoother Edge-TTS rhythm and intonation."""
    clean = normalize_dialogue(text)
    clean = re.sub(r"\s+([,!?។])", r"\1", clean)
    clean = re.sub(r"([,!?។]){2,}", r"\1", clean)
    # A final Khmer full stop gives declarative lines a gentle natural fall.
    if clean and clean[-1] not in "!?។…":
        clean += "។"
    return clean


async def synthesize(text, profile, output_path):
    clean_text = prepare_tts_text(text)
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

def character_voice_filters(tag):
    """Subtle per-role tone shaping so age/role labels do not all sound identical."""
    mapping = {
        'BOY': ['equalizer=f=180:t=q:w=1.0:g=-0.8', 'equalizer=f=2900:t=q:w=1.0:g=1.0'],
        'GIRL': ['equalizer=f=180:t=q:w=1.0:g=-1.0', 'equalizer=f=3000:t=q:w=1.0:g=1.0'],
        'M_YOUNG': ['equalizer=f=190:t=q:w=1.0:g=0.7', 'equalizer=f=2500:t=q:w=1.0:g=0.5'],
        'F_YOUNG': ['equalizer=f=220:t=q:w=1.0:g=0.4', 'equalizer=f=2600:t=q:w=1.0:g=0.6'],
        'M_ADULT': ['equalizer=f=170:t=q:w=1.0:g=1.6', 'equalizer=f=3200:t=q:w=1.0:g=-0.4'],
        'F_ADULT': ['equalizer=f=220:t=q:w=1.0:g=0.9', 'equalizer=f=3000:t=q:w=1.0:g=0.2'],
        'M_OLD': ['equalizer=f=140:t=q:w=1.0:g=2.2', 'equalizer=f=2600:t=q:w=1.0:g=-1.0', 'lowpass=f=7200:p=2'],
        'F_OLD': ['equalizer=f=180:t=q:w=1.0:g=1.7', 'equalizer=f=2800:t=q:w=1.0:g=-0.8', 'lowpass=f=7400:p=2'],
        'M_THINK': ['equalizer=f=180:t=q:w=1.0:g=1.2', 'equalizer=f=3500:t=q:w=1.0:g=-1.0', 'volume=0.96'],
        'F_THINK': ['equalizer=f=220:t=q:w=1.0:g=0.8', 'equalizer=f=3600:t=q:w=1.0:g=-0.8', 'volume=0.96'],
        'NARRATOR_M': ['equalizer=f=150:t=q:w=1.0:g=2.0', 'equalizer=f=2200:t=q:w=1.0:g=0.8'],
        'NARRATOR_F': ['equalizer=f=200:t=q:w=1.0:g=1.3', 'equalizer=f=2300:t=q:w=1.0:g=0.7'],
    }
    return mapping.get(tag, [])


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
    """
    Create one synchronized Khmer MP3.

    v3.0 rules:
    - Every voice starts at the original SRT start timestamp.
    - A clip is fitted inside the time available before the next cue.
    - Generated voices never overlap or compete with one another.
    - Breathy high frequencies are reduced without making speech muddy.
    - Loudness is mastered once at the end instead of aggressively per clip.
    """
    cues = parse_srt(srt_text)
    if not cues:
        raise ValueError('រកមិនឃើញ SRT និង timestamp ត្រឹមត្រូវទេ។')

    chinese_rows = [i + 1 for i, cue in enumerate(cues) if contains_cjk(cue['text'])]
    if chinese_rows:
        raise ValueError(
            f'SRT នៅមានអក្សរចិននៅបន្ទាត់៖ {chinese_rows[:20]}។ '
            'សូម Generate SRT ឡើងវិញ។'
        )

    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        clips = []
        clip_durations = []
        total_cues = len(cues)

        if progress_callback:
            progress_callback(2, "កំពុងរៀបចំសំឡេងតួអង្គ…")

        for index, cue in enumerate(cues):
            clip = root / f'clip_{index:04d}.mp3'
            profile = VOICE_PROFILES.get(cue['tag'], VOICE_PROFILES['M_ADULT'])
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

        for index, cue in enumerate(cues):
            start_ms = max(0, int(cue['start']))
            cue_end_ms = max(start_ms + 250, int(cue['end']))

            # The next voice owns its exact start time. The current voice must
            # finish before that point, so two generated speakers never overlap.
            if index + 1 < total_cues:
                next_start_ms = max(start_ms + 250, int(cues[index + 1]['start']))
                protected_end_ms = min(cue_end_ms, next_start_ms - MIN_VOICE_GAP_MS)
            else:
                protected_end_ms = cue_end_ms

            if protected_end_ms <= start_ms + 180:
                protected_end_ms = start_ms + 180

            slot_seconds = max(0.18, (protected_end_ms - start_ms) / 1000.0)
            audio_seconds = clip_durations[index]

            # Fit the spoken line to its real available slot. We allow a moderate
            # speed increase, then hard-trim only as the final overlap safeguard.
            required_speed = audio_seconds / slot_seconds
            safe_speed = min(max(1.0, required_speed), MAX_TEMPO_SPEED)
            tempo = atempo_chain(safe_speed) if safe_speed > 1.001 else ''
            rendered_seconds = audio_seconds / safe_speed
            trim_seconds = min(rendered_seconds, slot_seconds)

            fade_in = min(VOICE_FADE_IN_SECONDS, max(0.015, trim_seconds * 0.10))
            fade_out = min(VOICE_FADE_OUT_SECONDS, max(0.025, trim_seconds * 0.14))
            fade_out_start = max(0.01, trim_seconds - fade_out)

            label = f'a{index}'
            parts = [f'[{index}:a]asetpts=PTS-STARTPTS']
            if tempo:
                parts.append(tempo)

            # Warm, controlled speech chain:
            # - reduce rumble and strong airy hiss
            # - keep Khmer consonants understandable
            # - use gentle compression only
            parts.extend([
                'highpass=f=75:p=2',
                'lowpass=f=7600:p=2',
                'equalizer=f=180:t=q:w=1.0:g=1.2',
                'equalizer=f=320:t=q:w=1.1:g=1.0',
                'equalizer=f=1100:t=q:w=1.2:g=0.7',
                'equalizer=f=2400:t=q:w=1.1:g=0.8',
                'equalizer=f=4300:t=q:w=1.0:g=-1.8',
                'equalizer=f=5800:t=q:w=0.9:g=-3.2',
                'equalizer=f=7000:t=q:w=0.8:g=-3.8',
                *character_voice_filters(cue.get('tag', 'M_ADULT')),
                'acompressor=threshold=-23dB:ratio=2.0:attack=14:release=190:makeup=1.15:knee=4',
                f'atrim=0:{trim_seconds:.3f}',
                'asetpts=PTS-STARTPTS',
                f'afade=t=in:st=0:d={fade_in:.3f}',
                f'afade=t=out:st={fade_out_start:.3f}:d={fade_out:.3f}',
                'alimiter=limit=0.94:attack=7:release=100',
                f'adelay={start_ms}|{start_ms}[{label}]',
            ])

            filters.append(','.join(parts).replace('],', ']'))
            labels.append(f'[{label}]')
            final_end_ms = max(
                final_end_ms,
                start_ms + int(trim_seconds * 1000),
                cue_end_ms,
            )

        total = (final_end_ms + 350) / 1000.0

        # Master once after mixing. This avoids pumping and exaggerated breath
        # noise caused by loud-normalizing every small clip independently.
        filters.append(
            ''.join(labels)
            + f'amix=inputs={len(labels)}:duration=longest:dropout_transition=0:normalize=0,'
              'acompressor=threshold=-18dB:ratio=1.55:attack=18:release=240:makeup=1.0:knee=5,'
              'alimiter=limit=0.94:attack=8:release=150,'
              'loudnorm=I=-16:TP=-1.5:LRA=7,'
              f'apad=whole_dur={total:.3f},atrim=0:{total:.3f}[out]'
        )

        output = root / 'khmer_dubbed.mp3'
        command.extend([
            '-filter_complex', ';'.join(filters),
            '-map', '[out]',
            '-c:a', 'libmp3lame',
            '-ac', '2',
            '-ar', '48000',
            '-b:a', '192k',
            str(output),
        ])

        if progress_callback:
            progress_callback(92, "កំពុងបញ្ចូលសំឡេងទាំងអស់ជាបទ MP3 តែមួយ…")

        result = subprocess.run(command, capture_output=True, text=True, timeout=900)
        if result.returncode != 0:
            raise RuntimeError(result.stderr[-2200:] or 'FFmpeg failed.')
        if not output.exists() or output.stat().st_size < 1000:
            raise RuntimeError('MP3 ត្រូវបានបង្កើត ប៉ុន្តែមិនមានសំឡេងគ្រប់គ្រាន់។')

        if progress_callback:
            progress_callback(100, "បង្កើត MP3 រួចរាល់")
        return output.read_bytes()




# ─────────────────────────────────────────────────────────────────────────────
# PRIVATE CUSTOMER LOGIN + HIDDEN OWNER LICENSE MANAGEMENT
# This module adds security only. The original app UI/workflow below is unchanged.
# ─────────────────────────────────────────────────────────────────────────────
LICENSE_DB_PATH = Path(__file__).with_name("licenses.db")
SESSION_COOKIE_NAME = "ai_khemra_bro_customer_session"
LOGIN_COOKIE_NAME = "ai_khemra_bro_saved_login"
SESSION_IDLE_MINUTES = 30
LOGIN_WINDOW_MINUTES = 15
MAX_LOGIN_ATTEMPTS = 5
NEW_LICENSE_CARD_HOURS = 24


def _utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def _iso(value=None):
    return (value or _utcnow()).isoformat(timespec="seconds")


def _parse_iso(value):
    parsed = datetime.datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed.astimezone(datetime.timezone.utc)


def _secret(name, default=""):
    try:
        return str(st.secrets.get(name, default)).strip()
    except Exception:
        return str(default).strip()


def get_admin_username():
    return _secret("ADMIN_USERNAME", "KHEMRA")


def get_admin_password():
    # Works immediately even before Streamlit Secrets are configured.
    # For production, set ADMIN_PASSWORD in Streamlit Secrets to override this bootstrap value.
    return _secret("ADMIN_PASSWORD", "0719067125")


def license_connection():
    connection = sqlite3.connect(str(LICENSE_DB_PATH), timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=30000")
    return connection


def _ensure_column(connection, table, column, definition):
    names = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
    if column not in names:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def initialize_license_database():
    with license_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS licenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                access_code_hash TEXT UNIQUE,
                access_code_display TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                last_login_at TEXT,
                login_count INTEGER NOT NULL DEFAULT 0,
                active_session_hash TEXT,
                active_session_last_seen TEXT,
                created_card_until TEXT
            )
            """
        )
        # Safe migration from older versions of the same app.
        _ensure_column(connection, "licenses", "access_code_hash", "TEXT")
        _ensure_column(connection, "licenses", "access_code_display", "TEXT")
        _ensure_column(connection, "licenses", "active_session_hash", "TEXT")
        _ensure_column(connection, "licenses", "active_session_last_seen", "TEXT")
        _ensure_column(connection, "licenses", "created_card_until", "TEXT")
        _ensure_column(connection, "licenses", "saved_api_keys_encrypted", "TEXT")
        _ensure_column(connection, "licenses", "plan_label", "TEXT")
        old_columns = {row["name"] for row in connection.execute("PRAGMA table_info(licenses)")}
        if "access_code" in old_columns:
            rows = connection.execute(
                "SELECT id, access_code, access_code_hash, access_code_display FROM licenses"
            ).fetchall()
            for row in rows:
                raw = normalize_access_code(row["access_code"])
                if raw:
                    connection.execute(
                        "UPDATE licenses SET access_code_hash=COALESCE(access_code_hash, ?), "
                        "access_code_display=CASE WHEN access_code_display IS NULL OR access_code_display='' THEN ? ELSE access_code_display END "
                        "WHERE id=?",
                        (_hash_code(raw), raw, row["id"]),
                    )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS login_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_key TEXT NOT NULL,
                attempted_at TEXT NOT NULL,
                success INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_at TEXT NOT NULL,
                event_type TEXT NOT NULL,
                actor TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT ''
            )
            """
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_login_attempts_key_time ON login_attempts(attempt_key, attempted_at)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(event_at)")
        connection.commit()


def normalize_customer_name(value):
    return " ".join(str(value or "").strip().split())[:80]


def normalize_access_code(value):
    return re.sub(r"[^A-Z0-9-]", "", str(value or "").strip().upper())[:48]


def _hash_code(code):
    pepper = _secret("LICENSE_PEPPER", raw_cookie_secret)
    return hmac.new(pepper.encode("utf-8"), code.encode("utf-8"), hashlib.sha256).hexdigest()


def _hash_session(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _audit(event_type, actor, details=""):
    with license_connection() as connection:
        connection.execute(
            "INSERT INTO audit_log(event_at,event_type,actor,details) VALUES(?,?,?,?)",
            (_iso(), str(event_type)[:60], str(actor)[:100], str(details)[:500]),
        )
        connection.commit()


def _attempt_key(name, code):
    return hashlib.sha256(f"{name.casefold()}|{_hash_code(code)}".encode("utf-8")).hexdigest()


def _login_blocked(attempt_key):
    cutoff = _iso(_utcnow() - datetime.timedelta(minutes=LOGIN_WINDOW_MINUTES))
    with license_connection() as connection:
        count = connection.execute(
            "SELECT COUNT(*) AS c FROM login_attempts WHERE attempt_key=? AND attempted_at>=? AND success=0",
            (attempt_key, cutoff),
        ).fetchone()["c"]
    return count >= MAX_LOGIN_ATTEMPTS


def _record_login_attempt(attempt_key, success):
    with license_connection() as connection:
        connection.execute(
            "INSERT INTO login_attempts(attempt_key,attempted_at,success) VALUES(?,?,?)",
            (attempt_key, _iso(), 1 if success else 0),
        )
        # Keep the DB compact.
        cutoff = _iso(_utcnow() - datetime.timedelta(days=7))
        connection.execute("DELETE FROM login_attempts WHERE attempted_at < ?", (cutoff,))
        connection.commit()


def validate_manual_access_code(value):
    """Validate an owner-selected reusable access code."""
    code = normalize_access_code(value)
    if not code:
        raise ValueError("សូមបញ្ចូល Access Code ដែលអ្នកចង់កំណត់។")
    if len(code) < 4 or len(code) > 64:
        raise ValueError("Access Code ត្រូវមានចន្លោះពី 4 ដល់ 64 តួអក្សរ។")
    if not re.fullmatch(r"[A-Z0-9_-]+", code):
        raise ValueError("Access Code អាចប្រើតែ A-Z, 0-9, សញ្ញា - និង _ ប៉ុណ្ណោះ។")
    return code


def add_license(customer_name, access_code, duration_days, plan_label=""):
    name = normalize_customer_name(customer_name)
    if not name:
        raise ValueError("សូមបញ្ចូលឈ្មោះអតិថិជន។")

    days = int(duration_days)
    allowed_plans = {
        7: "7 ថ្ងៃ",
        30: "1 ខែ",
        90: "3 ខែ",
        180: "6 ខែ",
        365: "1 ឆ្នាំ",
    }
    if days not in allowed_plans:
        raise ValueError("រយៈពេលមិនត្រឹមត្រូវ។")

    plan = str(plan_label or allowed_plans[days]).strip()
    now = _utcnow()
    expires = now + datetime.timedelta(days=days)
    card_until = now + datetime.timedelta(hours=NEW_LICENSE_CARD_HOURS)
    code = validate_manual_access_code(access_code)

    with license_connection() as connection:
        duplicate = connection.execute(
            "SELECT 1 FROM licenses WHERE access_code_hash=? OR access_code_display=?",
            (_hash_code(code), code),
        ).fetchone()
        if duplicate:
            raise ValueError("Access Code នេះមានរួចហើយ។ សូមកំណត់លេខកូដផ្សេង។")
        connection.execute(
            """
            INSERT INTO licenses
            (customer_name, access_code_hash, access_code_display, created_at, expires_at,
             is_active, created_card_until, plan_label)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                name,
                _hash_code(code),
                code,
                _iso(now),
                _iso(expires),
                _iso(card_until),
                plan,
            ),
        )
        connection.commit()

    _audit("license_created", get_admin_username(), f"{name}|{plan}|{days} days")
    return code, expires, card_until


def _session_cookie_get():
    try:
        encrypted = cookie_manager.get(SESSION_COOKIE_NAME)
        return decrypt_api_keys(encrypted) if encrypted else ""
    except Exception:
        return ""


def _session_cookie_set(token):
    try:
        cookie_manager.set(
            SESSION_COOKIE_NAME,
            encrypt_api_keys(token),
            expires_at=datetime.datetime.now() + datetime.timedelta(days=365),
            key="save_customer_session_cookie",
        )
    except Exception:
        pass


def _session_cookie_delete():
    try:
        cookie_manager.delete(SESSION_COOKIE_NAME, key="delete_customer_session_cookie")
    except Exception:
        pass


def _saved_login_get():
    """Return encrypted saved customer credentials for automatic login."""
    try:
        encrypted = cookie_manager.get(LOGIN_COOKIE_NAME)
        if not encrypted:
            return "", ""
        payload = decrypt_api_keys(encrypted)
        data = json.loads(payload)
        return str(data.get("name", "")), str(data.get("code", ""))
    except Exception:
        return "", ""


def _saved_login_set(name, code):
    """Remember this customer's login on this browser until explicit logout."""
    try:
        payload = json.dumps({"name": str(name or ""), "code": str(code or "")}, ensure_ascii=False)
        cookie_manager.set(
            LOGIN_COOKIE_NAME,
            encrypt_api_keys(payload),
            expires_at=datetime.datetime.now() + datetime.timedelta(days=3650),
            key="save_customer_login_cookie",
        )
    except Exception:
        pass


def _saved_login_delete():
    try:
        cookie_manager.delete(LOGIN_COOKIE_NAME, key="delete_customer_login_cookie")
    except Exception:
        pass


def validate_customer_login(customer_name, access_code, existing_token="", acquire_session=False):
    """Validate a customer license without binding it to a device or browser.

    A valid, active, unexpired access code may be used again after logout,
    browser close, phone restart, or from another phone. The customer name is
    kept for display but the access code is the authentication credential.
    """
    entered_name = normalize_customer_name(customer_name)
    code = normalize_access_code(access_code)
    if not code:
        return False, "សូមបញ្ចូលលេខកូដ Access Code។", None, ""

    attempt_key = _attempt_key(entered_name or "code-user", code)
    if acquire_session and _login_blocked(attempt_key):
        return False, f"បានសាកច្រើនដងពេក។ សូមរង់ចាំ {LOGIN_WINDOW_MINUTES} នាទី។", None, ""

    now = _utcnow()
    code_hash = _hash_code(code)
    failure_reason = ""
    fresh = None
    token = existing_token or secrets.token_urlsafe(32)

    with license_connection() as connection:
        row = connection.execute(
            "SELECT * FROM licenses WHERE access_code_hash=? OR access_code_display=?",
            (code_hash, code),
        ).fetchone()

        if row is None:
            failure_reason = "លេខកូដមិនត្រឹមត្រូវ។"
        elif not bool(row["is_active"]):
            failure_reason = "លេខកូដនេះត្រូវបាន Owner បិទ។"
        elif now >= _parse_iso(row["expires_at"]):
            failure_reason = "កញ្ចប់របស់អ្នកបានផុតកំណត់។ សូមទាក់ទង Owner ដើម្បីបន្តសិទ្ធិប្រើប្រាស់។"
        else:
            # No device lock and no single-session lock. A purchased code can
            # be reused after logout/close and can work on any phone/browser.
            if acquire_session:
                connection.execute(
                    """
                    UPDATE licenses
                    SET active_session_hash=NULL,
                        active_session_last_seen=NULL,
                        last_login_at=?,
                        login_count=login_count+1
                    WHERE id=?
                    """,
                    (_iso(now), row["id"]),
                )
            else:
                connection.execute(
                    "UPDATE licenses SET active_session_hash=NULL, active_session_last_seen=NULL WHERE id=?",
                    (row["id"],),
                )
            connection.commit()
            fresh = connection.execute("SELECT * FROM licenses WHERE id=?", (row["id"],)).fetchone()

    if acquire_session:
        _record_login_attempt(attempt_key, not bool(failure_reason))
    if failure_reason:
        return False, failure_reason, None, ""

    display_name = str(fresh["customer_name"] or entered_name or "Customer")
    if acquire_session:
        _audit("customer_login", display_name, "success|multi-device")
    return True, "", dict(fresh), token


def release_customer_session(access_code, token, actor="customer"):
    """Log out this browser only; never block reuse of the purchased code."""
    code = normalize_access_code(access_code)
    with license_connection() as connection:
        row = connection.execute(
            "SELECT id,customer_name FROM licenses WHERE access_code_hash=? OR access_code_display=?",
            (_hash_code(code), code),
        ).fetchone()
        if row:
            connection.execute(
                "UPDATE licenses SET active_session_hash=NULL, active_session_last_seen=NULL WHERE id=?",
                (row["id"],),
            )
            connection.commit()
            _audit("customer_logout", actor, row["customer_name"])


def license_rows(search_text=""):
    query = "SELECT * FROM licenses"
    params = []
    if search_text.strip():
        query += " WHERE customer_name LIKE ? OR access_code_display LIKE ?"
        needle = f"%{search_text.strip()}%"
        params = [needle, needle]
    query += " ORDER BY id DESC"
    with license_connection() as connection:
        return connection.execute(query, params).fetchall()


def update_license_status(license_id, active):
    with license_connection() as connection:
        connection.execute(
            "UPDATE licenses SET is_active=?, active_session_hash=NULL, active_session_last_seen=NULL WHERE id=?",
            (1 if active else 0, int(license_id)),
        )
        connection.commit()
    _audit("license_status", get_admin_username(), f"id={license_id}|active={bool(active)}")


def renew_license(license_id, extra_days, plan_label=""):
    allowed_plans = {
        7: "7 ថ្ងៃ",
        30: "1 ខែ",
        90: "3 ខែ",
        180: "6 ខែ",
        365: "1 ឆ្នាំ",
    }
    days = int(extra_days)
    if days not in allowed_plans:
        raise ValueError("រយៈពេលបន្តមិនត្រឹមត្រូវ។")

    with license_connection() as connection:
        row = connection.execute(
            "SELECT expires_at,customer_name FROM licenses WHERE id=?",
            (int(license_id),),
        ).fetchone()
        if not row:
            raise ValueError("រកមិនឃើញ Customer។")

        now = _utcnow()
        current_expiry = _parse_iso(row["expires_at"])
        base = max(current_expiry, now)
        new_expiry = base + datetime.timedelta(days=days)
        plan = str(plan_label or allowed_plans[days]).strip()

        connection.execute(
            """
            UPDATE licenses
            SET expires_at=?, is_active=1, plan_label=?
            WHERE id=?
            """,
            (_iso(new_expiry), plan, int(license_id)),
        )
        connection.commit()

    _audit("license_renewed", get_admin_username(), f"{row['customer_name']}|{plan}|+{days}")


def disconnect_license(license_id):
    with license_connection() as connection:
        connection.execute(
            "UPDATE licenses SET active_session_hash=NULL,active_session_last_seen=NULL WHERE id=?",
            (int(license_id),),
        )
        connection.commit()
    _audit("session_disconnected", get_admin_username(), f"id={license_id}")


def delete_license(license_id):
    with license_connection() as connection:
        row = connection.execute("SELECT customer_name FROM licenses WHERE id=?", (int(license_id),)).fetchone()
        connection.execute("DELETE FROM licenses WHERE id=?", (int(license_id),))
        connection.commit()
    _audit("license_deleted", get_admin_username(), row["customer_name"] if row else str(license_id))


def hidden_owner_trigger():
    if "owner_click_count" not in st.session_state:
        st.session_state.owner_click_count = 0
    if "admin_gate_visible" not in st.session_state:
        st.session_state.admin_gate_visible = False
    with st.container(key="owner_trigger_container"):
        clicked = st.button("✦", key="owner_trigger", help="AI KHEMRA BRO")
    if clicked:
        st.session_state.owner_click_count += 1
        if st.session_state.owner_click_count >= 5:
            st.session_state.owner_click_count = 0
            st.session_state.admin_gate_visible = True
            st.rerun()



def render_private_subscription_countdown(expiry_datetime, plan_label):
    """
    Render a private live countdown for the currently authenticated customer.
    The browser only receives this customer's expiry timestamp.
    """
    import streamlit.components.v1 as components

    expiry_iso = expiry_datetime.astimezone(datetime.timezone.utc).isoformat()
    safe_plan = re.sub(r"[^0-9A-Za-z\u1780-\u17FF \-]", "", str(plan_label or "កញ្ចប់សមាជិក"))

    components.html(
        f"""
        <div class="khbr-countdown-card">
          <div class="khbr-plan">⌛️ {safe_plan}</div>
          <div id="khbr-countdown" class="khbr-time">កំពុងគណនា…</div>
          <div id="khbr-expiry" class="khbr-expiry"></div>
        </div>
        <style>
          html,body{{margin:0;padding:0;background:transparent;font-family:Arial,"Noto Sans Khmer",sans-serif}}
          .khbr-countdown-card{{
            min-height:112px;
            box-sizing:border-box;
            border-radius:16px;
            padding:18px 16px;
            display:flex;
            flex-direction:column;
            align-items:center;
            justify-content:center;
            text-align:center;
            color:#fff;
            border:1px solid rgba(255,255,255,.18);
            background:linear-gradient(90deg,#078bc9 0%,#25c9df 100%);
            box-shadow:0 9px 24px rgba(3,169,216,.23);
          }}
          .khbr-plan{{font-size:18px;font-weight:900;margin-bottom:9px}}
          .khbr-time{{font-size:20px;font-weight:950;line-height:1.45}}
          .khbr-expiry{{font-size:13px;font-weight:700;opacity:.92;margin-top:7px}}
        </style>
        <script>
          const end = new Date({expiry_iso!r});
          const timeNode = document.getElementById("khbr-countdown");
          const expiryNode = document.getElementById("khbr-expiry");

          function two(n) {{ return String(n).padStart(2, "0"); }}

          function updateCountdown() {{
            const now = new Date();
            let ms = end.getTime() - now.getTime();

            expiryNode.textContent =
              "ផុតកំណត់៖ " +
              two(end.getDate()) + "/" +
              two(end.getMonth()+1) + "/" +
              end.getFullYear() + " " +
              two(end.getHours()) + ":" +
              two(end.getMinutes());

            if (ms <= 0) {{
              timeNode.textContent = "❌ កញ្ចប់បានផុតកំណត់";
              return;
            }}

            const minute = 60 * 1000;
            const hour = 60 * minute;
            const day = 24 * hour;
            const week = 7 * day;
            const month = 30 * day;

            const months = Math.floor(ms / month); ms %= month;
            const weeks = Math.floor(ms / week); ms %= week;
            const days = Math.floor(ms / day); ms %= day;
            const hours = Math.floor(ms / hour); ms %= hour;
            const minutes = Math.floor(ms / minute); ms %= minute;
            const seconds = Math.floor(ms / 1000);

            const parts = [];
            if (months) parts.push(months + " ខែ");
            if (weeks) parts.push(weeks + " សប្តាហ៍");
            if (days) parts.push(days + " ថ្ងៃ");
            parts.push(two(hours) + " ម៉ោង");
            parts.push(two(minutes) + " នាទី");
            parts.push(two(seconds) + " វិនាទី");

            timeNode.textContent = "នៅសល់៖ " + parts.join(" • ");
          }}

          updateCountdown();
          setInterval(updateCountdown, 1000);
        </script>
        """,
        height=126,
        scrolling=False,
    )

def public_login_screen():
    st.markdown(
        '<div class="hero"><h1>AI KHEMRA BRO</h1><p>PRIVATE CUSTOMER ACCESS</p></div>',
        unsafe_allow_html=True,
    )

    with st.container(key="public_login_wrap"):
        st.markdown("### 🔐 ចូលប្រើកម្មវិធី")

        with st.container(key="customer_login_box"):
            with st.form("customer_login_form", clear_on_submit=False):
                name = st.text_input(
                    "ឈ្មោះ៖ (មិនចាំបាច់បញ្ចូលក៏បាន)",
                    placeholder="អាចទុកទទេបាន",
                )
                code = st.text_input(
                    "Access Code",
                    placeholder="KHBR-XXXX-XXXX",
                    type="password",
                )
                submitted = st.form_submit_button(
                    "ចូលប្រើកម្មវិធី",
                    use_container_width=True,
                )

        if submitted:
            existing = _session_cookie_get()
            ok, message, row, token = validate_customer_login(
                name,
                code,
                existing,
                acquire_session=True,
            )
            if ok:
                _session_cookie_set(token)
                _saved_login_set(row["customer_name"], row["access_code_display"])
                st.session_state.customer_authenticated = True
                st.session_state.customer_name = row["customer_name"]
                st.session_state.customer_code = row["access_code_display"]
                st.session_state.customer_session_token = token
                st.rerun()
            else:
                st.error(message)

        # Real clickable links: one locked 50% / 50% row on every phone size.
        st.markdown(
            """
            <div class="social-split">
              <a href="https://www.facebook.com/Khrmra?mibextid=wwXIfr&mibextid=wwXIfr" target="_blank" rel="noopener noreferrer"
                 aria-label="Open KHEMRA Facebook">
                <span class="social-icon">f</span>
                <span>Facebook</span>
              </a>
              <a href="https://t.me/+VC_6B66uwH5hMDE9" target="_blank" rel="noopener noreferrer"
                 aria-label="Open KHEMRA Telegram">
                <span class="social-icon">➤</span>
                <span>Telegram</span>
              </a>
            </div>
            <div class="login-help">
              សូមទាក់ទង Owner ដើម្បីទទួល <strong>Access Code</strong>
              សម្រាប់ចូលប្រើកម្មវិធី។
            </div>
            """,
            unsafe_allow_html=True,
        )


def _copy_card(name, code, expires_text):
    import html
    safe_name = html.escape(str(name))
    safe_code = html.escape(str(code))
    safe_expiry = html.escape(str(expires_text))
    payload = f"Name: {name}\nCode: {code}"
    safe_payload = payload.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
    import streamlit.components.v1 as components
    components.html(
        f"""
        <div style="font-family:Arial,sans-serif;background:#0f172a;color:white;border:1px solid #22d3ee;border-radius:14px;padding:14px;margin:4px 0 10px">
          <div style="font-weight:800;margin-bottom:7px">Name: {safe_name}</div>
          <div style="font-weight:800;margin-bottom:7px">Code: {safe_code}</div>
          <div style="opacity:.8;margin-bottom:10px">Expires: {safe_expiry}</div>
          <button onclick="navigator.clipboard.writeText(`{safe_payload}`).then(()=>this.innerText='✅ COPIED')"
            style="width:100%;padding:11px;border:0;border-radius:9px;background:linear-gradient(90deg,#0284c7,#22d3ee);color:white;font-weight:900">COPY NAME + CODE</button>
        </div>
        """,
        height=176,
    )


def admin_dashboard():
    st.markdown('<div class="hero"><h1>AI KHEMRA BRO</h1><p>PRIVATE OWNER MANAGEMENT</p></div>', unsafe_allow_html=True)
    admin_password = get_admin_password()

    if not st.session_state.get("admin_authenticated", False):
        left, center, right = st.columns([1, 1.25, 1])
        with center:
            st.markdown("### 👑 ម្ចាស់កម្មវិធី")
            with st.form("admin_login_form"):
                username = st.text_input("Username", autocomplete="off")
                password = st.text_input("Password", type="password", autocomplete="off")
                submitted = st.form_submit_button("ចូលគ្រប់គ្រង", use_container_width=True)
            if submitted:
                name_ok = hmac.compare_digest(username.strip().casefold(), get_admin_username().casefold())
                pass_ok = hmac.compare_digest(password, admin_password)
                if name_ok and pass_ok:
                    st.session_state.admin_authenticated = True
                    st.session_state.admin_gate_visible = True
                    _audit("admin_login", username.strip(), "success")
                    st.rerun()
                else:
                    _audit("admin_login_failed", username.strip() or "unknown", "failed")
                    st.error("Username ឬ Password មិនត្រឹមត្រូវ។")
            if st.button("← ត្រឡប់ទៅ Customer Login", key="close_admin_gate", use_container_width=True):
                st.session_state.admin_gate_visible = False
                st.session_state.owner_click_count = 0
                st.rerun()
        return

    top1, top2 = st.columns([4, 1])
    with top1:
        st.success("👑 Owner បានចូលរួច")
    with top2:
        if st.button("ចាកចេញ", key="admin_logout", use_container_width=True):
            _audit("admin_logout", get_admin_username(), "success")
            st.session_state.admin_authenticated = False
            st.session_state.admin_gate_visible = False
            st.session_state.owner_click_count = 0
            st.rerun()

    st.markdown("## ➕ បង្កើត Customer")
    st.caption("Owner ជាអ្នកកំណត់ Access Code ដោយខ្លួនឯង។ Code មួយអាច Login លើ iPhone, Android និង Browser ផ្សេងៗបាន ដោយមិនចងជាមួយឧបករណ៍។")
    with st.form("create_license_form", clear_on_submit=True):
        customer_name = st.text_input("ឈ្មោះអតិថិជន")
        manual_access_code = st.text_input(
            "Access Code ដែល Owner ចង់កំណត់",
            placeholder="ឧ. KHBR-001 ឬ VIP-2026-001",
            help="អាចប្រើ A-Z, 0-9, - និង _។ មិនមាន Auto Generate ទៀតទេ។",
        )
        duration_label = st.selectbox("រយៈពេល", ["7 ថ្ងៃ", "1 ខែ", "3 ខែ", "6 ខែ", "1 ឆ្នាំ"])
        create_clicked = st.form_submit_button("✅ រក្សាទុក Access Code", use_container_width=True)
    if create_clicked:
        days = {"7 ថ្ងៃ": 7, "1 ខែ": 30, "3 ខែ": 90, "6 ខែ": 180, "1 ឆ្នាំ": 365}[duration_label]
        try:
            code, expires, card_until = add_license(customer_name, manual_access_code, days, duration_label)
            st.session_state.new_license_name = normalize_customer_name(customer_name)
            st.session_state.new_license_code = code
            st.session_state.new_license_expiry = _iso(expires)
            st.session_state.new_license_card_until = _iso(card_until)
        except Exception as exc:
            st.error(str(exc))

    card_until = st.session_state.get("new_license_card_until")
    if card_until and _utcnow() < _parse_iso(card_until):
        expiry_text = _parse_iso(st.session_state.new_license_expiry).astimezone().strftime("%Y-%m-%d %H:%M")
        _copy_card(st.session_state.new_license_name, st.session_state.new_license_code, expiry_text)

    st.markdown("## 👥 គ្រប់គ្រងអតិថិជន")
    search = st.text_input("🔎 ស្វែងរកឈ្មោះ ឬ Code", key="license_search")
    rows = license_rows(search)
    if not rows:
        st.info("មិនទាន់មាន Customer។")
    now = _utcnow()
    for row in rows:
        expiry = _parse_iso(row["expires_at"])
        expired = now >= expiry
        online = bool(row["active_session_hash"]) and row["active_session_last_seen"] and (now - _parse_iso(row["active_session_last_seen"])) <= datetime.timedelta(minutes=SESSION_IDLE_MINUTES)
        status = "ផុតកំណត់" if expired else "បានបិទ" if not row["is_active"] else "Online" if online else "Active"
        with st.expander(f"{row['customer_name']} • {row['access_code_display']} • {status}"):
            st.write(f"**ផុតកំណត់:** {expiry.astimezone().strftime('%Y-%m-%d %H:%M')}")
            st.write(f"**Login:** {row['login_count']} ដង")
            st.code(f"Name: {row['customer_name']}\nCode: {row['access_code_display']}", language=None)
            renew_cols = st.columns(5)
            renew_options = [
                ("+7 ថ្ងៃ", 7, "7 ថ្ងៃ"),
                ("+1 ខែ", 30, "1 ខែ"),
                ("+3 ខែ", 90, "3 ខែ"),
                ("+6 ខែ", 180, "6 ខែ"),
                ("+1 ឆ្នាំ", 365, "1 ឆ្នាំ"),
            ]
            for renew_col, (button_label, renew_days, plan_name) in zip(renew_cols, renew_options):
                with renew_col:
                    if st.button(
                        button_label,
                        key=f"renew_{renew_days}_{row['id']}",
                        use_container_width=True,
                    ):
                        renew_license(row["id"], renew_days, plan_name)
                        st.rerun()

            action_left, action_middle, action_right = st.columns(3)
            with action_left:
                label = "បិទ" if row["is_active"] else "បើក"
                if st.button(label, key=f"toggle_{row['id']}", use_container_width=True):
                    update_license_status(row["id"], not bool(row["is_active"]))
                    st.rerun()
            with action_middle:
                if st.button("សម្អាត Session ចាស់", key=f"disconnect_{row['id']}", use_container_width=True):
                    disconnect_license(row["id"])
                    st.rerun()
            with action_right:
                if st.button("🗑️ លុប API Key", key=f"owner_delete_api_{row['id']}", use_container_width=True):
                    with license_connection() as connection:
                        connection.execute(
                            "UPDATE licenses SET saved_api_keys_encrypted='' WHERE id=?",
                            (int(row["id"]),),
                        )
                        connection.commit()
                    _audit(
                        "owner_deleted_customer_api_key",
                        get_admin_username(),
                        f"{row['customer_name']}|{row['access_code_display']}",
                    )
                    st.success("Owner បានលុប API Key របស់ Customer នេះរួច។")
                    st.rerun()

            with st.expander("⚠️ Advanced Delete"):
                confirmation = st.text_input("វាយ DELETE ដើម្បីលុប", key=f"delete_confirm_{row['id']}")
                if st.button("លុបជាអចិន្ត្រៃយ៍", key=f"delete_{row['id']}", disabled=confirmation != "DELETE", use_container_width=True):
                    delete_license(row["id"]); st.rerun()

    with st.expander("🧾 Audit Log"):
        with license_connection() as connection:
            logs = connection.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 100").fetchall()
        for log in logs:
            st.caption(f"{log['event_at']} • {log['event_type']} • {log['actor']} • {log['details']}")


initialize_license_database()
# Compatibility cleanup: remove historical device/session locks created by older versions.
with license_connection() as _lock_cleanup_connection:
    _lock_cleanup_connection.execute(
        "UPDATE licenses SET active_session_hash=NULL, active_session_last_seen=NULL"
    )
    _lock_cleanup_connection.commit()
hidden_owner_trigger()
if st.session_state.get("admin_gate_visible", False) or st.session_state.get("admin_authenticated", False):
    admin_dashboard()
    st.stop()

if not st.session_state.get("customer_authenticated", False):
    # Restore login automatically after refresh, phone restart, or app update.
    saved_name, saved_code = _saved_login_get()
    if saved_code:
        existing_token = _session_cookie_get()
        auto_ok, _, auto_row, auto_token = validate_customer_login(
            saved_name, saved_code, existing_token, acquire_session=False
        )
        if auto_ok:
            _session_cookie_set(auto_token)
            st.session_state.customer_authenticated = True
            st.session_state.customer_name = auto_row["customer_name"]
            st.session_state.customer_code = auto_row["access_code_display"]
            st.session_state.customer_session_token = auto_token
            st.rerun()
        else:
            _saved_login_delete()
            _session_cookie_delete()
    public_login_screen()
    st.stop()

current_token = st.session_state.get("customer_session_token") or _session_cookie_get()
login_ok, login_message, login_row, current_token = validate_customer_login(
    st.session_state.get("customer_name", ""),
    st.session_state.get("customer_code", ""),
    current_token,
    acquire_session=False,
)
if not login_ok:
    _session_cookie_delete()
    for key in ("customer_authenticated", "customer_name", "customer_code", "customer_session_token"):
        st.session_state.pop(key, None)
    st.error(login_message)
    st.rerun()

st.session_state.customer_session_token = current_token
st.caption(f"👤 {login_row['customer_name']}")

# Read this browser's saved key once per Streamlit session.
if "api_keys_manager" not in st.session_state:
    st.session_state.api_keys_manager = load_private_api_keys()

# Defaults are per user/session; no user's working data is shared with another.
for state_key, default_value in {
    "target_language": "Khmer (ខ្មែរ)",
    "translation_style": "🔴 Chinese Drama Pro",
    "model_selector": "gemini-3.5-flash-lite",
    "lite_mode": True,
    "api_saved_notice": False,
}.items():
    if state_key not in st.session_state:
        st.session_state[state_key] = default_value

with st.container(key="api_menu_container"):
    with st.popover("☰", help="API Key និងការកំណត់កម្មវិធី"):
        st.markdown("### ⚙️ ការកំណត់")

        # Private subscription status for the current authenticated customer.
        private_expiry = _parse_iso(login_row["expires_at"]).astimezone()
        private_plan = str(dict(login_row).get("plan_label") or "កញ្ចប់សមាជិក")
        private_now = _utcnow()
        private_active = bool(login_row["is_active"]) and private_now < _parse_iso(login_row["expires_at"])

        st.markdown("#### 📅 កញ្ចប់របស់អ្នក")
        render_private_subscription_countdown(private_expiry, private_plan)
        if not private_active:
            st.error("❌ កញ្ចប់បានផុតកំណត់។ សូមទាក់ទង Owner ដើម្បីបន្តសិទ្ធិ។")

        st.divider()
        st.selectbox("🌍 Target Language", ["Khmer (ខ្មែរ)"], key="target_language")
        st.radio(
            "🎭 Translation Style",
            ["🔴 Chinese Drama Pro", "⚪ Whisper Timestamp Sync", "⚪ Standard"],
            key="translation_style",
        )
        st.selectbox(
            "🤖 Gemini Model",
            [
                "gemini-3.5-flash-lite",
                "gemini-3.6-flash",
                "gemini-3.5-flash",
                "gemini-flash-latest",
            ],
            key="model_selector",
            help="App នឹងសាកម៉ូឌែលបម្រុងដោយស្វ័យប្រវត្តិ ប្រសិនបើម៉ូឌែលមួយ 404 ឬមិនអាចប្រើបាន។",
        )
        st.toggle("📶 4G Lite Mode", key="lite_mode")

        # API management stays at the bottom of Settings so it never occupies
        # the main translation workspace.
        st.divider()
        st.markdown("#### 🔑 Gemini API Key")
        st.caption(
            "API Key ត្រូវបានអ៊ិនគ្រីប និងរក្សាទុកជាមួយគណនីអ្នក។ "
            "អាចដាក់ច្រើនសោ ដោយមួយបន្ទាត់មួយសោ។"
        )
        st.text_area(
            "Gemini API Key",
            height=76,
            placeholder="AIza...",
            key="api_keys_manager",
            label_visibility="collapsed",
            help="បើសោមួយ quota ពេញ App នឹងសាកសោបន្ទាប់។",
        )

        if st.button("💾 រក្សាទុក API Key", key="save_api_keys", use_container_width=True):
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

        current_keys = [
            line.strip()
            for line in st.session_state.get("api_keys_manager", "").splitlines()
            if line.strip()
        ]
        if current_keys:
            st.success(f"✅ API Key ត្រៀមប្រើ៖ {len(current_keys)}")
        else:
            st.caption("មិនទាន់មាន API Key។ អ្នកនៅតែអាចបើកមើលកម្មវិធីបាន។")

        st.divider()
        if st.button("ចាកចេញ", key="customer_logout", use_container_width=True):
            release_customer_session(st.session_state.get("customer_code", ""), current_token)
            _session_cookie_delete()
            clear_private_user_session()
            for key in ("customer_authenticated", "customer_name", "customer_code", "customer_session_token"):
                st.session_state.pop(key, None)
            st.rerun()

api_keys_text = st.session_state.get("api_keys_manager", "")
valid_api_keys = [line.strip() for line in api_keys_text.splitlines() if line.strip()]
api_key = valid_api_keys[0] if valid_api_keys else ""
translation_style = st.session_state.translation_style
model = st.session_state.model_selector
lite_mode = st.session_state.lite_mode
max_mb = 60 if lite_mode else 150

if not valid_api_keys:
    st.warning("🔐 មិនទាន់មាន Gemini API Key — សូមបញ្ចូលក្នុង ☰ Settings ដើម្បីបកប្រែអក្សរទៅជាភាសាខ្មែរ។")

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
        help="MP4 ត្រូវបានណែនាំ។ App នឹងបង្រួមវីដេអូទៅ 480p ដោយស្វ័យប្រវត្តិ ដើម្បីកាត់បន្ថយ RAM និងល្បឿនដំណើរការ។",
        key=f"main_video_upload_{st.session_state.video_uploader_version}",
    )

    if uploaded_video is not None:
        source_stem = safe_download_stem(Path(uploaded_video.name).stem, 'khmer_story')
        st.session_state.source_video_stem = source_stem
        if not st.session_state.get('mp3_download_name') or st.session_state.get('mp3_download_name') == 'khmer_story_dubbed':
            suggested_name = f"{source_stem}_khmer"
            st.session_state.mp3_download_name = suggested_name
            st.session_state.mp3_filename_widget = suggested_name

        # Keep the uploaded filename and file size private on-screen.
        # The file is still available internally for validation and processing.
        size_mb = uploaded_video.size / (1024 * 1024)

        if size_mb > max_mb:
            st.error(f"សូមបង្រួមវីដេអូឱ្យតិចជាង {max_mb} MB។")
        else:
            if not lite_mode and st.checkbox("▶️ Video Preview"):
                st.video(uploaded_video)

            if st.button("📝 Generate Khmer SRT", key="generate_srt", use_container_width=True):
                video_path = save_upload(uploaded_video)
                st.session_state.project_temp_files.append(str(video_path))
                progress_bar = st.progress(1)
                progress_text = st.empty()
                started_at = time.time()
                try:
                    progress_text.markdown("🎧 កំពុងទាញសំឡេង និងស្គាល់ពាក្យពីវីដេអូ…")

                    # Stage 1 always works without Gemini: create source SRT once.
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(transcribe_video_to_source_srt, video_path)
                        while not future.done():
                            elapsed = time.time() - started_at
                            percent = min(58, max(2, int((elapsed / max(25.0, 20.0 + size_mb * 2.0)) * 58)))
                            minutes, seconds = divmod(int(elapsed), 60)
                            progress_bar.progress(percent)
                            progress_text.markdown(f"### ⏱️ {percent}% • {minutes:02d}:{seconds:02d}<br>🎧 កំពុងស្គាល់សំឡេង…", unsafe_allow_html=True)
                            time.sleep(0.4)
                        cues, source_srt = future.result()

                    st.session_state.source_srt_text = source_srt

                    if valid_api_keys:
                        progress_bar.progress(62)
                        progress_text.markdown("### ⏱️ 62%<br>🌐 កំពុងបកប្រែទៅភាសាខ្មែរ…", unsafe_allow_html=True)
                        try:
                            with ThreadPoolExecutor(max_workers=1) as executor:
                                future = executor.submit(video_to_srt, video_path, valid_api_keys, model, cues)
                                while not future.done():
                                    elapsed = time.time() - started_at
                                    percent = min(96, 62 + int((elapsed / max(40.0, 30.0 + size_mb * 2.5)) * 34))
                                    minutes, seconds = divmod(int(elapsed), 60)
                                    progress_bar.progress(percent)
                                    progress_text.markdown(f"### ⏱️ {percent}% • {minutes:02d}:{seconds:02d}<br>🌐 កំពុងបកប្រែទៅភាសាខ្មែរ…", unsafe_allow_html=True)
                                    time.sleep(0.5)
                                generated_srt = future.result()
                            notice = "✅ Khmer SRT បានបង្កើតរួចរាល់។"
                        except Exception as translation_exc:
                            # Never discard Whisper output when Gemini quota/key fails.
                            generated_srt = source_srt
                            notice = (
                                "⚠️ Whisper បានបង្កើត Source SRT រួច ប៉ុន្តែ Gemini មិនអាចបកប្រែបាន។ "
                                + friendly_ai_error(translation_exc, len(valid_api_keys))
                            )
                    else:
                        generated_srt = source_srt
                        notice = "⚠️ បានបង្កើត Source SRT រួច។ ដាក់ Gemini API Key ក្នុង Settings ដើម្បីបកប្រែទៅខ្មែរ។"

                    st.session_state.srt_text = generated_srt
                    st.session_state.main_srt_editor = generated_srt
                    st.session_state.pending_srt = ""
                    st.session_state.audio_bytes = None
                    st.session_state.workflow_notice = notice
                    progress_bar.progress(100)
                    time.sleep(0.25)
                    progress_bar.empty()
                    progress_text.empty()
                    st.rerun()

                except Exception as exc:
                    progress_bar.empty()
                    progress_text.empty()
                    st.error(f"❌ ដំណើរការវីដេអូមិនបាន៖ {exc}")
                finally:
                    video_path.unlink(missing_ok=True)

    st.subheader("Generated SRT")
    workflow_notice = st.session_state.pop("workflow_notice", "")
    if workflow_notice:
        if workflow_notice.startswith("✅"):
            st.success(workflow_notice)
        else:
            st.warning(workflow_notice)
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
                    ("\ufeff" + st.session_state.srt_text).encode("utf-8"),
                    f"{safe_download_stem(st.session_state.get('source_video_stem'), 'khmer_story')}_subtitle.srt",
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
        if not st.session_state.get("mp3_filename_widget"):
            st.session_state.mp3_filename_widget = st.session_state.get(
                "mp3_download_name", "khmer_story_dubbed"
            )
        st.text_input(
            "✏️ ឈ្មោះឯកសារ MP3",
            key="mp3_filename_widget",
            placeholder="ឧទាហរណ៍៖ រឿងភាគទី១_សំឡេងខ្មែរ",
            help="អ្នកអាចកែឈ្មោះឯកសារមុនចុច Download។",
        )
        st.session_state.mp3_download_name = st.session_state.mp3_filename_widget
        st.audio(st.session_state.audio_bytes, format="audio/mp3")
        download_stem = safe_download_stem(
            st.session_state.get("mp3_filename_widget"),
            fallback="khmer_story_dubbed",
        )
        st.download_button(
            "⬇️ ទាញយកសំឡេង MP3",
            st.session_state.audio_bytes,
            f"{download_stem}.mp3",
            "audio/mpeg",
            use_container_width=True,
        )

    def _clear_current_project():
        _reset_project_workspace()
        st.session_state.project_temp_files = []
        st.session_state.srt_text = ""
        st.session_state.pending_srt = ""
        st.session_state.audio_bytes = None
        st.session_state.audio_job_pending = False
        st.session_state.pending_editor_update = ""
        st.session_state.source_video_stem = "khmer_story"
        st.session_state.mp3_download_name = "khmer_story_dubbed"
        st.session_state.mp3_filename_widget = "khmer_story_dubbed"
        st.session_state.main_srt_editor = ""
        st.session_state.source_srt_text = ""
        st.session_state.speech_tab_audio_bytes = None
        st.session_state.text_tab_audio_bytes = None
        st.session_state.video_uploader_version = int(st.session_state.get("video_uploader_version", 0)) + 1

    st.markdown('<div class="clear-wrap">', unsafe_allow_html=True)
    st.button(
        "🗑️ សម្អាត (Clear Video Project)",
        key="clear_project",
        on_click=_clear_current_project,
        use_container_width=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with tab_translate:
    st.header("AI Subtitle Translator")
    st.info("បិទភ្ជាប់ Chinese SRT ហើយបកប្រែទៅ Khmer SRT ជាភាសាខ្មែរធម្មជាតិ ស្អាតសម្រាប់ទស្សនិកជនទូទៅ និងរក្សា timestamp ដើម។")
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
                    response = gemini_generate_with_retry(
                        client, model, TRANSLATE_PROMPT + "\n\nCUES:\n" + payload
                    )
                    for item in parse_json_array(response.text or ""):
                        cue_id = int(item.get("id"))
                        tag = str(item.get("tag", "M")).upper()
                        if tag not in VOICE_PROFILES:
                            tag = "M_ADULT"
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
        "Khmer SRT with [BOY] [GIRL] [M_YOUNG] [F_YOUNG] [M_ADULT] [F_ADULT] [M_OLD] [F_OLD] [M_THINK] [F_THINK] [NARRATOR_M] [NARRATOR_F]",
        height=360,
        key="speech_srt_input",
    )
    if st.button("🎧 Create MP3", key="srt_to_speech_btn"):
        if not speech_srt.strip():
            st.warning("សូមបញ្ចូល Khmer SRT។")
        else:
            try:
                with st.spinner("កំពុងបង្កើតសំឡេង…"):
                    st.session_state.speech_tab_audio_bytes = create_mp3(speech_srt)
                st.success("✅ បង្កើត MP3 រួចរាល់។")
            except Exception as exc:
                st.error(f"❌ {exc}")
    if st.session_state.get("speech_tab_audio_bytes"):
        st.audio(st.session_state.speech_tab_audio_bytes, format="audio/mp3")
        st.download_button(
            "⬇️ ទាញយក MP3",
            st.session_state.speech_tab_audio_bytes,
            "khmer_srt_speech.mp3",
            "audio/mpeg",
            key="download_srt_speech_mp3",
            use_container_width=True,
        )

with tab_text_speech:
    st.header("Text → Speech")
    plain_text = st.text_area("Khmer Text", height=260, key="plain_text_input")
    voice_choice = st.selectbox(
        "Voice",
        ["BOY", "GIRL", "M_YOUNG", "F_YOUNG", "M_ADULT", "F_ADULT", "M_OLD", "F_OLD", "M_THINK", "F_THINK", "NARRATOR_M", "NARRATOR_F"],
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
                    st.session_state.text_tab_audio_bytes = output.read_bytes()
                st.success("✅ បង្កើតសំឡេងរួចរាល់។")
            except Exception as exc:
                st.error(f"❌ {exc}")
    if st.session_state.get("text_tab_audio_bytes"):
        st.audio(st.session_state.text_tab_audio_bytes, format="audio/mp3")
        st.download_button(
            "⬇️ ទាញយក MP3",
            st.session_state.text_tab_audio_bytes,
            "khmer_text_speech.mp3",
            "audio/mpeg",
            key="download_text_speech_mp3",
            use_container_width=True,
        )

st.caption("AI-KHEMRA-BRO • Chinese Story Translation • Mobile-first")
