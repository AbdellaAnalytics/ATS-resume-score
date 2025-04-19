from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from PyPDF2 import PdfReader
import docx2txt
import json
import io

app = FastAPI()

# السماح بالكروس أورجن للفرونت إند
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# تحميل ملف الكلمات المفتاحية الكامل
with open("keywords_full.json", "r", encoding="utf-8") as f:
    KEYWORDS = json.load(f)

# استخراج النص من PDF
def extract_text_from_pdf(file_data):
    try:
        reader = PdfReader(file_data)
        return " ".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        return ""

# استخراج النص من DOCX
def extract_text_from_docx(file_data):
    try:
        return docx2txt.process(file_data)
    except Exception:
        return ""

# دالة حساب السكور
def calculate_ats_score(resume_text):
    resume_text = resume_text.lower()
    total_keywords = 0
    matched_keywords = 0

    for category in KEYWORDS:
        keywords = KEYWORDS[category]
        total_keywords += len(keywords)
        for keyword in keywords:
            if keyword.lower() in resume_text:
                matched_keywords += 1

    if total_keywords == 0:
        return 0
    score = (matched_keywords / total_keywords) * 100
    return round(score)

# مسار رفع السيرة الذاتية
@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    try:
        filename = file.filename.lower()
        contents = await file.read()

        if filename.endswith(".pdf"):
            resume_text = extract_text_from_pdf(io.BytesIO(contents))
        elif filename.endswith(".docx"):
            with open("temp.docx", "wb") as f:
                f.write(contents)
            resume_text = extract_text_from_docx("temp.docx")
        else:
            return {"error": "Unsupported file type. Please upload PDF or DOCX."}

        if not resume_text.strip():
            return {"error": "Failed to extract text from resume."}

        ats_score = calculate_ats_score(resume_text)
        return {"ats_score": ats_score}
    except Exception as e:
        return {"error": "Something went wrong while processing the resume."}
