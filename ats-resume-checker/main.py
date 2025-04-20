from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional
import docx2txt
import PyPDF2
import tempfile
import os
import re
from collections import defaultdict
import spacy
import math

app = FastAPI()

# Load English language model for NLP processing
try:
    nlp = spacy.load("en_core_web_sm")
except:
    raise ImportError("Please install the English language model: python -m spacy download en_core_web_sm")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Job profiles with specific keywords and weights
JOB_PROFILES = {
    "software_engineer": {
        "keywords": ["python", "java", "c++", "javascript", "react", "angular", "node.js", 
                    "docker", "kubernetes", "aws", "azure", "git", "sql", "nosql", 
                    "rest api", "microservices", "agile", "scrum"],
        "weight": 1.5,
        "required_sections": ["skills", "experience", "education"]
    },
    "data_scientist": {
        "keywords": ["python", "r", "sql", "machine learning", "deep learning", "pytorch", 
                     "tensorflow", "pandas", "numpy", "data visualization", "statistics", 
                     "big data", "hadoop", "spark", "tableau", "power bi"],
        "weight": 1.4,
        "required_sections": ["skills", "projects", "education"]
    },
    "business_analyst": {
        "keywords": ["sql", "excel", "power bi", "tableau", "requirements gathering", 
                     "stakeholder management", "uml", "business process", "agile", 
                     "scrum", "jira", "user stories", "data analysis", "dashboard"],
        "weight": 1.3,
        "required_sections": ["experience", "skills", "education"]
    },
    "marketing_specialist": {
        "keywords": ["digital marketing", "seo", "sem", "social media", "content marketing", 
                    "email marketing", "google analytics", "ppc", "crm", "market research", 
                    "brand management", "adobe creative suite", "copywriting"],
        "weight": 1.2,
        "required_sections": ["experience", "skills"]
    },
    "generic": {
        "keywords": [],
        "weight": 1.0,
        "required_sections": ["experience", "education", "skills"]
    }
}

def extract_text(file: UploadFile) -> str:
    """Extract text from PDF or DOCX files"""
    try:
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
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")

def detect_sections(text: str) -> Dict[str, str]:
    """Detect and extract resume sections using NLP and pattern matching"""
    section_patterns = {
        "experience": r"(work\s*experience|professional\s*experience|employment\s*history)",
        "education": r"(education|academic\s*background|degrees)",
        "skills": r"(skills|technical\s*skills|competencies)",
        "projects": r"(projects|selected\s*projects|key\s*projects)",
        "certifications": r"(certifications|licenses|training)",
        "summary": r"(summary|profile|about\s*me)",
        "objective": r"(objective|career\s*goal)"
    }
    
    sections = {}
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    current_section = None
    current_content = []
    
    for line in lines:
        # Check if line matches any section header
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

def analyze_text_structure(text: str) -> Dict[str, int]:
    """Analyze resume structure and formatting"""
    analysis = {
        "bullet_points": len(re.findall(r"[-•\u2022]", text)),
        "numbers": len(re.findall(r"\b\d{4}\b|\d+\s+years?", text.lower())),
        "action_verbs": len(re.findall(r"\b(developed|implemented|designed|created|led|managed|improved|optimized)\b", text.lower())),
        "word_count": len(text.split()),
        "paragraph_count": len(re.findall(r"\n\s*\n", text)) + 1,
        "line_length_variation": len(set(len(line) for line in text.split('\n')))
    }
    return analysis

def calculate_section_score(sections: Dict[str, str], required_sections: List[str]) -> float:
    """Calculate score based on presence and completeness of sections"""
    score = 0
    max_section_score = 50
    
    # Check for required sections
    present_sections = [s for s in required_sections if s in sections]
    section_presence_score = (len(present_sections) / len(required_sections)) * 30
    
    # Check section content quality
    section_content_score = 0
    for section, content in sections.items():
        content_length = len(content.split())
        if section in ["experience", "projects"] and content_length >= 50:
            section_content_score += 5
        elif section in ["skills", "education"] and content_length >= 20:
            section_content_score += 5
        elif content_length >= 30:
            section_content_score += 5
    
    # Cap the content score
    section_content_score = min(section_content_score, 20)
    
    return min(section_presence_score + section_content_score, max_section_score)

def calculate_keyword_score(text: str, keywords: List[str]) -> float:
    """Calculate score based on keyword matches"""
    if not keywords:
        return 0
    
    text_lower = text.lower()
    matched_keywords = [kw for kw in keywords if kw in text_lower]
    unique_matches = len(set(matched_keywords))
    
    # Score based on percentage of keywords matched with diminishing returns
    coverage = unique_matches / len(keywords)
    if coverage >= 0.8:
        return 40
    elif coverage >= 0.6:
        return 30
    elif coverage >= 0.4:
        return 20
    elif coverage >= 0.2:
        return 10
    return 0

def calculate_experience_score(text: str) -> float:
    """Calculate score based on experience indicators"""
    score = 0
    max_score = 20
    
    # Years of experience
    year_matches = re.findall(r"(\d+)\s+years?", text.lower())
    if year_matches:
        total_years = sum(int(y) for y in year_matches)
        score += min(total_years * 2, 10)  # 1 point per 0.5 years, max 10
    
    # Job positions
    position_pattern = r"\b(senior|lead|manager|director|vp|vice president|head of)\b"
    if re.search(position_pattern, text.lower()):
        score += 5
    
    # Company recognition (simple version)
    company_pattern = r"\b(google|microsoft|amazon|apple|facebook|ibm|oracle)\b"
    if re.search(company_pattern, text.lower()):
        score += 5
    
    return min(score, max_score)

