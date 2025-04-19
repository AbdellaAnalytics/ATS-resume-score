from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from docx import Document
import pdfplumber
import requests
import datetime
import io

app = FastAPI()

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_text_from_pdf(file_bytes):
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            return "\n".join([page.extract_text() or '' for page in pdf.pages])
    except Exception as e:
        return None

def extract_text_from_docx(file_bytes):
    try:
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        return None

def calculate_ats_score(text):
    if not text:
        return 0
    length = len(text.strip())
    if length == 0:
        return 0
    elif length < 500:
        return 50
    elif length < 1000:
        return 75
    else:
        return 90

def log_to_google_sheets(name, score):
    try:
        response = requests.post(
            "https://script.google.com/macros/s/AKfycbxbSbii1A86bMyvCdMLzOOAY8YND-XAxhFmoNg3OpVCt09-VTnCu_sPkDvNvCKgFc85/exec",
            json={
                "name": name,
                "score": score,
                "timestamp": str(datetime.datetime.now())
            },
            timeout=10
        )
        return response.status_code
    except Exception as e:
        return None

@app.post("/upload-resume/")
async def analyze_resume(file: UploadFile = File(...)):
    try:
        content = await file.read()
        filename = file.filename

        if filename.endswith(".pdf"):
            text = extract_text_from_pdf(content)
        elif filename.endswith(".docx"):
            text = extract_text_from_docx(content)
        else:
            return JSONResponse(status_code=400, content={"error": "Unsupported file type."})

        if not text:
            return JSONResponse(status_code=500, content={"error": "Failed to extract text."})

        score = calculate_ats_score(text)
        log_to_google_sheets(filename, score)

        return {"score": score}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "Unknown issue."})
