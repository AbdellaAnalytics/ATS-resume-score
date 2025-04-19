from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pdfplumber
from docx import Document
from io import BytesIO
from datetime import datetime
import requests
import traceback

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Google Apps Script Webhook URL (replace with yours)
GOOGLE_SHEET_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbxbSbii1A86bMyvCdMLzOOAY8YND-XAxhFmoNg3OpVCt09-VTnCu_sPkDvNvCKgFc85/exec"

# Extract text from PDF
def extract_text_from_pdf(contents):
    with pdfplumber.open(BytesIO(contents)) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""
        return text

# Extract text from DOCX
def extract_text_from_docx(contents):
    doc = Document(BytesIO(contents))
    return "\n".join([para.text for para in doc.paragraphs])

# Simple ATS score simulation (based on text length)
def calculate_ats_score(text):
    score = min(100, max(10, len(text) // 50))
    return score

# Log data to Google Sheets
def log_to_google_sheets(filename, score, timestamp):
    payload = {
        "file_name": filename,
        "ats_score": score,
        "timestamp": timestamp
    }
    response = requests.post(GOOGLE_SHEET_WEBHOOK_URL, json=payload)
    print("Logged to Google Sheets:", response.status_code)

@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        content_type = file.content_type
        print("Received file:", file.filename)
        print("Content type:", content_type)

        # Extract text based on file type
        if content_type == "application/pdf" or file.filename.endswith(".pdf"):
            text = extract_text_from_pdf(contents)
        elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or file.filename.endswith(".docx"):
            text = extract_text_from_docx(contents)
        else:
            return JSONResponse(status_code=400, content={"error": "Unsupported file type."})

        print("Extracted text length:", len(text))
        ats_score = calculate_ats_score(text)
        print("ATS Score:", ats_score)

        timestamp = datetime.now().strftime("%m/%d/%Y %H:%M")
        log_to_google_sheets(file.filename, ats_score, timestamp)

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
