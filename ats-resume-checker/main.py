from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional
import docx2txt
import PyPDF2
import tempfile
import os
import re
import math

app = FastAPI(title="Resume Parser API", version="1.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Job profiles configuration
JOB_PROFILES = {
    "software_engineer": {
        "keywords": ["python", "java", "c++", "javascript", "react", "angular", "node.js", 
                    "docker", "kubernetes", "aws", "azure", "git", "sql", "nosql"],
        "weight": 1.5,
        "required_sections": ["skills", "experience", "education"]
    },
    "data_scientist": {
        "keywords": ["python", "r", "sql", "machine learning", "deep learning", "pytorch", 
                     "tensorflow", "pandas", "numpy", "data visualization", "statistics"],
        "weight": 1.4,
        "required_sections": ["skills", "projects", "education"]
    },
    "generic": {
        "keywords": [],
        "weight": 1.0,
        "required_sections": ["experience", "education", "skills"]
    }
}

def extract_text(file: UploadFile) -> str:
    """Extract text from PDF or DOCX files with error handling"""
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
        
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload PDF or DOCX.")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

def detect_sections(text: str) -> Dict[str, str]:
    """Identify resume sections using pattern matching"""
    section_patterns = {
        "experience": r"(work\s*experience|professional\s*experience|employment\s*history)",
        "education": r"(education|academic\s*background|degrees)",
        "skills": r"(skills|technical\s*skills|competencies)",
        "projects": r"(projects|selected\s*projects|key\s*projects)",
        "certifications": r"(certifications|licenses|training)"
    }
    
    sections = {}
    current_section = None
    current_content = []
    
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        matched = False
        for section, pattern in section_patterns.items():
            if re.search(pattern, line.lower()):
                if current_section:
                    sections[current_section] = ' '.join(current_content)
                current_section = section
                current_content = []
                matched = True
                break
        
        if not matched and current_section:
            current_content.append(line)
    
    if current_section:
        sections[current_section] = ' '.join(current_content)
    
    return sections

def analyze_structure(text: str) -> Dict[str, int]:
    """Analyze resume structure and formatting"""
    return {
        "bullet_points": len(re.findall(r"[-•\u2022]", text)),
        "numbers": len(re.findall(r"\b\d{4}\b|\d+\s+years?", text.lower())),
        "word_count": len(text.split()),
        "paragraph_count": len(re.findall(r"\n\s*\n", text)) + 1
    }

def calculate_score(text: str, job_profile: str = "generic") -> Dict[str, any]:
    """Calculate resume score with comprehensive metrics"""
    if job_profile not in JOB_PROFILES:
        job_profile = "generic"
    
    profile = JOB_PROFILES[job_profile]
    sections = detect_sections(text)
    structure = analyze_structure(text)
    
    # Section score (0-50)
    present_sections = [s for s in profile["required_sections"] if s in sections]
    section_score = (len(present_sections) / len(profile["required_sections"])) * 50
    
    # Keyword score (0-40)
    text_lower = text.lower()
    matched_keywords = [kw for kw in profile["keywords"] if kw in text_lower]
    keyword_score = min((len(matched_keywords) / len(profile["keywords"])) * 40, 40) if profile["keywords"] else 0
    
    # Experience score (0-20)
    year_matches = re.findall(r"(\d+)\s+years?", text_lower)
    experience_score = min(sum(int(y) for y in year_matches) * 2, 20) if year_matches else 0
    
    # Formatting score (0-15)
    formatting_score = 0
    if structure["bullet_points"] >= 5:
        formatting_score += 5
    if structure["numbers"] >= 3:
        formatting_score += 5
    if 300 <= structure["word_count"] <= 1000:
        formatting_score += 5
    
    # Combine scores with weights
    base_score = (
        section_score * 0.3 +
        keyword_score * 0.4 +
        experience_score * 0.2 +
        formatting_score * 0.1
    )
    
    # Apply job profile weight
    weighted_score = min(base_score * profile["weight"], 100)
    
    # Prepare recommendations
    recommendations = []
    missing_sections = [s for s in profile["required_sections"] if s not in sections]
    if missing_sections:
        recommendations.append(f"Add missing sections: {', '.join(missing_sections)}")
    if structure["bullet_points"] < 3:
        recommendations.append("Use more bullet points for better readability")
    
    return {
        "ats_score": round(weighted_score),
        "job_profile": job_profile,
        "score_breakdown": {
            "section_score": round(section_score),
            "keyword_score": round(keyword_score),
            "experience_score": round(experience_score),
            "formatting_score": round(formatting_score)
        },
        "recommendations": recommendations,
        "matched_keywords": matched_keywords
    }

@app.post("/analyze-resume/")
async def analyze_resume(file: UploadFile = File(...), job_profile: str = "generic"):
    """Endpoint to analyze and score a resume"""
    try:
        text = extract_text(file)
        if not text.strip():
            raise HTTPException(status_code=400, detail="The file appears to be empty or couldn't be read")
        
        return calculate_score(text, job_profile.lower())
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/job-profiles/")
async def list_job_profiles():
    """List available job profiles for scoring"""
    return {
        "available_profiles": list(JOB_PROFILES.keys()),
        "description": "Specify one of these in the 'job_profile' parameter when analyzing a resume"
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
