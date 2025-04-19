from pathlib import Path
import difflib
import json
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from docx import Document
import PyPDF2

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# تحميل الكلمات المفتاحية من الملف الخارجي
with open("keywords_full.json", "r", encoding="utf-8") as f:
    KEYWORDS = json.load(f)

def extract_text_from_pdf(file_path):
    text = ""
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text

def extract_text_from_docx(file_path):
    doc = Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_text(file_path: Path) -> str:
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext == ".docx":
        return extract_text_from_docx(file_path)
    elif ext == ".doc":
        return extract_text_from_docx(file_path)  # basic fallback
    else:
        raise ValueError("Unsupported file type")

def count_matches(resume_text, keywords_dict, threshold=0.8):
    resume_text_lower = resume_text.lower()
    resume_words = set(resume_text_lower.split())
    all_keywords = set()

    for category in keywords_dict:
        all_keywords.update([kw.lower() for kw in keywords_dict[category]])

    matched_keywords = set()
    for kw in all_keywords:
        matches = difflib.get_close_matches(kw, resume_words, n=1, cutoff=threshold)
        if matches:
            matched_keywords.add(kw)

    score = int((len(matched_keywords) / len(all_keywords)) * 100)
    return score, matched_keywords

@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    try:
        file_location = f"temp_{file.filename}"
        with open(file_location, "wb") as f:
            f.write(await file.read())

        text = extract_text(Path(file_location))
        score, matched = count_matches(text, KEYWORDS)
        return {"ats_score": score, "matched_keywords": list(matched)}

    except Exception as e:
        return {"error": str(e)}
