from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from PyPDF2 import PdfReader
import docx2txt
import io
import difflib
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔍 كلمات مفتاحية موسعة لجميع التخصصات
KEYWORDS = [
    "excel", "python", "sql", "data analysis", "power bi", "tableau", "dashboard",
    "seo", "google ads", "facebook ads", "branding", "campaign", "email marketing",
    "invoice", "quickbooks", "erp", "reconciliation", "tax", "vat", "ledger",
    "recruitment", "payroll", "employee engagement", "training", "labor law",
    "sales", "crm", "cold calling", "upselling", "b2b", "b2c", "pipeline",
    "customer service", "ticketing", "zendesk", "support", "call center",
    "java", "c++", "html", "css", "javascript", "react", "node.js", "api", "git",
    "project management", "scrum", "kanban", "jira", "trello",
    "teamwork", "communication", "problem solving", "leadership", "multitasking",
    "attention to detail", "adaptability", "presentation", "strategy"
]

# Normalize words by removing punctuation and lowercasing
def normalize(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)  # remove punctuation
    return text

# استخلاص النص من PDF
def extract_text_from_pdf(file_data):
    try:
        reader = PdfReader(file_data)
        return " ".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return ""

# استخلاص النص من DOCX
def extract_text_from_docx(file_data):
    try:
        return docx2txt.process(file_data)
    except Exception:
        return ""

# حساب السكور بالذكاء باستخدام مطابقة تقريبية وتطبيع
def calculate_ats_score(text, threshold=0.8):
    text = normalize(text)
    words = set(text.split())
    matched_keywords = []

    for keyword in KEYWORDS:
        keyword_norm = normalize(keyword)
        matches = difflib.get_close_matches(keyword_norm, words, n=1, cutoff=threshold)
        if matches:
            matched_keywords.append(keyword)

    score = (len(matched_keywords) / len(KEYWORDS)) * 100
    return round(score), matched_keywords

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

        print("\n--- Extracted Text Preview (First 1000 characters) ---\n")
        print(resume_text[:1000])
        print("\n------------------------------------------------------\n")

        score, matched = calculate_ats_score(resume_text)
        return {
            "ats_score": score,
            "matched_keywords": matched,
            "total_keywords": len(KEYWORDS)
        }
    except Exception:
        return {"error": "Something went wrong while processing the resume."}
