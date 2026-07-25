import asyncio
import re
import subprocess
import tempfile
import time
from pathlib import Path

import edge_tts
import streamlit as st
from google import genai

st.set_page_config(page_title='AI KHEMRA BRO', page_icon='🎬', layout='centered', initial_sidebar_state='collapsed')

st.markdown('''
<style>
.stApp{background:#080d15;color:#f8fafc}.block-container{max-width:900px;padding-top:1.2rem;padding-bottom:3rem}
.hero{border:2px solid #d900ff;border-radius:24px;padding:26px 18px;text-align:center;background:linear-gradient(145deg,#17171d,#0b1018);box-shadow:0 0 24px rgba(217,0,255,.22);margin-bottom:20px}
.hero h1{font-size:40px;margin:0 0 8px;font-weight:900}.hero p{margin:0;color:#23c8ef;font-weight:800;letter-spacing:1.5px}
.step{background:#111b2a;border:1px solid #26374f;border-radius:16px;padding:14px 16px;margin:12px 0}.ok{background:#073d31;border:1px solid #10b981;border-radius:14px;padding:13px 15px;margin:10px 0}
.stButton>button{width:100%;min-height:50px;border:0;border-radius:13px;color:white;font-weight:850;font-size:16px;background:linear-gradient(90deg,#9b1bd1,#ec00ff)}
.stDownloadButton>button{width:100%;min-height:48px;border-radius:13px;font-weight:800}div[data-testid="stFileUploader"]{background:#eef2f7;border-radius:16px;padding:10px}
div[data-testid="stTextArea"] textarea{background:#182438!important;color:#fff!important;border:1px solid #5a6b82!important;border-radius:12px!important;font-size:16px!important;line-height:1.65!important;font-family:"Noto Sans Khmer","Khmer OS System",Arial,sans-serif!important}
@media(max-width:700px){.hero h1{font-size:31px}.hero p{font-size:11px}.block-container{padding-left:1rem;padding-right:1rem}}
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
'F_THINK':{'voice':SREYMOM,'rate':'-8%','pitch':'-6Hz','volume':'-12%'}}

PROMPT='''You are an expert Chinese-drama subtitle translator for Khmer dubbing.
Listen to all spoken dialogue in the uploaded Chinese video and return valid Khmer SRT only.
Rules:
1. Keep accurate SRT numbering and timestamps.
2. Do not skip short dialogue.
3. Translate into natural spoken Khmer suitable for Chinese drama dubbing.
4. Add exactly one speaker tag at the beginning of every subtitle line.
5. Allowed tags only: [M] [F] [BOY] [GIRL] [OLD_M] [OLD_F] [M_THINK] [F_THINK]
6. No markdown fences or explanations.
7. No Chinese characters in the Khmer dialogue.'''

for key,value in {'srt_text':'','audio_bytes':None}.items():
    if key not in st.session_state: st.session_state[key]=value

def clean_srt(text):
    text=re.sub(r'^```(?:srt)?\s*','',text.strip(),flags=re.I)
    return re.sub(r'\s*```$','',text).strip()

def save_upload(uploaded_file):
    suffix=Path(uploaded_file.name).suffix or '.mp4'
    temp=tempfile.NamedTemporaryFile(delete=False,suffix=suffix)
    temp.write(uploaded_file.getbuffer()); temp.close(); return Path(temp.name)

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
    tag_re=re.compile(r'^\[(M|F|BOY|GIRL|OLD_M|OLD_F|M_THINK|F_THINK)\]\s*',re.I)
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

def create_mp3(srt_text):
    cues=parse_srt(srt_text)
    if not cues: raise ValueError('រកមិនឃើញ SRT និង timestamp ត្រឹមត្រូវទេ។')
    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder); clips=[]
        for index,cue in enumerate(cues):
            clip=root/f'clip_{index:04d}.mp3'; run_async(synthesize(cue['text'],VOICE_PROFILES.get(cue['tag'],VOICE_PROFILES['M']),clip)); clips.append(clip)
        command=['ffmpeg','-y']
        for clip in clips: command.extend(['-i',str(clip)])
        filters=[]; labels=[]
        for index,cue in enumerate(cues):
            duration=max(0.1,(cue['end']-cue['start'])/1000); delay=max(0,cue['start']); label=f'a{index}'
            filters.append(f'[{index}:a]atrim=0:{duration:.3f},asetpts=PTS-STARTPTS,adelay={delay}|{delay}[{label}]'); labels.append(f'[{label}]')
        total=(max(c['end'] for c in cues)+500)/1000
        filters.append(''.join(labels)+f'amix=inputs={len(labels)}:duration=longest:dropout_transition=0,apad=whole_dur={total:.3f},atrim=0:{total:.3f}[out]')
        output=root/'khmer_dubbed.mp3'
        command.extend(['-filter_complex',';'.join(filters),'-map','[out]','-ac','2','-ar','44100','-b:a','128k',str(output)])
        result=subprocess.run(command,capture_output=True,text=True,timeout=600)
        if result.returncode!=0: raise RuntimeError(result.stderr[-1200:] or 'FFmpeg failed.')
        return output.read_bytes()

st.markdown('<div class="hero"><h1>AI KHEMRA BRO</h1><p>UPLOAD CHINESE VIDEO → KHMER SRT → KHMER MP3</p></div>',unsafe_allow_html=True)

with st.expander('⚙️ Settings',expanded=False):
    api_key=st.text_input('Gemini API Key',type='password',placeholder='AIza...')
    model=st.selectbox('AI Model',['gemini-2.5-flash','gemini-2.5-pro'])
    lite_mode=st.toggle('📶 4G Lite Mode',value=True)
    max_mb=60 if lite_mode else 150
    st.caption(f'វីដេអូណែនាំមិនលើស {max_mb} MB')

st.markdown('<div class="step"><b>1️⃣ Upload Chinese Video</b></div>',unsafe_allow_html=True)
uploaded_video=st.file_uploader('📥 ទទួលឯកសារវីដេអូ',type=['mp4','mov','mkv','webm'],help='MP4 ត្រូវបានណែនាំសម្រាប់ 4G និងទូរស័ព្ទ។')

if uploaded_video is not None:
    size_mb=uploaded_video.size/(1024*1024)
    st.markdown(f'<div class="ok">✅ ទទួលវីដេអូរួចរាល់<br>📄 {uploaded_video.name}<br>📦 {size_mb:.1f} MB</div>',unsafe_allow_html=True)
    if size_mb>max_mb: st.error(f'សូមបង្រួមវីដេអូឱ្យតិចជាង {max_mb} MB។')
    else:
        if not lite_mode and st.checkbox('▶️ មើលវីដេអូ Preview'): st.video(uploaded_video)
        if st.button('📝 បង្កើតអក្សរខ្មែរ SRT'):
            if not api_key.strip(): st.error('សូមបញ្ចូល Gemini API Key ក្នុង Settings ជាមុន។')
            else:
                video_path=save_upload(uploaded_video)
                try:
                    with st.status('កំពុងបង្កើតអក្សរខ្មែរ…',expanded=True) as status:
                        st.write('📤 កំពុងផ្ញើវីដេអូទៅ AI…'); st.write('🎧 កំពុងស្ដាប់សំឡេងចិន…'); st.write('🌐 កំពុងបកប្រែទៅភាសាខ្មែរ…')
                        st.session_state.srt_text=video_to_srt(video_path,api_key.strip(),model); st.session_state.audio_bytes=None
                        status.update(label='✅ បង្កើត Khmer SRT រួចរាល់',state='complete')
                except Exception as exc: st.error(f'❌ {exc}')
                finally: video_path.unlink(missing_ok=True)

if st.session_state.srt_text:
    st.markdown('<div class="step"><b>2️⃣ Generated Khmer SRT</b></div>',unsafe_allow_html=True)
    st.session_state.srt_text=st.text_area('អក្សរខ្មែរបង្ហាញនៅទីនេះ ហើយអាចកែបាន',value=st.session_state.srt_text,height=430)
    st.download_button('⬇️ Download Khmer SRT',st.session_state.srt_text.encode('utf-8'),'khmer_story.srt','application/x-subrip')
    st.markdown('<div class="step"><b>3️⃣ Generate Khmer Voice MP3</b></div>',unsafe_allow_html=True)
    if st.button('🎙️ បង្កើតសំឡេងខ្មែរ MP3'):
        try:
            with st.spinner('កំពុងបង្កើតសំឡេង Piseth និង Sreymom…'): st.session_state.audio_bytes=create_mp3(st.session_state.srt_text)
            st.success('✅ បង្កើត MP3 រួចរាល់។')
        except Exception as exc: st.error(f'❌ {exc}')

if st.session_state.audio_bytes:
    st.audio(st.session_state.audio_bytes,format='audio/mp3')
    st.download_button('⬇️ Download Khmer MP3',st.session_state.audio_bytes,'khmer_story_dubbed.mp3','audio/mpeg')

if uploaded_video is not None or st.session_state.srt_text:
    if st.button('🗑️ Clear Project'):
        st.session_state.srt_text=''; st.session_state.audio_bytes=None; st.rerun()

st.caption('AI-KHEMRA-BRO • Chinese Story Translation • Mobile-first')
