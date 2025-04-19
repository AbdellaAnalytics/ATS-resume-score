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
    keywords = [
        "experience", "skills", "education", "summary", "achievements", "projects"
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
