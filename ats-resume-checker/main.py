from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from docx import Document
import pdfplumber
import io
import re
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = FastAPI()

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Google Sheets Setup
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("ATS Resume Score").sheet1  # Sheet name

# Extract text from PDF
def extract_text_from_pdf(file_bytes):
    text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

# Extract text from DOCX
def extract_text_from_docx(file_bytes):
    doc = Document(io.BytesIO(file_bytes))
    text = " ".join([para.text for para in doc.paragraphs])
    return text

# Simple ATS score function (based on keyword matching)
def calculate_ats_score(text):
    keywords = ['python', 'sql', 'excel', 'power bi', 'data analysis', 'kpi', 'reporting', 'forecasting']
    text = text.lower()
    count = sum(text.count(word) for word in keywords)
    max_score = len(keywords) * 2  # Adjust as needed
    return min(round((count / max_score) * 100), 100)

# Main route
@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    try:
        contents = await file.read()

        # Detect file type and extract text
        if file.filename.endswith(".pdf"):
            text = extract_text_from_pdf(contents)
        elif file.filename.endswith(".docx"):
            text = extract_text_from_docx(contents)
        else:
            return {"error": "Unsupported file format. Use PDF or DOCX."}

        # Score the resume
        score = calculate_ats_score(text)

        # Log to Google Sheet
        timestamp = datetime.datetime.now().strftime("%m/%d/%Y %H:%M")
        sheet.append_row([file.filename, score, timestamp])

        return {"score": score}

    except Exception as e:
        print("❌ Error:", str(e))
        return {"error": "Failed to analyze resume. Please try again."}
