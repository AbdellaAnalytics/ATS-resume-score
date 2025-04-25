# main.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import docx2txt
import PyPDF2
import tempfile
import os
import re
from datetime import datetime
from typing import Dict, List, Tuple
import nltk
from nltk.corpus import stopwords
from pydantic import BaseModel

# Initialize NLTK (safe download)
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

app = FastAPI(title="Resume Scorer Pro", version="1.0")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Response Model
class AnalysisResult(BaseModel):
    score: int
    industry: str
    strengths: List[str]
    suggestions: List[str]
    metrics: Dict[str, int]

# Resume Validation
MIN_RESUME_LENGTH = 100  # Minimum words to consider as valid resume
RESUME_SECTIONS = {"experience", "education", "skills"}

def validate_resume(text: str) -> bool:
    """Check if text resembles a resume"""
    word_count = len(text.split())
    if word_count < MIN_RESUME_LENGTH:
        return False
    
    text_lower = text.lower()
    found_sections = sum(1 for section in RESUME_SECTIONS if section in text_lower)
    return found_sections >= 2 or \
           bool(re.search(r"\b(phone|email|contact)\b", text_lower))

# Text Extraction
def extract_text(file: UploadFile) -> str:
    """Safe text extraction from PDF/DOCX"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename[-4:]) as tmp:
            tmp.write(file.file.read())
            tmp_path = tmp.name

        if file.filename.lower().endswith('.pdf'):
            with open(tmp_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = " ".join(page.extract_text() or "" for page in reader.pages)
        elif file.filename.lower().endswith(('.docx', '.doc')):
            text = docx2txt.process(tmp_path)
        else:
            raise HTTPException(400, "Unsupported file type")
            
        os.unlink(tmp_path)
        return text.strip()
    
    except Exception as e:
        raise HTTPException(500, f"File processing error: {str(e)}")

# Analysis Engine
def analyze_resume(text: str) -> AnalysisResult:
    """Core scoring logic"""
    if not validate_resume(text):
        raise HTTPException(400, "Document doesn't appear to be a resume")
    
    text_lower = text.lower()
    stop_words = set(stopwords.words('english'))
    
    # Section Analysis
    sections_found = [s for s in RESUME_SECTIONS if s in text_lower]
    missing_sections = [s for s in RESUME_SECTIONS if s not in sections_found]
    
    # Experience Analysis
    exp_years = len(re.findall(r"(20\d{2}|'\d{2})\s*[-–—]\s*(20\d{2}|'\d{2}|present)", text_lower))
    
    # Keyword Analysis
    keywords = {
        "tech": ["python", "java", "sql", "aws"],
        "business": ["management", "marketing", "sales"]
    }
    matched_keywords = []
    industry_scores = {"tech": 0, "business": 0}
    
    for industry, terms in keywords.items():
        for term in terms:
            if re.search(rf"\b{term}\b", text_lower):
                matched_keywords.append(term)
                industry_scores[industry] += 1
    
    industry = max(industry_scores.items(), key=lambda x: x[1])[0]
    
    # Scoring (100-point scale)
    section_score = len(sections_found) * 10
    keyword_score = min(len(matched_keywords) * 2, 20)
    experience_score = min(exp_years * 5, 25)
    metrics_score = len(re.findall(r"\d+%|\$?\d+", text_lower)) * 2
    
    total_score = min(section_score + keyword_score + experience_score + metrics_score, 95)
    total_score = max(total_score, 40)  # Minimum score
    
    # Suggestions
    suggestions = []
    if missing_sections:
        suggestions.append(f"Add missing section: {', '.join(missing_sections)}")
    if industry_scores[industry] < 3:
        suggestions.append(f"Add more {industry} keywords like: {', '.join(keywords[industry][:3])}")
    if exp_years < 2:
        suggestions.append("Highlight projects if work experience is limited")
    
    return AnalysisResult(
        score=total_score,
        industry=industry,
        strengths=matched_keywords[:5],
        suggestions=suggestions,
        metrics={
            "sections": len(sections_found),
            "keywords": len(matched_keywords),
            "experience_years": exp_years
        }
    )

# API Endpoints
@app.post("/analyze", response_model=AnalysisResult)
async def analyze(file: UploadFile = File(...)):
    try:
        text = extract_text(file)
        return analyze_resume(text)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0"}

# For Render deployment
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
