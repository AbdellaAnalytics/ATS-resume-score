from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PyPDF2 import PdfReader
import docx2txt
import tempfile
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Extensive list of industry keywords
KEYWORDS = [
    # Programming & Tech
    "python", "java", "javascript", "html", "css", "react", "node.js", "sql", "api", "git", "docker", "aws", "azure",
    "c++", "c#", "php", "typescript", "flutter", "kotlin", "swift", "linux", "bash", "tensorflow", "pytorch",

    # Data & Analytics
    "excel", "power bi", "tableau", "sql", "data analysis", "data visualization", "machine learning", "statistics",
    "r", "python", "pandas", "numpy", "data science", "etl", "big data", "kpi", "dashboard", "predictive modeling",

    # Customer Service
    "customer service", "call center", "crm", "problem-solving", "communication skills", "multitasking",
    "handling complaints", "customer satisfaction",

    # Marketing & Sales
    "marketing", "digital marketing", "seo", "sem", "google ads", "facebook ads", "sales", "negotiation",
    "crm", "email marketing", "social media", "content creation", "branding", "lead generation",

    # Engineering
    "autocad", "solidworks", "matlab", "engineering", "design", "manufacturing", "production", "cad", "cam",
    "electrical", "mechanical", "civil", "structural", "project management",

    # Finance & Accounting
    "accounting", "finance", "budgeting", "forecasting", "financial analysis", "erp", "sap", "quickbooks",
    "tax", "audit", "bookkeeping", "cash flow", "balance sheet", "p&l", "journal entries",

    # Management & Soft Skills
    "leadership", "management", "teamwork", "communication", "problem solving", "time management",
    "adaptability", "conflict resolution", "strategic planning", "decision making",

    # Education / Training
    "teaching", "training", "curriculum development", "lesson planning", "instruction", "online teaching",
    "education", "lms", "classroom management", "assessment"
]

@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        temp_path = f"temp_{file.filename}"
        with open(temp_path, "wb") as f:
            f.write(contents)

        text = ""
        if file.filename.endswith(".pdf"):
            try:
                reader = PdfReader(temp_path)
                for page in reader.pages:
                    text += page.extract_text() or ""
            except:
                os.remove(temp_path)
                return {"error": "Failed to read PDF. Is it valid?"}

        elif file.filename.endswith(".docx"):
            text = docx2txt.process(temp_path)
        else:
            os.remove(temp_path)
            return {"error": "Unsupported file format. Please upload PDF or DOCX."}

        os.remove(temp_path)

        text = text.lower()
        matches = [word for word in KEYWORDS if word.lower() in text]
        score = int((len(set(matches)) / len(KEYWORDS)) * 100)

        return {"ats_score": score}

    except Exception as e:
        return {"error": f"Error processing file: {str(e)}"}
