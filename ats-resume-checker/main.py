# main.py - Improved Version for Resume Scorer Pro

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import docx2txt
import PyPDF2
import tempfile
import os
import re
from typing import List, Dict
import nltk
from nltk.corpus import stopwords

# Ensure NLTK stopwords are available
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

app = FastAPI(title="Resume Scorer Pro", version="1.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
MIN_WORD_COUNT = 100
REQUIRED_SECTIONS = {"experience", "education", "skills"}
KEYWORDS = {
    "tech": ["python", "java", "sql", "aws"],
    "business": ["management", "marketing", "sales"]
}

class AnalysisResult(BaseModel):
    score: int
    industry: str
    strengths: List[str]
    suggestions: List[str]
    metrics: Dict[str, int]

def extract_text(file: UploadFile) -> str:
    try:
        suffix = ".docx" if file.filename.endswith(".docx") else ".pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file.file.read())
            tmp_path = tmp.name

        if file.filename.lower().endswith(".pdf"):
            with open(tmp_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = " ".join(page.extract_text() or "" for page in reader.pages)
        elif file.filename.lower().endswith(".docx"):
            text = docx2txt.process(tmp_path)
        else:
            raise HTTPException(400, "Unsupported file type")

        os.unlink(tmp_path)
        return text.strip()

    except Exception as e:
        raise HTTPException(500, f"File processing error: {str(e)}")

def is_valid_resume(text: str) -> bool:
    word_count = len(text.split())
    if word_count < MIN_WORD_COUNT:
        return False
    found_sections = sum(1 for section in REQUIRED_SECTIONS if section in text.lower())
    return found_sections >= 2

def analyze_resume(text: str) -> AnalysisResult:
    if not is_valid_resume(text):
        raise HTTPException(400, "This file doesn't look like a proper resume.")

    text_lower = text.lower()
    stop_words = set(stopwords.words("english"))

    found_sections = [sec for sec in REQUIRED_SECTIONS if sec in text_lower]
    missing_sections = [sec for sec in REQUIRED_SECTIONS if sec not in found_sections]

    exp_years = len(re.findall(r"(20\d{2}|'\d{2})\s*[-–—]\s*(20\d{2}|'\d{2}|present)", text_lower))

    matched_keywords = []
    industry_scores = {"tech": 0, "business": 0}

    for industry, words in KEYWORDS.items():
        for word in words:
            if re.search(rf"\b{word}\b", text_lower):
                matched_keywords.append(word)
                industry_scores[industry] += 1

    industry = max(industry_scores.items(), key=lambda x: x[1])[0]

    section_score = len(found_sections) * 10
    keyword_score = min(len(matched_keywords) * 2, 20)
    experience_score = min(exp_years * 5, 25)
    numeric_data_score = len(re.findall(r"\d+%|\$?\d+", text_lower)) * 2

    total_score = min(section_score + keyword_score + experience_score + numeric_data_score, 95)
    total_score = max(total_score, 40)

    suggestions = []
    if missing_sections:
        suggestions.append(f"Add missing section(s): {', '.join(missing_sections)}")
    if industry_scores[industry] < 3:
        suggestions.append(f"Add more {industry} keywords (e.g., {', '.join(KEYWORDS[industry][:3])})")
    if exp_years < 2:
        suggestions.append("Include more project/work experience if available")

    return AnalysisResult(
        score=total_score,
        industry=industry,
        strengths=matched_keywords[:5],
        suggestions=suggestions,
        metrics={
            "sections": len(found_sections),
            "keywords": len(matched_keywords),
            "experience_years": exp_years
        }
    )

@app.post("/analyze", response_model=AnalysisResult)
async def analyze(file: UploadFile = File(...)):
    try:
        text = extract_text(file)
        return analyze_resume(text)
    except HTTPException as http_err:
        raise http_err
    except Exception as err:
        raise HTTPException(500, f"Unexpected error: {str(err)}")

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
