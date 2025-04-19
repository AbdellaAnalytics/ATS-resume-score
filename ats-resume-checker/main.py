from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import docx2txt
from PyPDF2 import PdfReader
import os
from langdetect import detect

app = FastAPI()

# للسماح بالاتصال من الواجهة
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# الكلمات المفتاحية العامة
ENGLISH_KEYWORDS = [
    "data analysis", "Excel", "Python", "Power BI", "SQL", "dashboard",
    "KPI", "visualization", "report", "insights", "business intelligence"
]

ARABIC_KEYWORDS = [
    "تحليل البيانات", "إكسل", "باور بي آي", "بايثون", "تقارير", "مؤشرات الأداء",
    "عرض مرئي", "مخططات", "نظام المحاسبة", "تحليل"
]

def extract_text(file: UploadFile):
    ext = file.filename.lower().split('.')[-1]
    if ext == 'pdf':
        pdf = PdfReader(file.file)
        text = ''
        for page in pdf.pages:
            text += page.extract_text() or ''
    elif ext == 'docx':
        temp_path = f"temp_{file.filename}"
        with open(temp_path, "wb") as f:
            f.write(file.file.read())
        text = docx2txt.process(temp_path)
        os.remove(temp_path)
    else:
        text = ''
    return text.strip()

@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    try:
        text = extract_text(file)
        language = detect(text) if text else "unknown"
        keywords = ARABIC_KEYWORDS if language == "ar" else ENGLISH_KEYWORDS
        text_lower = text.lower()

        matched_keywords = [kw for kw in keywords if kw.lower() in text_lower]
        score = int((len(matched_keywords) / len(keywords)) * 100)

        return {
            "ats_score": score,
            "matched_keywords": matched_keywords,
            "language": language
        }

    except Exception as e:
        return {"error": str(e)}
