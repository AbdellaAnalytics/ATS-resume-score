from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import docx2txt
import PyPDF2
import tempfile
import os
import requests
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Your Google Apps Script webhook
GOOGLE_SHEET_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbxbSbii1A86bMyvCdMLzOOAY8YND-XAxhFmoNg3OpVCt09-VTnCu_sPkDvNvCKgFc85/exec"

def extract_text(file: UploadFile):
    try:
        if file.filename.endswith(".pdf"):
            pdf_reader = PyPDF2.PdfReader(file.file)
            text = " ".join([
                page.extract_text() for page in pdf_reader.pages
                if page.extract_text()
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
    except Exception as e:
        print("❌ Error reading file:", e)
        text = ""
    return text

def calculate_ats_score(text: str) -> int:
    score = 0
    keywords = [
        "experience", "skills", "education", "summary", "achievements", "projects"
    ]
    for word in keywords:
        if word in text.lower():
            score += 15
    return min(score, 100)

def log_to_google_sheets(name: str, score: int):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = {
            "name": name,
            "score": score,
            "timestamp": timestamp
        }
        response = requests.post(GOOGLE_SHEET_WEBHOOK_URL, json=data)
        print("✅ Logged to Google Sheets:", response.status_code)
    except Exception as e:
        print("⚠️ Failed to log to Google Sheets:", e)

@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    print("📩 Received file:", file.filename)
    file.file.seek(0)

    text = extract_text(file)
    print("📝 Extracted text length:", len(text))

    if not text:
        return {"error": "Could not extract text from the resume."}

    score = calculate_ats_score(text)
    log_to_google_sheets(file.filename, score)

    return {"ats_score": score}

@app.get("/")
def read_root():
    return {"message": "ATS Resume Score API is running."}
