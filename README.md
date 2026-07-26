# AI KHEMRA BRO

កម្មវិធី Streamlit សម្រាប់បកប្រែវីដេអូទៅជាអក្សររងភាសាខ្មែរ និងបង្កើតសំឡេង MP3 ជាមួយប្រព័ន្ធ Customer License ឯកជន។

## Files

- `app.py` — UI ដើម និងមុខងារ AI ទាំងអស់ ព្រមទាំងប្រព័ន្ធ License
- `requirements.txt` — Python packages
- `packages.txt` — System package (`ffmpeg`)
- `README.md` — សេចក្ដីណែនាំ

## Streamlit Secrets

បើក Streamlit Community Cloud → App settings → Secrets ហើយបញ្ចូល៖

```toml
ADMIN_USERNAME = "KHEMRA"
ADMIN_PASSWORD = "0719067125"
```

សម្រាប់សុវត្ថិភាព កុំដាក់លេខសម្ងាត់នៅក្នុង GitHub repository សាធារណៈ។ អ្នកអាចប្តូរ `ADMIN_PASSWORD` នៅក្នុង Secrets ពេលណាក៏បាន។

## Owner access

1. បើក App ធម្មតា។
2. ចុចសញ្ញាតូចនៅជ្រុងខាងស្តាំលើ 5 ដង។
3. បញ្ចូល Owner username និង password។
4. បង្កើត Customer ដោយជ្រើស 7 ថ្ងៃ, 30 ថ្ងៃ ឬ 1 ឆ្នាំ។
5. ចុច `COPY NAME + CODE` ម្តង ដើម្បី Copy ទាំងឈ្មោះ និងលេខកូដ។

ប្រអប់លេខកូដថ្មីលាក់ដោយស្វ័យប្រវត្តិក្រោយ 24 ម៉ោង ប៉ុន្តែ License នៅតែមានរហូតដល់ថ្ងៃផុតកំណត់។

## Customer access

Customer បញ្ចូលតែ៖

- Name
- Access Code

លេខកូដមួយអាចមាន Active Session តែមួយក្នុងពេលតែមួយ។ បើ Browser មិនមានសកម្មភាពលើស 10 នាទី Session ចាស់ត្រូវបានចាត់ទុកថាផុតសកម្មភាព ហើយអាចចូលពីឧបករណ៍ថ្មីបាន។ Owner ក៏អាចចុច `ផ្តាច់ Session` បាន។

## Deploy

Upload ឯកសារទាំង 4 ទៅ GitHub root ហើយ Deploy `app.py` នៅ Streamlit Community Cloud។

> ចំណាំ៖ SQLite នៅលើ Streamlit Community Cloud អាចត្រូវបាន reset ពេល App redeploy/restart។ សម្រាប់ការលក់ជាផ្លូវការនិងរក្សាទិន្នន័យយូរ គួរប្តូរ Database ទៅ PostgreSQL ឬ Supabase។
