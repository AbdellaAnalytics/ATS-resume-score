from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import docx2txt
import PyPDF2
import tempfile
import os

# ✅ FastAPI app instance (MUST be at top level)
app = FastAPI()

# ✅ CORS setup to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (adjust as needed)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Extract text from PDF or DOCX
def extract_text(file: UploadFile):
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

# ✅ Calculate ATS Score
def calculate_ats_score(text: str) -> int:
    score = 0
    keywords = keywords = ["communication", "teamwork", "leadership", "problem solving", "creativity", "critical thinking", "adaptability", "time management", "attention to detail", "collaboration", "presentation", "multitasking", "decision making", "project management", "budgeting", "forecasting", "kpi", "reporting", "strategic planning", "operations", "performance metrics", "business analysis", "negotiation", "risk management", "compliance", "scheduling", "coordination", "accounting", "bookkeeping", "reconciliation", "financial statements", "payroll", "cost control", "vat", "tax return", "audit", "balance sheet", "profit and loss", "financial analysis", "accounts payable", "accounts receivable", "digital marketing", "seo", "sem", "email marketing", "social media", "lead generation", "sales", "cold calling", "crm", "branding", "advertising", "market research", "content creation", "campaigns", "customer acquisition", "conversion rate", "recruitment", "talent acquisition", "hr policies", "employee relations", "interviews", "onboarding", "training", "performance appraisal", "benefits administration", "python", "sql", "java", "javascript", "html", "css", "linux", "bash", "git", "docker", "kubernetes", "cloud", "aws", "azure", "devops", "api", "database", "networking", "cybersecurity", "software development", "web development", "debugging", "data analysis", "data visualization", "excel", "power bi", "tableau", "statistics", "dashboard", "etl", "machine learning", "ai", "business intelligence", "big data", "logistics", "inventory", "warehouse", "supply chain", "shipping", "procurement", "sourcing", "transportation", "dispatch", "order management", "stock control", "customer service", "support", "client relations", "call center", "troubleshooting", "ticketing system", "service level agreement", "customer satisfaction", "graphic design", "photoshop", "illustrator", "ui", "ux", "adobe", "figma", "animation", "video editing", "web design", "nursing", "patient care", "clinical", "diagnosis", "treatment", "medical records", "emergency response", "healthcare compliance", "teaching", "lesson planning", "curriculum", "classroom management", "e-learning", "student engagement", "assessment", "pedagogy"
    ]
    for word in keywords:
        if word in text.lower():
            score += 15
    return min(score, 100)

# ✅ Resume Upload Endpoint
@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    print("📄 File received:", file.filename)
    file.file.seek(0)
    text = extract_text(file)
    print("📝 Extracted text:", text)

    if not text:
        return {"error": "Could not read file."}

    score = calculate_ats_score(text)
    return {"ats_score": score}

# ✅ Optional root route
@app.get("/")
def root():
    return {"message": "ATS Resume Score API is running."}
