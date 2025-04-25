from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import docx2txt
import PyPDF2
import tempfile
import os
import re
from datetime import datetime
from typing import Dict, List, Tuple, Set
import nltk
from nltk.corpus import stopwords, wordnet
from collections import Counter
import difflib

app = FastAPI(title="AI Resume Scorer Pro", version="5.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize NLP resources
nltk.download(['stopwords', 'wordnet', 'punkt'], quiet=True)
STOPWORDS = set(stopwords.words('english'))

# Resume-specific constants
MIN_RESUME_WORDS = 150
RESUME_KEYPHRASES = {"work experience", "professional experience", "education", 
                    "skills", "employment history", "career objective"}

# Industry keywords with synonyms
INDUSTRY_KEYWORDS = {
    "tech": {
        "primary": ["python", "java", "javascript", "c++", "sql"],
        "synonyms": {
            "python": ["python", "py", "django", "flask"],
            "java": ["java", "jvm", "spring", "j2ee"],
            "sql": ["sql", "mysql", "postgresql", "database"]
        }
    },
    "business": {
        "primary": ["management", "strategy", "leadership", "marketing"],
        "synonyms": {
            "management": ["management", "supervision", "administration"],
            "marketing": ["marketing", "advertising", "branding"]
        }
    }
}

def is_resume(text: str) -> bool:
    """Smart detection if document is actually a resume"""
    text_lower = text.lower()
    
    # Check for resume-like structure
    section_count = sum(1 for phrase in RESUME_KEYPHRASES if phrase in text_lower)
    if section_count < 2:
        return False
    
    # Check for personal information patterns
    has_contact = (re.search(r"(phone|mobile|contact)", text_lower) and 
                  re.search(r"\b[\w\.-]+@[\w\.-]+\.\w+\b", text_lower))
    
    # Check for experience/education patterns
    has_timeline = bool(re.search(r"(20\d{2}|'\d{2})\s*[-–—]\s*(20\d{2}|'\d{2}|present)", text_lower))
    
    return has_contact or has_timeline or (section_count >= 3)

def get_synonyms(word: str) -> Set[str]:
    """Get synonyms and similar words using WordNet and manual mappings"""
    synonyms = set()
    
    # Get WordNet synonyms
    for syn in wordnet.synsets(word):
        for lemma in syn.lemmas():
            synonyms.add(lemma.name().lower().replace('_', ' '))
    
    # Add from our manual synonym mappings
    for industry in INDUSTRY_KEYWORDS.values():
        if word in industry["synonyms"]:
            synonyms.update(industry["synonyms"][word])
    
    # Add similar words using difflib
    similar_words = difflib.get_close_matches(word, INDUSTRY_KEYWORDS.keys(), n=2)
    synonyms.update(similar_words)
    
    return synonyms

def extract_text(file: UploadFile) -> str:
    """Extract text with resume validation"""
    try:
        if not file.filename.lower().endswith(('.pdf', '.docx')):
            raise HTTPException(400, "Only PDF and DOCX files are supported")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename[-5:]) as tmp:
            tmp.write(file.file.read())
            tmp_path = tmp.name

        text = ""
        if file.filename.endswith(".pdf"):
            with open(tmp_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = " ".join([page.extract_text() or "" for page in reader.pages])
        else:
            text = docx2txt.process(tmp_path)
        
        os.unlink(tmp_path)
        
        if not is_resume(text):
            raise HTTPException(400, "This doesn't appear to be a resume document")
            
        return text.lower().strip()
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error processing file: {str(e)}")

def analyze_content(text: str) -> Dict:
    """Comprehensive resume analysis with smart scoring"""
    # Section analysis
    sections, missing_sections = analyze_sections(text)
    
    # Experience analysis
    exp_years, position_count, metrics = extract_experience(text)
    
    # Keyword analysis with synonyms
    industry, keyword_matches = analyze_keywords_with_synonyms(text)
    
    # Calculate scores
    section_score = min(len(sections) * 10, 30)  # Max 30
    exp_score = min(exp_years * 2 + position_count * 3 + metrics * 2, 40)  # Max 40
    keyword_score = min(len(keyword_matches) * 2, 20)  # Max 20
    format_score = analyze_formatting(text)  # Max 10
    
    total_score = section_score + exp_score + keyword_score + format_score
    normalized_score = min(max(40 + (total_score * 0.6), 40), 95)  # Scale to 40-95
    
    return {
        "score": round(normalized_score),
        "industry": industry,
        "details": {
            "sections": sections,
            "missing_sections": missing_sections,
            "experience_years": exp_years,
            "positions": position_count,
            "achievements": metrics,
            "keywords": keyword_matches,
            "formatting": format_score
        },
        "suggestions": generate_suggestions(sections, missing_sections, keyword_matches, exp_years, metrics)
    }

def analyze_keywords_with_synonyms(text: str) -> Tuple[str, List[str]]:
    """Industry keyword analysis with synonym support"""
    industry_scores = {}
    all_matches = []
    
    for industry, data in INDUSTRY_KEYWORDS.items():
        score = 0
        matches = []
        
        for primary_word in data["primary"]:
            # Check primary word and all synonyms
            search_terms = {primary_word} | get_synonyms(primary_word)
            for term in search_terms:
                if re.search(rf"\b{term}\b", text):
                    matches.append(primary_word)  # Track the primary keyword
                    score += 1
                    break  # Count each primary word only once
        
        industry_scores[industry] = score
        if matches:
            all_matches.extend(matches)
    
    top_industry = max(industry_scores.items(), key=lambda x: x[1])[0] if industry_scores else "general"
    return top_industry, all_matches

def generate_suggestions(sections, missing_sections, keywords, exp_years, metrics) -> List[str]:
    """Generate personalized improvement suggestions"""
    suggestions = []
    
    if missing_sections:
        suggestions.append(f"Add missing sections: {', '.join(missing_sections)}")
    
    if exp_years < 2:
        suggestions.append("Highlight any relevant experience, including internships or projects")
    elif metrics < 3:
        suggestions.append("Add more quantifiable achievements (e.g., 'Increased efficiency by 20%')")
    
    # Industry-specific suggestions
    industry_keywords = set(INDUSTRY_KEYWORDS.get("tech", {}).get("primary", []))
    missing_keywords = [kw for kw in industry_keywords if kw not in keywords][:3]
    if missing_keywords:
        suggestions.append(f"Consider adding these keywords: {', '.join(missing_keywords)}")
    
    return suggestions

@app.post("/analyze")
async def analyze_resume(file: UploadFile = File(...)):
    """Main analysis endpoint"""
    try:
        text = extract_text(file)
        if len(text.split()) < MIN_RESUME_WORDS:
            raise HTTPException(400, "Document is too short to be a resume")
        
        return analyze_content(text)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Analysis error: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "5.0"}
