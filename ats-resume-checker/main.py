from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber
import io
from docx import Document
from datetime import datetime
import requests
import traceback

app = FastAPI()

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_text_from_pdf(file_bytes):
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        return "\n".join([page.extract_text() or "" for page in pdf.pages])

def extract_text_from_docx(file_bytes):
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join([para.text for para in doc.paragraphs])

def calculate_ats_score(text):
    keywords = ['python', 'data', 'sql', 'analysis', 'excel', 'power bi', 'machine learning']
    score = sum(1 for word in keywords if word.lower() in text.lower())
    return int((score / len(keywords)) * 100)

def log_to_google_sheets(file_name, score, timestamp):
    sheet_url = "https://script.google.com/macros/s/AKfycbxbSbii1A86bMyvCdMLzOOAY8YND-XAxhFmoNg3OpVCt09-VTnCu_sPkDvNvCKgFc85/exec"
    data = {"file_name": file_name, "ats_score": score, "timestamp": timestamp}
    try:
        response = requests.post(sheet_url, json=data)
        print(f"Logged to Google Sheets: {response.status_code}")
    except Exception as e:
        print("Error logging to Google Sheets:", e)

@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        content_type = file.content_type
        print("Received file:", file.filename)
        print("Content type:", content_type)

        text = ""

        if content_type == "application/pdf" or file.filename.endswith(".pdf"):
            text = extract_text_from_pdf(contents)
        elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or file.filename.endswith(".docx"):
            text = extract_text_from_docx(contents)
        else:
            return JSONResponse(status_code=400, content={"error": "Unsupported file type."})

        print("Extracted text length:", len(text))

        ats_score = calculate_ats_score(text)
        print("ATS Score:", ats_score)

        # Logging to Google Sheets
        timestamp = datetime.now().strftime("%m/%d/%Y %H:%M")
        log_to_google_sheets(file.filename, ats_score, timestamp)

        return {"score": ats_score}

    except Exception as e:
        print("Exception occurred:")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to analyze resume. Please try again.", "details": str(e)}
        )
