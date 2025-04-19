from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import datetime
import pdfplumber
import io
from docx import Document
import traceback
import requests
import mimetypes

app = FastAPI()

# CORS settings (allow all for testing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Google Sheets Script URL
GOOGLE_SHEETS_WEBHOOK = "https://script.google.com/macros/s/AKfycbxbSbii1A86bMyvCdMLzOOAY8YND-XAxhFmoNg3OpVCt09-VTnCu_sPkDvNvCKgFc85/exec"

def extract_text_from_pdf(file_bytes):
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            text = ''
            for page in pdf.pages:
                text += page.extract_text() or ''
        return text
    except Exception as e:
        raise Exception("PDF extraction failed: " + str(e))

def extract_text_from_docx(file_bytes):
    try:
        doc = Document(io.BytesIO(file_bytes))
        return '\n'.join([p.text for p in doc.paragraphs])
    except Exception as e:
        raise Exception("DOCX extraction failed: " + str(e))

def calculate_ats_score(text: str) -> int:
    # Example ATS score logic (based on word count)
    score = min(100, int(len(text.split()) / 10))
    return score

@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    try:
        filename = file.filename
        contents = await file.read()
        content_type = file.content_type or mimetypes.guess_type(filename)[0]

        if content_type == "application/pdf" or filename.endswith(".pdf"):
            text = extract_text_from_pdf(contents)
        elif content_type in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword"
        ] or filename.endswith(".docx"):
            text = extract_text_from_docx(contents)
        else:
            return JSONResponse(status_code=400, content={"error": "Unsupported file type."})

        if not text.strip():
            return JSONResponse(status_code=400, content={"error": "Empty or unreadable resume."})

        ats_score = calculate_ats_score(text)

        # Send to Google Sheets
        payload = {
            "file_name": filename,
            "ats_score": ats_score,
            "timestamp": datetime.now().strftime("%m/%d/%Y %H:%M")
        }

        response = requests.post(GOOGLE_SHEETS_WEBHOOK, data=payload)
        print("Logged to Google Sheets:", response.status_code)

        return {"score": ats_score}

    except Exception as e:
        error_trace = traceback.format_exc()
        print("Traceback:", error_trace)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to analyze resume. Please try again.",
                "details": str(e),
                "trace": error_trace
            }
        )
