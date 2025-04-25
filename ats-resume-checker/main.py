from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import docx2txt
import PyPDF2
import tempfile
import os
import re
import math
from typing import Dict, List, Optional
from collections import defaultdict

app = FastAPI(
    title="Smart Resume Scorer",
    version="2.0",
    description="An intelligent resume scoring system with job-specific analysis (spaCy-free version)"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
CONFIG = {
    "max_score": 100,
    "min_score": 10,
    "job_profiles": {
        "software_engineer": {
            "keywords": ["python", "java", "c++", "algorithm", "data structure", 
                        "git", "agile", "debugging", "database", "api"],
            "required_sections": ["experience", "education", "skills", "projects"],
            "weight": {"keywords": 0.4, "sections": 0.3, "experience": 0.3}
        },
        "data_scientist": {
            "keywords": ["python", "machine learning", "statistics", "sql", 
                        "data analysis", "pandas", "numpy", "visualization", "ai"],
            "required_sections": ["experience", "education", "skills", "projects"],
            "weight": {"keywords": 0.5, "sections": 0.2, "experience": 0.3}
        },
        "marketing": {
            "keywords": ["campaign", "social media", "seo", "content", 
                        "branding", "analytics", "strategy", "digital", "market"],
            "required_sections": ["experience", "education", "skills"],
            "weight": {"keywords": 0.3, "sections": 0.4, "experience": 0.3}
        },
        "default": {
            "keywords": [],
            "required_sections": ["experience", "education", "skills"],
            "weight": {"keywords": 0.3, "sections": 0.4, "experience": 0.3}
        }
    },
    "common_section_headers": [
        "experience", "education", "skills", "projects",
        "work history", "professional experience", 
        "technical skills", "certifications"
    ]
}

def extract_text(file: UploadFile) -> str:
    """Extract text from PDF, DOCX, or TXT files with improved error handling"""
    try:
        if file.filename.endswith(".pdf"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(file.file.read())
                tmp_path = tmp.name
            
            text = ""
            try:
                with open(tmp_path, "rb") as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
            except Exception as e:
                raise ValueError(f"PDF parsing error: {str(e)}")
            finally:
                os.unlink(tmp_path)
            return text.strip()
        
        elif file.filename.endswith(".docx"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                tmp.write(file.file.read())
                tmp_path = tmp.name
            
            try:
                text = docx2txt.process(tmp_path)
            except Exception as e:
                raise ValueError(f"DOCX parsing error: {str(e)}")
            finally:
                os.unlink(tmp_path)
            return text.strip()
        
        elif file.filename.endswith(".txt"):
            return (await file.read()).decode("utf-8").strip()
        
        raise HTTPException(status_code=400, detail="Unsupported file format. Supported formats: PDF, DOCX, TXT")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

def analyze_text(text: str) -> Dict:
    """Perform text analysis using regex and simple NLP techniques"""
    text_lower = text.lower()
    
    # Extract sections by looking for headings (text in all caps or with following colon)
    sections = []
    lines = text.split('\n')
    for line in lines:
        clean_line = line.strip()
        if len(clean_line) < 50:  # Likely a heading if short
            # Check for section headers
            if any(header in clean_line.lower() for header in CONFIG["common_section_headers"]):
                section_name = clean_line.split(':')[0].strip().lower()
                sections.append(section_name)
            # Check ALL CAPS headings
            elif clean_line.isupper() and len(clean_line.split()) < 5:
                sections.append(clean_line.lower())
    
    # Extract skills by looking for common patterns
    skills = set()
    skill_patterns = [
        r"(?:proficient in|skilled in|expertise in|skills?)[:;\s]*(.*?)(?:\n|\.|$)",
        r"(?:technical skills?|programming languages?)[:;\s]*(.*?)(?:\n|\.|$)"
    ]
    for pattern in skill_patterns:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            # Split skills by commas, slashes, etc.
            for skill in re.split(r'[,/;]', match):
                clean_skill = skill.strip()
                if clean_skill and len(clean_skill.split()) < 4:  # Skip long phrases
                    skills.add(clean_skill)
    
    # Count word frequency for important terms
    words = re.findall(r'\b\w+\b', text_lower)
    word_freq = defaultdict(int)
    for word in words:
        if len(word) > 3:  # Ignore short words
            word_freq[word] += 1
    
    return {
        "word_count": len(words),
        "sections": list(set(sections)),  # Remove duplicates
        "skills": list(skills),
        "word_freq": dict(word_freq),
        "readability": calculate_readability(text)
    }

def calculate_readability(text: str) -> float:
    """Calculate Flesch Reading Ease score without complex NLP"""
    sentences = [s.strip() for s in re.split(r'[.!?]', text) if s.strip()]
    words = [w for w in re.findall(r'\b\w+\b', text.lower()) if w]
    
    if not sentences or not words:
        return 0
    
    avg_sentence_length = len(words) / len(sentences)
    syllables = sum([count_syllables(word) for word in words])
    avg_syllables = syllables / len(words)
    
    return 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables)

def count_syllables(word: str) -> int:
    """Approximate syllable counting without NLP"""
    word = word.lower().strip(".:;?!")
    if len(word) <= 3:
        return 1
    
    vowels = "aeiouy"
    count = 0
    prev_char_was_vowel = False
    
    for char in word:
        if char in vowels and not prev_char_was_vowel:
            count += 1
            prev_char_was_vowel = True
        else:
            prev_char_was_vowel = False
    
    # Adjust for common endings
    if word.endswith(('es', 'ed')) and not word.endswith(('ses', 'sed', 'xes', 'xed')):
        count -= 1
    
    return max(1, count)

def calculate_job_specific_score(text: str, analysis: Dict, job_profile: str) -> int:
    """Calculate score based on specific job requirements"""
    profile = CONFIG["job_profiles"].get(job_profile, CONFIG["job_profiles"]["default"])
    text_lower = text.lower()
    score = 0
    
    # Section coverage (30%)
    section_score = 0
    found_sections = [section for section in profile["required_sections"] 
                     if any(s in " ".join(analysis["sections"]) for s in [section, f"{section}s"])]
    section_coverage = len(found_sections) / len(profile["required_sections"])
    section_score = section_coverage * 30 * profile["weight"]["sections"]
    
    # Keyword matching (40%)
    keyword_score = 0
    if profile["keywords"]:
        # Check both in skills and full text
        found_in_skills = sum(1 for kw in profile["keywords"] 
                            if any(kw in skill for skill in analysis["skills"]))
        found_in_text = sum(1 for kw in profile["keywords"] if kw in text_lower)
        found_keywords = max(found_in_skills, found_in_text)
        
        keyword_coverage = found_keywords / len(profile["keywords"])
        keyword_score = keyword_coverage * 40 * profile["weight"]["keywords"]
    
    # Experience quality (30%)
    experience_score = 0
    experience_phrases = [
        "years", "experience", "worked", "developed", "managed",
        "led", "created", "implemented", "achieved", "improved"
    ]
    experience_matches = sum(1 for phrase in experience_phrases if phrase in text_lower)
    experience_score = min(experience_matches, 10) * 3 * profile["weight"]["experience"]
    
    # Combine scores
    total_score = section_score + keyword_score + experience_score
    
    # Adjust for document quality
    quality_factor = min(analysis["word_count"] / 500, 1)  # Normalize based on length
    final_score = total_score * quality_factor
    
    # Ensure score is within bounds
    return min(max(round(final_score), CONFIG["min_score"]), CONFIG["max_score"])

def generate_feedback(score: int, analysis: Dict, job_profile: str) -> Dict:
    """Generate constructive feedback based on the analysis"""
    profile = CONFIG["job_profiles"].get(job_profile, CONFIG["job_profiles"]["default"])
    feedback = {
        "score": score,
        "strengths": [],
        "improvements": [],
        "job_profile": job_profile
    }
    
    # Check sections
    found_sections = [section for section in profile["required_sections"] 
                     if any(s in " ".join(analysis["sections"]) for s in [section, f"{section}s"])]
    
    if len(found_sections) == len(profile["required_sections"]):
        feedback["strengths"].append("All important sections are included")
    else:
        missing = set(profile["required_sections"]) - set(found_sections)
        feedback["improvements"].append(f"Add missing sections: {', '.join(missing)}")
    
    # Check keywords
    if profile["keywords"]:
        found_keywords = [kw for kw in profile["keywords"] 
                        if kw in " ".join(analysis["skills"]) or kw in " ".join(analysis["sections"])]
        if found_keywords:
            feedback["strengths"].append(
                f"Contains relevant keywords: {', '.join(found_keywords[:5])}"
                f"{'...' if len(found_keywords) > 5 else ''}"
            )
        
        if len(found_keywords) < len(profile["keywords"]) / 2:
            feedback["improvements"].append(
                f"Include more {job_profile.replace('_', ' ')} keywords like: "
                f"{', '.join(list(set(profile['keywords']) - set(found_keywords))[:5])}"
            )
    
    # Check length
    if analysis["word_count"] < 200:
        feedback["improvements"].append("Resume is too short - consider adding more details about your experience")
    elif analysis["word_count"] > 800:
        feedback["improvements"].append("Resume is too long - consider making it more concise")
    
    # Check readability
    if analysis["readability"] < 50:
        feedback["improvements"].append("Improve readability - use simpler sentences and bullet points")
    elif analysis["readability"] > 80:
        feedback["strengths"].append("Excellent readability - easy to understand")
    
    # Add skills feedback
    if analysis["skills"]:
        feedback["strengths"].append(f"Skills identified: {', '.join(analysis['skills'][:5])}{'...' if len(analysis['skills']) > 5 else ''}")
    
    return feedback

@app.post("/score/")
async def score_resume(
    file: UploadFile = File(...),
    job_profile: Optional[str] = "default"
) -> Dict:
    """
    Score a resume with optional job profile matching
    
    Parameters:
    - file: The resume file (PDF, DOCX, or TXT)
    - job_profile: Optional job profile to match against (software_engineer, data_scientist, marketing)
    
    Returns:
    - JSON with score, analysis, and feedback
    """
    try:
        # Validate job profile
        if job_profile not in CONFIG["job_profiles"]:
            job_profile = "default"
        
        # Extract and analyze text
        text = extract_text(file)
        if not text.strip():
            raise HTTPException(status_code=400, detail="Empty file")
        
        analysis = analyze_text(text)
        score = calculate_job_specific_score(text, analysis, job_profile)
        feedback = generate_feedback(score, analysis, job_profile)
        
        return {
            "score": score,
            "job_profile": job_profile,
            "analysis": {
                "word_count": analysis["word_count"],
                "sections_found": analysis["sections"],
                "skills_identified": analysis["skills"][:10],  # Return top 10 skills
                "readability_score": round(analysis["readability"], 1)
            },
            "feedback": feedback
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing resume: {str(e)}")

@app.get("/job_profiles/")
def list_job_profiles() -> List[str]:
    """List available job profiles for scoring"""
    return list(CONFIG["job_profiles"].keys())

@app.get("/")
def health_check() -> Dict:
    """Service health check"""
    return {
        "status": "OK",
        "version": app.version,
        "supported_job_profiles": list(CONFIG["job_profiles"].keys())
    }
