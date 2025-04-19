from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from PyPDF2 import PdfReader
import docx2txt
import io

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ موسعة الكلمات المفتاحية لجميع الوظائف
KEYWORDS = [
    # Data
    "excel", "python", "sql", "data", "analysis", "analytics", "reporting", "insights", "forecasting",
    "power bi", "tableau", "dashboard", "visualization", "statistics", "regression", "data mining",
    # Marketing
    "seo", "google ads", "facebook ads", "branding", "campaign", "content", "digital marketing",
    "email marketing", "instagram", "marketing strategy", "analytics", "a/b testing", "keyword research",
    # Accounting
    "invoice", "quickbooks", "erp", "reconciliation", "tax", "vat", "ledger", "balance sheet",
    "accounts payable", "accounts receivable", "bookkeeping", "financial statement", "journal entries",
    # HR
    "recruitment", "onboarding", "payroll", "hr policies", "employee engagement", "training", "labor law",
    "talent acquisition", "compliance", "benefits", "performance review",
    # Sales & Customer
    "sales", "crm", "cold calling", "closing deals", "upselling", "b2b", "b2c", "pipeline", "negotiation",
    "customer service", "customer satisfaction", "inbound", "outbound", "zendesk", "ticketing",
    # Software Dev
    "java", "c++", "html", "css", "javascript", "react", "node.js", "django", "flask", "api", "git", "github",
    "unit testing", "oop", "agile", "scrum", "docker", "linux", "ci/cd",
    # Project Management
    "project management", "pmp", "scrum", "kanban", "jira", "trello", "timeline", "stakeholders", "budget",
    # General
    "teamwork", "communication", "problem solving", "leadership", "multitasking", "presentation",
    "attention to detail", "time management", "adaptability"
]

def extract_text_from_pdf(file_data):
    try:
        reader = PdfReader(file_data)
        return " ".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return ""

def extract_text_from_docx(file_data):
    try:
        return docx2txt.process(file_data)
    except Exception:
        return ""

def calculate_ats_score(resume_text):
    resume_text = resume_text.lower()
    matched_keywords = sum(1 for keyword in KEYWORDS if keyword in resume_text)
    score = (matched_keywords / len(KEYWORDS)) * 100
    return round(score)

@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    try:
        filename = file.filename.lower()
        contents = await file.read()

        if filename.endswith(".pdf"):
            resume_text = extract_text_from_pdf(io.BytesIO(contents))
        elif filename.endswith(".docx"):
            with open("temp.docx", "wb") as f:
                f.write(contents)
            resume_text = extract_text_from_docx("temp.docx")
        else:
            return {"error": "Unsupported file type. Please upload PDF or DOCX."}

        if not resume_text.strip():
            return {"error": "Failed to extract text from resume."}

        ats_score = calculate_ats_score(resume_text)
        return {"ats_score": ats_score}
    except Exception:
        return {"error": "Something went wrong while processing the resume."}
