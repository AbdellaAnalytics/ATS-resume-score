import os
import re
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from PyPDF2 import PdfReader
import docx2txt
from typing import List
from collections import Counter

app = FastAPI()

# السماح للفرونت إند بالاتصال
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# كلمات مفتاحية تغطي معظم الوظائف
ALL_KEYWORDS = [
    "data analysis", "python", "sql", "excel", "power bi", "tableau", "machine learning",
    "accounting", "finance", "budgeting", "forecasting", "tax", "reconciliation",
    "sales", "marketing", "seo", "content creation", "social media", "branding",
    "project management", "agile", "scrum", "jira", "kanban",
    "supply chain", "logistics", "inventory", "procurement",
    "customer service", "crm", "support", "communication",
    "web development", "html", "css", "javascript", "react", "django", "flask",
    "human resources", "recruitment", "training", "onboarding",
    "german", "arabic", "english", "translation", "language skills",
    "problem solving", "teamwork", "leadership", "time management", "adaptability"
]

def extract_text_from_pdf(file) -> str:
    try:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception:
        return ""

def extract_text_from_docx(file) -> str:
    try:
        return docx2txt.process(file)
    except Exception:
        return ""

def calculate_score(resume_text: str, keywords: List[str]) -> int:
    resume_text_lower = resume_text.lower()
    total_keywords = len(keywords)
    matched_keywords = sum(1 for word in keywords if word.lower() in resume_text_lower)
    score = int((matched_keywords / total_keywords) * 100) if total_keywords else 0
    return score

@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    try:
        if file.filename.endswith(".pdf"):
            resume_text = extract_text_from_pdf(file.file)
        elif file.filename.endswith(".docx"):
            resume_text = extract_text_from_docx(file.file)
        else:
            return {"error": "Unsupported file type"}

        if not resume_text.strip():
            return {"error": "Failed to extract text from file."}

        # حساب السكور
        ats_score = calculate_score(resume_text, ALL_KEYWORDS)

        # نقاط القوة والكلمات الموجودة
        matched = [kw for kw in ALL_KEYWORDS if kw.lower() in resume_text.lower()]
        missing = [kw for kw in ALL_KEYWORDS if kw.lower() not in resume_text.lower()]

        return {
            "ats_score": ats_score,
            "summary": resume_text[:1000],
            "matched_keywords": matched,
            "missing_keywords": missing,
            "recommendations": f"Add missing keywords like: {', '.join(missing[:5])}" if missing else "Your resume looks great!"
        }

    except Exception as e:
        return {"error": str(e)}
