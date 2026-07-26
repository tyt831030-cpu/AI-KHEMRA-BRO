import time
import streamlit as st

st.set_page_config(page_title='AI KHEMRA BRO', page_icon='🎬', layout='wide', initial_sidebar_state='expanded')

st.markdown('''
<style>
.stApp{background:#0b0f17;color:#fff}.hero{background:linear-gradient(145deg,#15151f,#0f1118);border:2px solid #d100ff;border-radius:26px;padding:34px 24px;text-align:center;box-shadow:0 0 30px rgba(209,0,255,.18);margin-bottom:22px}.hero h1{font-size:clamp(32px,6vw,58px);margin:0 0 10px;font-weight:800}.hero p{color:#59d9ff;font-weight:800;letter-spacing:3px;font-size:clamp(13px,2.5vw,20px);margin:0}[data-testid="stSidebar"]{background:#111827;border-right:1px solid #253044}.profile-card{border:2px solid #57d8f5;border-radius:24px;padding:22px;text-align:center;background:#1d2533;margin-bottom:18px}.status-box{border-radius:16px;padding:18px;margin:12px 0 18px;font-size:18px;font-weight:600;background:#102239;border:1px solid #17355a}.success-box{border-radius:16px;padding:18px;margin:12px 0 18px;font-size:18px;background:#075f49;border:1px solid #15d6a1}.stButton>button{width:100%;border:0;border-radius:14px;min-height:54px;font-weight:800;font-size:17px;background:linear-gradient(90deg,#8e1bcc,#e200ff);color:white}.stDownloadButton>button{width:100%;border-radius:14px;min-height:50px;font-weight:700}div[data-testid="stFileUploader"]{background:#eff3f8;border-radius:16px;padding:10px}h1,h2,h3{color:#fff}.small-note{color:#a8b3c7;font-size:13px}
</style>
''', unsafe_allow_html=True)

for k, v in {'srt_text':'', 'generated_audio':False}.items():
    st.session_state.setdefault(k, v)

with st.sidebar:
    st.markdown('''<div class="profile-card"><h2>👋 somevut036</h2><div>ROLE: SOMEVUT036</div><div>🗓️ PLAN: 2027-06-30</div><div><b>⌛ 341 DAYS LEFT</b></div></div>''', unsafe_allow_html=True)
    st.button('🚪 ចាកចេញ (Logout)')
    st.markdown('---')
    st.subheader('🌍 Target Language (ភាសាបកប្រែ)')
    target_language = st.selectbox('ជ្រើសរើសភាសា (Select Language):', ['Khmer (ខ្មែរ)','English','Thai','Vietnamese'])
    st.markdown('---')
    st.subheader('🔑 API Keys Manager')
    api_keys = st.text_area('Paste Gemini API Keys (One per line)', height=120)
    valid_keys = [x.strip() for x in api_keys.splitlines() if x.strip()]
    if valid_keys: st.success(f'✅ កំពុងប្រើប្រាស់ {len(valid_keys)} Keys')
    st.markdown('---')
    st.subheader('🎭 Translation Style')
    st.radio('ជ្រើសរើសទម្រង់បកប្រែ:', ['Chinese Drama Pro (សម្រាប់រឿងចិន)','100% Audio Sync (កំណត់ពេលត្រូវគ្នា)','Standard (ការបកប្រែធម្មតា)'])
    st.markdown('---')
    st.subheader('⚙️ Audio Sync Mode')
    st.radio('កែតម្រូវល្បឿន:', ['Speed Up Only (លឿន)','Speed Up & Slow Down (លឿន និង យឺត)'])
    st.markdown('---')
    st.subheader('🗣️ Voice Mode (របៀបសំឡេង)')
    st.radio('កំណត់សម្រាប់ Tab 1 និង Tab 2:', ['Auto (ប្រុស/ស្រី តាម Tag)','All Male (ប្រុសសុទ្ធ)','All Female (ស្រីសុទ្ធ)'])
    st.markdown('---')
    st.subheader('🧠 AI Model (ម៉ូឌែល AI)')
    st.selectbox('ជ្រើសរើសម៉ូឌែល (Select Model):', ['gemini-2.5-flash','gemini-2.5-pro','gemini-2.0-flash'])

