import os
import json
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from docx import Document
from PyPDF2 import PdfReader
import datetime
import random
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = FastAPI()

# Enable CORS for frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Google Sheets setup using credentials from env variable
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_json = os.getenv("GOOGLE_CREDS_JSON")
creds_dict = json.loads(creds_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("ATS Score Logger").sheet1

def extract_text(file: UploadFile):
    if file.filename.endswith(".pdf"):
        reader = PdfReader(file.file)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    elif file.filename.endswith(".docx"):
        doc = Document(file.file)
        return "\n".join(para.text for para in doc.paragraphs)
    else:
        raise ValueError("Unsupported file type")

def calculate_ats_score(text: str) -> int:
    if not text.strip():
        return 0
    return random.randint(70, 90)  # Simulated score for demo

@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    try:
        text = extract_text(file)
        score = calculate_ats_score(text)

        sheet.append_row([
            file.filename,
            score,
            datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        ])
        return JSONResponse(content={"score": score})

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/")
async def root():
    return {"message": "ATS Resume Checker API is live."}
