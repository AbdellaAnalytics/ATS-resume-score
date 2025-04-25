from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import docx2txt
import PyPDF2
import tempfile
import os
import re
from typing import Dict, List, Tuple
from datetime import datetime

app = FastAPI(
    title="Pro Resume Scorer", 
    version="3.0",
    description="Advanced resume analysis API with comprehensive scoring and improvement suggestions"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://bookmejob.com", "http://localhost:3000"],  # Added localhost for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants for scoring
MAX_SECTION_SCORE = 30
MAX_CONTENT_SCORE = 40
MAX_KEYWORD_SCORE = 20
MAX_FORMATTING_SCORE = 10
MAX_EXPERIENCE_SCORE = 20

# Industry-specific keyword sets
TECH_KEYWORDS = {"python", "java", "sql", "javascript", "c++", "git", "docker", "aws", "machine learning", "ai"}
BUSINESS_KEYWORDS = {"management", "strategy", "leadership", "marketing", "sales", "finance", "budget", "roi"}
DESIGN_KEYWORDS = {"ux", "ui", "figma", "adobe", "photoshop", "illustrator", "typography", "wireframing"}
ANALYTICS_KEYWORDS = {"data analysis", "excel", "power bi", "tableau", "statistics", "sql", "python", "r"}

def detect_industry(text: str) -> str:
    """Detect the most likely industry based on keywords"""
    text_lower = text.lower()
    keyword_counts = {
        "tech": sum(1 for kw in TECH_KEYWORDS if kw in text_lower),
        "business": sum(1 for kw in BUSINESS_KEYWORDS if kw in text_lower),
        "design": sum(1 for kw in DESIGN_KEYWORDS if kw in text_lower),
        "analytics": sum(1 for kw in ANALYTICS_KEYWORDS if kw in text_lower)
    }
    return max(keyword_counts.items(), key=lambda x: x[1])[0] if keyword_counts else "general"

def extract_text(file: UploadFile) -> str:
    """Extract text from uploaded file (PDF or DOCX)"""
    try:
        if file.filename.endswith(".pdf"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(file.file.read())
                tmp_path = tmp.name

            with open(tmp_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = " ".join([page.extract_text() for page in reader.pages if page.extract_text()])
            os.unlink(tmp_path)
            return text

        elif file.filename.endswith(".docx"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                tmp.write(file.file.read())
                tmp_path = tmp.name
            text = docx2txt.process(tmp_path)
            os.unlink(tmp_path)
            return text

        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload PDF or DOCX.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

def extract_experience(text: str) -> Tuple[int, List[str]]:
    """Extract and analyze work experience section"""
    experience_pattern = r"(experience|work history|employment history)(.*?)(?=(education|skills|$))"
    matches = re.search(experience_pattern, text, re.IGNORECASE | re.DOTALL)
    
    if not matches:
        return 0, []
    
    experience_text = matches.group(2)
    
    # Count years of experience
    year_pattern = r"(20\d{2}|'\d{2})\s*[-–—]\s*(20\d{2}|'\d{2}|present|current)"
    year_matches = re.findall(year_pattern, experience_text, re.IGNORECASE)
    
    total_years = 0
    positions = []
    
    for start, end in year_matches:
        try:
            start_year = int(start) if len(start) == 4 else 2000 + int(start[1:])
            if end.lower() in ["present", "current"]:
                end_year = datetime.now().year
            else:
                end_year = int(end) if len(end) == 4 else 2000 + int(end[1:])
            total_years += (end_year - start_year)
            
            # Extract job titles
            title_match = re.search(r"(.+?)\s*" + re.escape(start), experience_text)
            if title_match:
                positions.append(title_match.group(1).strip())
        except:
            continue
    
    # Extract bullet points with metrics
    bullet_points = re.findall(r"•\s*(.*?)[.•]", experience_text)
    metrics = [bp for bp in bullet_points if any(word in bp.lower() for word in ["%", "increase", "decrease", "growth", "saved", "reduced"])]
    
    return total_years, metrics

def analyze_formatting(text: str) -> int:
    """Analyze resume formatting quality"""
    score = 0
    
    # Check for consistent headings
    headings = re.findall(r"\n\s*[A-Z][A-Za-z ]+:\s*\n", text)
    if len(headings) >= 3:  # At least 3 main sections
        score += 3
    
    # Check for bullet points
    if "•" in text or "-" in text or "*" in text:
        score += 2
    
    # Check for length (1-2 pages)
    word_count = len(text.split())
    if 300 <= word_count <= 800:
        score += 3
    elif word_count > 800:
        score += 1  # Some credit for content, but too long
    
    # Check for contact info
    if any(re.search(pattern, text) for pattern in [r"\b[\w\.-]+@[\w\.-]+\.\w+\b", r"\(\d{3}\) \d{3}-\d{4}"]):
        score += 2
    
    return min(score, MAX_FORMATTING_SCORE)

def analyze_resume(text: str) -> Dict:
    """Comprehensive resume analysis with industry-specific scoring"""
    text_lower = text.lower()
    word_count = len(text.split())
    industry = detect_industry(text)
    
    # Section analysis
    required_sections = ["experience", "education", "skills"]
    sections_found = [s for s in required_sections if re.search(rf"\b{s}\b", text_lower)]
    missing_sections = [s for s in required_sections if s not in sections_found]
    section_score = (len(sections_found) / len(required_sections)) * MAX_SECTION_SCORE
    
    # Content analysis
    content_score = 0
    if word_count > 200:
        content_score += 10  # Base score for sufficient content
        content_score += min((word_count - 200) // 20, MAX_CONTENT_SCORE - 10)
    
    # Keyword analysis (industry-specific)
    if industry == "tech":
        keywords = TECH_KEYWORDS
    elif industry == "business":
        keywords = BUSINESS_KEYWORDS
    elif industry == "design":
        keywords = DESIGN_KEYWORDS
    elif industry == "analytics":
        keywords = ANALYTICS_KEYWORDS
    else:
        keywords = TECH_KEYWORDS | BUSINESS_KEYWORDS | DESIGN_KEYWORDS | ANALYTICS_KEYWORDS
    
    matched_keywords = [kw for kw in keywords if kw in text_lower]
    keyword_score = min(len(matched_keywords) * 2, MAX_KEYWORD_SCORE)
    
    # Experience analysis
    total_years, metrics = extract_experience(text)
    experience_score = min(total_years * 2, MAX_EXPERIENCE_SCORE)  # 2 points per year
    if metrics:
        experience_score = min(experience_score + len(metrics), MAX_EXPERIENCE_SCORE)
    
    # Formatting analysis
    formatting_score = analyze_formatting(text)
    
    # Calculate total score (weighted)
    total_score = (
        0.25 * section_score +
        0.20 * content_score +
        0.20 * keyword_score +
        0.25 * experience_score +
        0.10 * formatting_score
    )
    
    # Normalize to 40-95 range
    final_score = min(max(round(total_score), 40), 95)
    
    # Generate suggestions
    suggestions = []
    
    # Section suggestions
    if missing_sections:
        suggestions.append(f"Add missing sections: {', '.join(missing_sections)}")
    
    # Content suggestions
    if word_count < 300:
        suggestions.append("Resume is too short. Expand with more details about your experience and skills.")
    elif word_count > 800:
        suggestions.append("Resume may be too long. Consider condensing to 1-2 pages.")
    
    # Keyword suggestions
    missing_industry_keywords = [kw for kw in keywords if kw not in matched_keywords][:5]
    if missing_industry_keywords and industry != "general":
        suggestions.append(f"Consider adding these {industry} keywords: {', '.join(missing_industry_keywords)}")
    
    # Experience suggestions
    if total_years == 0:
        suggestions.append("Include dates for your work experience to show duration.")
    elif metrics and len(metrics) < 2:
        suggestions.append("Add more quantifiable achievements (e.g., 'Increased sales by 20%').")
    
    # Formatting suggestions
    if formatting_score < 5:
        suggestions.append("Improve formatting with clear section headings and bullet points.")
    
    # Industry-specific advice
    if industry == "tech":
        suggestions.append("For tech roles, highlight specific technologies and projects.")
    elif industry == "business":
        suggestions.append("For business roles, emphasize leadership and strategic impact.")
    
    return {
        "score": final_score,
        "industry": industry,
        "details": {
            "word_count": word_count,
            "estimated_experience_years": total_years,
            "quantifiable_achievements": len(metrics),
            "sections_found": sections_found,
            "missing_sections": missing_sections,
            "keyword_matches": matched_keywords[:10],  # Show top 10
            "formatting_score": formatting_score,
            "breakdown": {
                "section_score": round(section_score, 1),
                "content_score": round(content_score, 1),
                "keyword_score": round(keyword_score, 1),
                "experience_score": round(experience_score, 1),
                "formatting_score": round(formatting_score, 1)
            }
        },
        "suggestions": suggestions
    }

@app.post("/score/")
async def score_resume(file: UploadFile = File(...)):
    """Endpoint to analyze and score a resume"""
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file uploaded.")
        
        text = extract_text(file)
        if not text.strip():
            raise HTTPException(status_code=400, detail="Empty or unreadable file.")
        
        return analyze_resume(text)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@app.get("/health")
def health_check():
    """Health check endpoint with additional status information"""
    return {
        "status": "OK",
        "version": "3.0",
        "supported_file_types": ["PDF", "DOCX"]
    }
