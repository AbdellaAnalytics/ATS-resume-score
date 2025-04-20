from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional
import docx2txt
import PyPDF2
import tempfile
import os
import re
import math

app = FastAPI(title="Smart Resume Analyzer", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enhanced job profiles with weighted keywords
JOB_PROFILES = {
    "generic": {
        "keywords": {
            "communication": ["presentation", "writing", "public speaking", "negotiation"],
            "technical": ["excel", "word", "powerpoint", "outlook"],
            "management": ["leadership", "team management", "project management"]
        },
        "weight": 1.0,
        "required_sections": ["experience", "education", "skills"]
    },
    "software_engineer": {
        "keywords": {
            "programming": ["python", "java", "javascript", "c++", "c#"],
            "web": ["html", "css", "react", "angular", "node.js"],
            "devops": ["docker", "kubernetes", "aws", "azure", "ci/cd"],
            "database": ["sql", "mysql", "mongodb", "postgresql"]
        },
        "weight": 1.2,
        "required_sections": ["experience", "education", "skills", "projects"]
    },
    "data_scientist": {
        "keywords": {
            "analysis": ["python", "r", "pandas", "numpy", "statistics"],
            "ml": ["machine learning", "deep learning", "tensorflow", "pytorch"],
            "visualization": ["matplotlib", "seaborn", "tableau", "power bi"]
        },
        "weight": 1.2,
        "required_sections": ["experience", "education", "skills", "projects"]
    }
}

def extract_text(file: UploadFile) -> str:
    """Improved text extraction with better error handling"""
    try:
        if file.filename.endswith(".pdf"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(file.file.read())
                tmp_path = tmp.name
            
            text = ""
            with open(tmp_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            os.unlink(tmp_path)
            return text.strip()
        
        elif file.filename.endswith(".docx"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                tmp.write(file.file.read())
                tmp_path = tmp.name
            
            text = docx2txt.process(tmp_path)
            os.unlink(tmp_path)
            return text.strip()
        
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload PDF or DOCX.")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

def detect_sections(text: str) -> Dict[str, str]:
    """Enhanced section detection with hierarchical parsing"""
    section_patterns = {
        "contact": r"(contact\s*information|personal\s*details)",
        "summary": r"(summary|profile|about\s*me)",
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
                    sections[current_section] = '\n'.join(current_content).strip()
                current_section = section
                current_content = []
                matched = True
                break
        
        if not matched and current_section:
            current_content.append(line)
    
    if current_section:
        sections[current_section] = '\n'.join(current_content).strip()
    
    return sections

def analyze_content(text: str, sections: Dict[str, str]) -> Dict[str, any]:
    """Comprehensive content analysis with multiple metrics"""
    text_lower = text.lower()
    
    # Experience analysis
    experience_years = 0
    year_matches = re.findall(r"(\d+)\s+years?", text_lower)
    if year_matches:
        experience_years = min(sum(int(y) for y in year_matches), 30)  # Cap at 30 years
    
    # Education analysis
    education_level = 0
    if re.search(r"\b(ph\.?d\.?|doctorate)\b", text_lower):
        education_level = 3
    elif re.search(r"\b(master|m\.?s\.?|m\.?a\.?)\b", text_lower):
        education_level = 2
    elif re.search(r"\b(bachelor|b\.?s\.?|b\.?a\.?)\b", text_lower):
        education_level = 1
    
    # Structure analysis
    bullet_points = len(re.findall(r"[-•\u2022]", text))
    numbers = len(re.findall(r"\b\d{4}\b|\d+\s+years?", text_lower))
    action_verbs = len(re.findall(
        r"\b(developed|implemented|designed|created|led|managed|improved|optimized|increased|reduced)\b", 
        text_lower
    ))
    
    return {
        "experience_years": experience_years,
        "education_level": education_level,
        "bullet_points": bullet_points,
        "numbers": numbers,
        "action_verbs": action_verbs,
        "word_count": len(text.split()),
        "section_word_counts": {k: len(v.split()) for k, v in sections.items()}
    }

def calculate_keyword_score(text: str, keyword_categories: Dict[str, List[str]]) -> Dict[str, any]:
    """Calculate keyword scores with category weighting"""
    text_lower = text.lower()
    results = {"matches": {}, "scores": {}, "total": 0}
    
    for category, keywords in keyword_categories.items():
        matched = [kw for kw in keywords if kw in text_lower]
        results["matches"][category] = matched
        # Score is based on percentage of keywords matched in category
        results["scores"][category] = (len(matched) / len(keywords)) * 100 if keywords else 0
        results["total"] += results["scores"][category]
    
    # Normalize total score to 0-100 range
    if keyword_categories:
        results["total"] = results["total"] / len(keyword_categories)
    
    return results

def calculate_resume_score(text: str, job_profile: str = "generic") -> Dict[str, any]:
    """Smart scoring algorithm with balanced metrics"""
    if job_profile not in JOB_PROFILES:
        job_profile = "generic"
    
    profile = JOB_PROFILES[job_profile]
    sections = detect_sections(text)
    content_analysis = analyze_content(text, sections)
    keyword_analysis = calculate_keyword_score(text, profile["keywords"])
    
    # SECTION SCORE (0-30 points)
    present_sections = [s for s in profile["required_sections"] if s in sections]
    section_score = (len(present_sections) / len(profile["required_sections"])) * 30
    
    # Add points for content in sections
    for section in present_sections:
        if content_analysis["section_word_counts"].get(section, 0) > 30:
            section_score += 2
    
    section_score = min(section_score, 30)
    
    # KEYWORD SCORE (0-30 points)
    keyword_score = min(keyword_analysis["total"] * 0.3, 30)
    
    # EXPERIENCE SCORE (0-20 points)
    experience_score = min(content_analysis["experience_years"] * 0.67, 20)  # 1 point per 1.5 years
    
    # EDUCATION SCORE (0-10 points)
    education_score = content_analysis["education_level"] * 3.33  # 3.33 points per level
    
    # FORMATTING SCORE (0-10 points)
    formatting_score = 0
    if content_analysis["bullet_points"] >= 5:
        formatting_score += 4
    if content_analysis["numbers"] >= 3:
        formatting_score += 3
    if content_analysis["action_verbs"] >= 5:
        formatting_score += 3
    
    # COMBINE SCORES
    base_score = (
        section_score +
        keyword_score +
        experience_score +
        education_score +
        formatting_score
    )
    
    # Apply job profile weight (without making it too harsh)
    weighted_score = base_score * (1 + (profile["weight"] - 1) * 0.5)
    
    # Normalize to 0-100 range using improved sigmoid
    normalized_score = 100 / (1 + math.exp(-0.1 * (weighted_score - 50)))
    
    # Prepare recommendations
    recommendations = []
    missing_sections = [s for s in profile["required_sections"] if s not in sections]
    if missing_sections:
        recommendations.append(f"Add missing sections: {', '.join(missing_sections)}")
    
    if content_analysis["bullet_points"] < 3:
        recommendations.append("Use more bullet points for better readability")
    
    if content_analysis["numbers"] < 2:
        recommendations.append("Include quantifiable achievements (e.g., 'increased sales by 20%')")
    
    if content_analysis["action_verbs"] < 3:
        recommendations.append("Add more action verbs (e.g., 'developed', 'managed', 'improved')")
    
    # Find important missing keywords
    important_missing = []
    for category, matches in keyword_analysis["matches"].items():
        if len(matches) / len(profile["keywords"][category]) < 0.5:  # Less than 50% matched
            example_keywords = profile["keywords"][category][:3]
            important_missing.append(f"{category} (e.g., {', '.join(example_keywords)})")
    
    if important_missing:
        recommendations.append(f"Consider adding keywords related to: {', '.join(important_missing)}")
    
    return {
        "ats_score": round(normalized_score),
        "job_profile": job_profile,
        "score_breakdown": {
            "section_score": round(section_score),
            "keyword_score": round(keyword_score),
            "experience_score": round(experience_score),
            "education_score": round(education_score),
            "formatting_score": round(formatting_score)
        },
        "keyword_matches": keyword_analysis["matches"],
        "recommendations": recommendations,
        "content_analysis": {
            "experience_years": content_analysis["experience_years"],
            "education_level": content_analysis["education_level"],
            "word_count": content_analysis["word_count"]
        }
    }

@app.post("/analyze/")
async def analyze_resume(file: UploadFile = File(...), job_profile: str = "generic"):
    """Enhanced analyze endpoint with better scoring"""
    try:
        text = extract_text(file)
        if not text.strip():
            raise HTTPException(status_code=400, detail="The file appears to be empty")
        
        return calculate_resume_score(text, job_profile.lower())
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")

@app.get("/profiles/")
async def list_profiles():
    """List available job profiles"""
    return {
        "profiles": JOB_PROFILES,
        "default": "generic"
    }

@app.get("/")
def health_check():
    return {"status": "OK", "version": "2.0"}
