from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from docx import Document
from PyPDF2 import PdfReader
import os
import json
import io

app = FastAPI()

# Allow frontend to access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the keywords file
with open("keywords.json", "r", encoding="utf-8") as f:
    KEYWORDS = json.load(f)

def extract_text_from_pdf(file):
    try:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text.lower()
    except Exception as e:
        raise ValueError("Failed to read PDF file.")

def extract_text_from_docx(file):
    try:
        document = Document(file)
        return "\n".join([para.text for para in document.paragraphs]).lower()
    except Exception:
        raise ValueError("Failed to read DOCX file.")

def calculate_score(text: str) -> int:
    score = 0
    total_keywords = 0

    for category_keywords in KEYWORDS.values():
        total_keywords += len(category_keywords)
        for keyword in category_keywords:
            if keyword.lower() in text:
                score += 1

    if total_keywords == 0:
        return 0

    return round((score / total_keywords) * 100)

@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        file_ext = os.path.splitext(file.filename)[-1].lower()

        if file_ext == ".pdf":
            text = extract_text_from_pdf(io.BytesIO(contents))
        elif file_ext == ".docx":
            text = extract_text_from_docx(io.BytesIO(contents))
        else:
            return {"error": "Unsupported file format. Please upload PDF or DOCX."}

        ats_score = calculate_score(text)
        return {"ats_score": ats_score}

    except Exception as e:
        return {"error": str(e)}
