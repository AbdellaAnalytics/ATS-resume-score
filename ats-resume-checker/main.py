from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import docx2txt
import PyPDF2
import tempfile
import os
import re
import math

app = FastAPI(title="Simple Resume Scorer", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_text(file: UploadFile) -> str:
    """Extract text from PDF or DOCX files"""
    try:
        if file.filename.endswith(".pdf"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(file.file.read())
                tmp_path = tmp.name
            
            with open(tmp_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                text = " ".join([
                    page.extract_text() for page in pdf_reader.pages
                    if page.extract_text()
                ])
            
            os.unlink(tmp_path)
            return text
        
        elif file.filename.endswith(".docx"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                tmp.write(file.file.read())
                tmp_path = tmp.name
            
            text = docx2txt.process(tmp_path)
            os.unlink(tmp_path)
            return text
        
        raise HTTPException(status_code=400, detail="Unsupported file format")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

def calculate_score(text: str) -> int:
    """Flexible scoring algorithm that gives reasonable scores"""
    text_lower = text.lower()
    
    # Basic checks (0-40 points)
    basic_score = 0
    sections = ["experience", "education", "skills"]
    basic_score += sum(10 for section in sections if section in text_lower)
    
    # Content quality (0-40 points)
    content_score = 0
    word_count = len(text.split())
    if word_count > 200:
        content_score += 20  # Base points for having content
        content_score += min((word_count - 200) // 20, 20)  # Up to 20 more points for length
    
    # Keywords (0-20 points)
    keyword_score = 0
    common_keywords = [
        "experience", "education", "skills", "project", "work", 
        "university", "degree", "certification", "developed", 
        "managed", "achieved", "improved"
    ]
    keyword_score = min(sum(1 for kw in common_keywords if kw in text_lower) * 2, 20)
    
    # Combine scores with flexible weighting
    total_score = basic_score + content_score + keyword_score
    
    # Normalize to 40-90 range (avoiding extremes)
    normalized_score = 40 + (total_score * 0.5)
    
    # Ensure score is within reasonable bounds
    return min(max(round(normalized_score), 40), 90)

@app.post("/score/")
async def score_resume(file: UploadFile = File(...)):
    """Simplified scoring endpoint"""
    try:
        text = extract_text(file)
        if not text.strip():
            raise HTTPException(status_code=400, detail="Empty file")
        
        score = calculate_score(text)
        return {"score": score}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def health_check():
    return {"status": "OK"}
