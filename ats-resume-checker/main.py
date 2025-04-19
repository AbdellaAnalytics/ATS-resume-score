from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from docx import Document
import pdfplumber
from datetime import datetime
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GOOGLE_SHEET_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbxbSbii1A86bMyvCdMLzOOAY8YND-XAxhFmoNg3OpVCt09-VTnCu_sPkDvNvCKgFc85/exec"

def extract_text_from_docx(file_path):
    doc = Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_text_from_pdf(file_path):
    with pdfplumber.open(file_path) as pdf:
        return "\n".join([page.extract_text() or "" for page in pdf.pages])

def calculate_ats_score(text):
    # Placeholder logic
    return min(100, int(len(text) / 30))

def log_to_google_sheets(filename, score):
    try:
        data = {
            "filename": filename,
            "score": score,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }
        response = requests.post(GOOGLE_SHEET_WEBHOOK_URL, json=data)
        return response.status_code
    except Exception as e:
        print("Logging error:", e)
        return None

@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        temp_path = f"temp_{file.filename}"
        with open(temp_path, "wb") as f:
            f.write(contents)

        # Detect file type
        if file.filename.endswith(".docx"):
            text = extract_text_from_docx(temp_path)
        elif file.filename.endswith(".pdf"):
            text = extract_text_from_pdf(temp_path)
        else:
            return JSONResponse(content={"error": "Unsupported file type."}, status_code=400)

        score = calculate_ats_score(text)
        log_status = log_to_google_sheets(file.filename, score)

        os.remove(temp_path)
        return {"ats_score": score}

    except Exception as e:
        print("Server Error:", e)
        return JSONResponse(content={"error": "Unknown issue."}, status_code=500)

@app.get("/")
def root():
    return HTMLResponse(content="<h2>Resume Score API is live</h2>")