def calculate_education_score(text: str) -> float:
    """Calculate score based on education indicators"""
    score = 0
    max_score = 15
    
    # Degree types
    degree_pattern = r"\b(bachelor|b\.?s\.?|b\.?a\.?|master|m\.?s\.?|m\.?a\.?|ph\.?d\.?|doctorate)\b"
    degrees = re.findall(degree_pattern, text.lower())
    if degrees:
        score += len(degrees) * 3
    
    # University recognition (simple version)
    university_pattern = r"\b(harvard|mit|stanford|oxford|cambridge|caltech|princeton)\b"
    if re.search(university_pattern, text.lower()):
        score += 3
    
    # GPA mention
    if re.search(r"\bgpa\b.*\b[3-4]\.\d", text.lower()):
        score += 3
    
    return min(score, max_score)

def calculate_formatting_score(structure: Dict[str, int]) -> float:
    """Calculate score based on resume formatting and structure"""
    score = 0
    max_score = 15
    
    # Bullet points
    if structure["bullet_points"] >= 5:
        score += 5
    elif structure["bullet_points"] >= 3:
        score += 3
    
    # Action verbs
    if structure["action_verbs"] >= 5:
        score += 5
    elif structure["action_verbs"] >= 3:
        score += 3
    
    # Word count
    if 400 <= structure["word_count"] <= 800:
        score += 3
    elif 300 <= structure["word_count"] < 400 or 800 < structure["word_count"] <= 1200:
        score += 1
    
    # Numbers (quantifiable achievements)
    if structure["numbers"] >= 3:
        score += 2
    
    return min(score, max_score)

def normalize_score(score: float, max_possible: float = 100) -> int:
    """Normalize score to 0-100 range using sigmoid function for better distribution"""
    # Scale to 0-10 range first
    scaled_score = (score / max_possible) * 10
    
    # Apply sigmoid function
    sigmoid = 1 / (1 + math.exp(-scaled_score + 5))
    
    # Scale back to 0-100
    normalized = round(sigmoid * 100)
    
    # Ensure within bounds
    return max(0, min(100, normalized))

def calculate_resume_score(text: str, job_profile: str = "generic") -> Dict[str, any]:
    """Calculate comprehensive resume score for a specific job profile"""
    if job_profile not in JOB_PROFILES:
        job_profile = "generic"
    
    profile = JOB_PROFILES[job_profile]
    sections = detect_sections(text)
    structure = analyze_text_structure(text)
    
    # Calculate component scores
    section_score = calculate_section_score(sections, profile["required_sections"])
    keyword_score = calculate_keyword_score(text, profile["keywords"])
    experience_score = calculate_experience_score(text)
    education_score = calculate_education_score(text)
    formatting_score = calculate_formatting_score(structure)
    
    # Combine scores with weights
    base_score = (
        section_score * 0.25 +
        keyword_score * 0.30 +
        experience_score * 0.20 +
        education_score * 0.15 +
        formatting_score * 0.10
    )
    
    # Apply job profile weight
    weighted_score = base_score * profile["weight"]
    
    # Normalize the score
    final_score = normalize_score(weighted_score)
    
    # Prepare detailed breakdown
    breakdown = {
        "section_score": round(section_score),
        "keyword_score": round(keyword_score),
        "experience_score": round(experience_score),
        "education_score": round(education_score),
        "formatting_score": round(formatting_score),
        "job_profile_weight": profile["weight"],
        "base_score": round(base_score),
        "weighted_score": round(weighted_score)
    }
    
    # Identify missing keywords
    text_lower = text.lower()
    missing_keywords = [kw for kw in profile["keywords"] if kw not in text_lower]
    
    # Identify missing sections
    missing_sections = [s for s in profile["required_sections"] if s not in sections]
    
    # Prepare recommendations
    recommendations = []
    if missing_sections:
        recommendations.append(f"Add missing sections: {', '.join(missing_sections)}")
    if missing_keywords and len(missing_keywords) < 10:
        recommendations.append(f"Consider adding these keywords: {', '.join(missing_keywords[:5])}")
    if structure["action_verbs"] < 3:
        recommendations.append("Include more action verbs (e.g., 'developed', 'managed', 'improved')")
    if structure["bullet_points"] < 3:
        recommendations.append("Use more bullet points for better readability")
    if not structure["numbers"]:
        recommendations.append("Add quantifiable achievements (e.g., 'increased sales by 20%')")
    
    return {
        "ats_score": final_score,
        "job_profile": job_profile,
        "score_breakdown": breakdown,
        "recommendations": recommendations,
        "detected_sections": list(sections.keys())
    }

@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...), job_profile: str = "generic"):
    """Endpoint to upload and score a resume"""
    print(f"📄 File received: {file.filename} for job profile: {job_profile}")
    
    try:
        text = extract_text(file)
        if not text:
            raise HTTPException(status_code=400, detail="Could not extract text from file")
        
        print(f"📝 Extracted text (first 500 chars): {text[:500]}...")
        
        result = calculate_resume_score(text, job_profile.lower())
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/job-profiles/")
async def get_job_profiles():
    """Endpoint to list available job profiles"""
    return {
        "available_profiles": list(JOB_PROFILES.keys()),
        "description": "Use these profile names in the 'job_profile' parameter when uploading a resume"
    }

@app.get("/")
def root():
    return {"message": "Advanced Smart ATS Resume Score API is running."}