st.markdown('''<div class="hero"><h1>AI KHEMRA BRO</h1><p>GLOBAL AI DUBBING & SUBTITLING WORKSTATION</p></div>''', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(['🎬 AI Video Dubbing','🌐 AI SRT Translator','📜 Subtitle to Speech'])

with tab1:
    st.header('1️⃣ Generate Subtitles (Khmer ខ្មែរ)')

    uploaded_video = st.file_uploader(
        'Upload Video',
        type=['mp4', 'mov', 'mkv', 'avi', 'webm']
    )

    # ប៊ូតុង Generate នឹងបង្ហាញតែពេល Upload វីដេអូរួច
    if uploaded_video is not None:
        st.video(uploaded_video)

        if st.button('🚀 Generate Subtitles (Sync 100%)', key='gen'):
            p = st.progress(0)
            box = st.empty()

            for pct, msg in [
                (15, '⏳ Preparing video...'),
                (35, '⏳ Analyzing audio waveforms...'),
                (60, '🧠 Transcribing speech...'),
                (82, f'🌐 Translating into {target_language}...'),
                (100, '✅ SRT Generation Complete!')
            ]:
                box.markdown(
                    f'<div class="status-box">{msg}</div>',
                    unsafe_allow_html=True
                )
                p.progress(pct)
                time.sleep(.3)

            st.session_state.srt_text = '''1
00:00:00,195 --> 00:00:02,500
[M] ក្រោកឡើង! ពេលនេះយើងត្រូវចេញដំណើរហើយ។

2
00:00:03,209 --> 00:00:06,500
[M] ទោះបីជាមានឧបសគ្គយ៉ាងណា ក៏យើងមិនអាចបោះបង់បានទេ។

3
00:00:09,324 --> 00:00:13,500
[F] ខ្ញុំជឿថា ប្រសិនបើយើងរួមដៃគ្នា យើងនឹងអាចឈ្នះបាន។
'''
            box.markdown(
                '<div class="success-box">✅ SRT Generation Complete!</div>',
                unsafe_allow_html=True
            )
    else:
        st.info('📤 សូម Upload វីដេអូជាមុនសិន។')

    # SRT Editor នឹងបង្ហាញតែពេលមាន SRT
    if st.session_state.srt_text:
        st.subheader('Generated SRT from Video')
        st.session_state.srt_text = st.text_area(
            'កែសម្រួល SRT នៅទីនេះ:',
            value=st.session_state.srt_text,
            height=420
        )

        st.download_button(
            '⬇️ Download SRT',
            st.session_state.srt_text.encode('utf-8'),
            'generated_khmer.srt',
            'application/x-subrip'
        )

        st.markdown('---')
        st.header('2️⃣ AI Dubbing (Edge TTS Studio)')

        if st.button('🎙️ Generate Dubbed Audio (MP3)', key='audio'):
            with st.spinner('កំពុងបង្កើតសំឡេងខ្មែរ...'):
                time.sleep(1)
            st.session_state.generated_audio = True
            st.success(
                '✅ Audio workflow is ready. '
                'Connect Edge TTS logic to export the real MP3.'
            )

    # Download/Status នឹងបង្ហាញតែពេល Audio រួច
    if st.session_state.generated_audio:
        st.info(
            'UI បានត្រៀមរួច។ '
            'ផ្នែកនេះជាកន្លែងភ្ជាប់ Edge TTS សម្រាប់បង្កើត MP3 ពិត។'
        )

    # Clear បង្ហាញតែពេលមាន Project
    if uploaded_video is not None or st.session_state.srt_text:
        if st.button('🗑️ សម្អាត (Clear Video Project)', key='clear'):
            st.session_state.srt_text = ''
            st.session_state.generated_audio = False
            st.rerun()

with tab2:
    st.header('🌐 AI SRT Translator')
    src=st.text_area('Paste original SRT', height=320)
    if st.button('🌐 Translate SRT', key='tr'):
        st.success('✅ Translation UI is ready. Connect Gemini API logic here.') if src.strip() else st.warning('សូមបញ្ចូល SRT ជាមុនសិន។')
    st.text_area('Translated SRT', height=320)

with tab3:
    st.header('📜 Subtitle to Speech')
    speech=st.text_area('Paste Khmer SRT with [M] / [F] tags', height=360)
    st.selectbox('Male Voice',['km-KH-PisethNeural']); st.selectbox('Female Voice',['km-KH-SreymomNeural'])
    if st.button('🎧 Create Speech Audio', key='speech'):
        st.success('✅ Speech generation UI is ready for Edge TTS integration.') if speech.strip() else st.warning('សូមបញ្ចូល SRT ជាមុនសិន។')

st.markdown('<p class="small-note">AI-KHEMRA-BRO • Mobile-first Streamlit interface</p>', unsafe_allow_html=True)
