from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from docx import Document
from PyPDF2 import PdfReader
import json
import difflib
import os
import io

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load keywords from JSON (should be in same directory)
with open("keywords_full.json", "r", encoding="utf-8") as f:
    KEYWORDS = json.load(f)

# Flatten keywords from all categories
ALL_KEYWORDS = set()
for category_keywords in KEYWORDS.values():
    ALL_KEYWORDS.update([kw.lower() for kw in category_keywords])

# Extract text from PDF
def extract_text_from_pdf(file_bytes):
    text = ""
    reader = PdfReader(io.BytesIO(file_bytes))
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text.lower()

# Extract text from DOCX
def extract_text_from_docx(file_bytes):
    with open("temp.docx", "wb") as f:
        f.write(file_bytes)
    doc = Document("temp.docx")
    os.remove("temp.docx")
    return " ".join([para.text for para in doc.paragraphs]).lower()

# Match keywords approximately using difflib
def calculate_score(text, threshold=0.85):
    words = set(text.split())
    matched = set()
    for kw in ALL_KEYWORDS:
        if difflib.get_close_matches(kw, words, n=1, cutoff=threshold):
            matched.add(kw)
    score = int((len(matched) / len(ALL_KEYWORDS)) * 100) if ALL_KEYWORDS else 0
    return score, matched

# API endpoint to analyze resume
@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        ext = file.filename.lower().split(".")[-1]

        if ext == "pdf":
            text = extract_text_from_pdf(contents)
        elif ext == "docx":
            text = extract_text_from_docx(contents)
        else:
            return {"error": "Unsupported file type. Upload PDF or DOCX."}

        if not text or len(text) < 30:
            return {"error": "Unable to extract meaningful content from resume."}

        score, matched = calculate_score(text)
        return {
            "ats_score": score,
            "matched_keywords": sorted(matched),
            "total_keywords": len(ALL_KEYWORDS)
        }
    except Exception as e:
        return {"error": f"Failed to process resume. Error: {str(e)}"}
