# AI KHEMRA BRO v6.3.3 — Pre-Release Fixed

កំណែនេះបានសម្អាតកំហុសសំខាន់ៗមុន Deploy៖

- លុប `video_to_srt()` ដែលស្ទួន ទុកតែ pipeline មួយ
- ដក Owner password ដែលសរសេរផ្ទាល់ក្នុងកូដ
- ដក Cookie key សាធារណៈដែលសរសេរផ្ទាល់ក្នុងកូដ
- អាន Secrets បានទាំង Streamlit Secrets និង Railway Variables
- បង្កើត local Cookie secret ចៃដន្យជំនួស hard-coded fallback
- កែ Version ទៅ `6.3.3`
- រក្សាស្លាកសំឡេង `[M]`, `[F]`, `[M_THINK]`, `[F_THINK]`
- ត្រួតពិនិត្យ Python syntax និង function ស្ទួនរួច

## ឯកសារដំឡើង

- `app.py`
- `requirements.txt`
- `packages.txt`
- `secrets.example.toml`

## Secrets ត្រូវកំណត់មុនប្រើ Owner Login

ដាក់ក្នុង Streamlit Secrets ឬ Railway Variables៖

```toml
ADMIN_USERNAME = "KHEMRA"
ADMIN_PASSWORD = "លេខសម្ងាត់ខ្លាំងរបស់អ្នក"
COOKIE_SECRET = "សោចៃដន្យវែងយ៉ាងតិច 32 តួ"
LICENSE_PEPPER = "សោចៃដន្យផ្សេងមួយទៀត"
```

កុំ Upload `secrets.example.toml` ជា Secrets ពិតដោយមិនប្ដូរតម្លៃឧទាហរណ៍។

## ដំឡើង

1. ជំនួសឯកសារចាស់ដោយឯកសារក្នុង ZIP នេះ។
2. កំណត់ Variables/Secrets ខាងលើ។
3. Redeploy ឬ Restart។
4. សាក Owner Login → Customer Code → Upload Video → SRT → MP3 មួយជុំ។

## កំណត់សម្គាល់

Syntax និងរចនាសម្ព័ន្ធកូដបានឆ្លងការត្រួតពិនិត្យ។ ការសាក Gemini, Edge-TTS និង Whisper ពេញលេញត្រូវធ្វើនៅលើ Server ដែលមាន Internet និង API Key ពិត។
