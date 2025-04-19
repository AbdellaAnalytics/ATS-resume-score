from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PyPDF2 import PdfReader
import docx2txt
import json
import io

app = FastAPI()

# السماح للفرونت إند بالتواصل مع الباك إند
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# تحميل الكلمات المفتاحية من ملف JSON
with open("keywords.json", "r", encoding="utf-8") as f:
    KEYWORDS = json.load(f)

# استخراج النص من ملف PDF
def extract_text_from_pdf(file_data):
    try:
        reader = PdfReader(io.BytesIO(file_data))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        return ""

# استخراج النص من ملف DOCX
def extract_text_from_docx(file_data):
    try:
        with open("temp_uploaded.docx", "wb") as f:
            f.write(file_data)
        return docx2txt.process("temp_uploaded.docx")
    except Exception as e:
        return ""

# حساب السكور من النص
def calculate_score(text):
    text = text.lower()
    total_keywords = 0
    matched_keywords = 0

    for category in KEYWORDS:
        for keyword in KEYWORDS[category]:
            total_keywords += 1
            if keyword.lower() in text:
                matched_keywords += 1

    if total_keywords == 0:
        return 0
    return int((matched_keywords / total_keywords) * 100)

# نقطة النهاية لتحليل السيرة الذاتية
@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    file_data = await file.read()
    file_ext = file.filename.split(".")[-1].lower()

    if file_ext == "pdf":
        text = extract_text_from_pdf(file_data)
    elif file_ext in ["docx", "doc"]:
        text = extract_text_from_docx(file_data)
    else:
        return {"error": "Unsupported file format"}

    if not text or len(text.strip()) < 20:
        return {"error": "Failed to extract content. File might be empty or unreadable."}

    ats_score = calculate_score(text)
    return {"ats_score": ats_score}
