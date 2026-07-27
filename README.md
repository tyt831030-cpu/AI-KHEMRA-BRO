# AI KHEMRA BRO v7.1 — Streamlit 4-File Build

ឯកសារដែលត្រូវដាក់ក្នុង GitHub មានតែ 4៖

1. app.py
2. requirements.txt
3. packages.txt
4. README.md

កុំដាក់ Dockerfile សម្រាប់ Streamlit Community Cloud។

## របៀបដំឡើង

- លុបកូដចាស់នៅក្នុងឯកសារទាំង 4
- Upload ឯកសារថ្មីទាំង 4 ទៅ root folder នៃ GitHub repository
- ឈ្មោះឯកសារត្រូវតែដូចខាងលើ ដោយគ្មានលេខក្នុងវង់ក្រចក
- បន្ទាប់មកចូល Streamlit → Manage app → Reboot app

## FFmpeg

- packages.txt ដំឡើង ffmpeg នៅលើ Streamlit Cloud
- requirements.txt មាន imageio-ffmpeg ជា fallback
- app.py ស្វែងរក FFmpeg ដោយស្វ័យប្រវត្តិ

## Main file

Streamlit main file path ត្រូវកំណត់ជា:

app.py
