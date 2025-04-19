from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import docx2txt
import PyPDF2
import tempfile
import os
import requests
from datetime import datetime

app = FastAPI()

# Allow all origins for simplicity (you can restrict this in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Your Google Apps Script Web App URL
GOOGLE_SHEET_WEBHOOK = "https://script.google.com/macros/s/AKfycbxbSbii1A86bMyvCdMLzOOAY8YND-XAxhFmoNg3OpVCt09-VTnCu_sPkDvNvCKgFc85/exec"

# Extract text from uploaded file
def extract_text(file: UploadFile) -> str:
    if file.filename.endswith(".pdf"):
        pdf_reader = PyPDF2.PdfReader(file.file)
        text = " ".join([
            page.extract_text() for page in pdf_reader.pages if page.extract_text()
        ])
    elif file.filename.endswith(".docx"):
        file.file.seek(0)
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
        temp.write(file.file.read())
        temp.close()
        text = docx2txt.process(temp.name)
        os.unlink(temp.name)
    else:
        text = ""
    return text

# Score logic
def calculate_ats_score(text: str) -> int:
    score = 0
    keywords = ["experience", "skills", "education", "summary", "achievements", "projects"]
    for word in keywords:
        if word in text.lower():
            score += 15
    return min(score, 100)

# Logging to Google Sheets
def log_to_google_sheets(name: str, score: int):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload = {
            "file_name": name,
            "score": score,
            "timestamp": timestamp
        }
        requests.post(GOOGLE_SHEET_WEBHOOK, json=payload)
    except Exception as e:
        print("⚠️ Failed to log to Google Sheets:", e)

# API endpoint
@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    print("📩 Received file:", file.filename)
    print("📄 Content type:", file.content_type)
    file.file.seek(0)

    text = extract_text(file)
    print("📝 Extracted text length:", len(text))

    if not text:
        print("⚠️ No text extracted.")
        return {"error": "Could not read file."}

    score = calculate_ats_score(text)
    print("✅ ATS Score:", score)

    log_to_google_sheets(file.filename, score)

    return {"ats_score": score}

# Optional: root endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to the ATS Resume Score API"}
