from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from docx import Document
import pdfplumber
import io
import datetime
import requests

app = FastAPI()

# Allow frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Google Sheets webhook URL
GOOGLE_SHEET_WEBHOOK = "https://script.google.com/macros/s/AKfycbxbSbii1A86bMyvCdMLzOOAY8YND-XAxhFmoNg3OpVCt09-VTnCu_sPkDvNvCKgFc85/exec"

# Extract text from PDF
def extract_text_from_pdf(file_bytes):
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        text = ''
        for page in pdf.pages:
            text += page.extract_text() or ''
        return text

# Extract text from DOCX
def extract_text_from_docx(file_bytes):
    doc = Document(io.BytesIO(file_bytes))
    return '\n'.join([p.text for p in doc.paragraphs])

# Simple ATS scoring logic
def calculate_ats_score(text):
    keywords = ['python', 'data', 'analysis', 'sql', 'excel', 'power bi', 'communication', 'teamwork']
    text_lower = text.lower()
    score = sum(1 for word in keywords if word in text_lower)
    return int((score / len(keywords)) * 100)

@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        content_type = file.content_type

        # Extract text based on file type
        if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text = extract_text_from_docx(contents)
        elif content_type == "application/pdf":
            text = extract_text_from_pdf(contents)
        else:
            return JSONResponse(status_code=400, content={"error": "Only PDF or DOCX files are supported."})

        if not text.strip():
            return JSONResponse(status_code=400, content={"error": "No readable text found in the document."})

        # Calculate ATS score
        score = calculate_ats_score(text)

        # Log to Google Sheets
        try:
            requests.post(GOOGLE_SHEET_WEBHOOK, json={
                "file_name": file.filename,
                "score": score,
                "timestamp": datetime.datetime.now().strftime('%m/%d/%Y %H:%M')
            })
        except Exception as logging_error:
            print(f"Logging error: {logging_error}")

        return {"ats_score": score}

    except Exception as e:
        print("❌ Resume parsing failed:", str(e))
        return JSONResponse(status_code=500, content={"error": "Failed to analyze resume. Please try again."})
