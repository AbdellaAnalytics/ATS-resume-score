
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import docx2txt
import PyPDF2
import tempfile
import os
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_text(file: UploadFile):
    if file.filename.endswith(".pdf"):
        pdf_reader = PyPDF2.PdfReader(file.file)
        text = " ".join([
            page.extract_text() for page in pdf_reader.pages
            if page.extract_text()
        ])
    elif file.filename.endswith(".docx"):
        file.file.seek(0)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp.write(file.file.read())
            tmp_path = tmp.name
        text = docx2txt.process(tmp_path)
        os.unlink(tmp_path)
    else:
        text = ""
    return text

def calculate_advanced_score(text: str) -> int:
    text_lower = text.lower()
    score = 0

    # Section keywords
    sections = ["experience", "education", "skills", "projects", "certifications", "summary", "objective"]
    section_matches = sum(1 for section in sections if section in text_lower)
    if section_matches >= 4:
        score += 20

    # Years of experience
    if re.search(r"(\d+\s+years|\bsince\s+\d{4})", text_lower):
        score += 15

    # Technical keywords
    tech_keywords = ["python", "excel", "sql", "power bi", "tableau", "html", "css", "javascript", "sap", "erp"]
    tech_matches = sum(1 for word in tech_keywords if word in text_lower)
    if tech_matches >= 5:
        score += 20

    # Resume length
    word_count = len(text.split())
    if 400 <= word_count <= 1000:
        score += 15

    # Formatting & bullet points
    bullet_points = len(re.findall(r"[-•\u2022]", text))
    numbers = len(re.findall(r"\b\d{4}\b|\d+\syears", text_lower))
    if bullet_points >= 5 or numbers >= 3:
        score += 20

    # Max 90%
    return min(score, 90)

@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    print("📄 File received:", file.filename)
    file.file.seek(0)
    text = extract_text(file)
    print("📝 Extracted text:", text[:500])

    if not text:
        return {"error": "Could not read file."}

    score = calculate_advanced_score(text)
    return {
        "ats_score": score
    }

@app.get("/")
def root():
    return {"message": "Advanced ATS Resume Score API is running."}
