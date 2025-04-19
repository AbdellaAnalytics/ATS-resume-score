from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse
import pdfplumber
from docx import Document
import requests
from datetime import datetime
import io

app = FastAPI()

# Allow CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Google Apps Script endpoint
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxbSbii1A86bMyvCdMLzOOAY8YND-XAxhFmoNg3OpVCt09-VTnCu_sPkDvNvCKgFc85/exec"

@app.get("/", response_class=HTMLResponse)
async def home():
    return "<h1>ATS Resume Score Checker is Running</h1>"

@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    try:
        content = await file.read()
        filename = file.filename.lower()

        # Extract text from PDF or DOCX
        if filename.endswith(".pdf"):
            text = extract_text_from_pdf(content)
        elif filename.endswith(".docx"):
            text = extract_text_from_docx(content)
        else:
            return JSONResponse(status_code=400, content={"error": "Unsupported file format. Only PDF and DOCX allowed."})

        print("Extracted text length:", len(text))

        if len(text.strip()) < 100:
            return JSONResponse(status_code=400, content={"error": "Resume is too short or could not be processed. Try a different file."})

        # Score is based on length (very simplified)
        score = min(int((len(text) / 3000) * 100), 100)

        # Log to Google Sheets
        log_to_google_sheets(file.filename, score)

        return {"score": score}
    
    except Exception as e:
        print("Error:", str(e))
        return JSONResponse(status_code=500, content={"error": "Failed to analyze resume. Please try again."})


def extract_text_from_pdf(content: bytes) -> str:
    text = ""
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def extract_text_from_docx(content: bytes) -> str:
    doc = Document(io.BytesIO(content))
    return "\n".join([para.text for para in doc.paragraphs])


def log_to_google_sheets(filename: str, score: int):
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload = {
            "filename": filename,
            "score": score,
            "timestamp": now,
        }
        response = requests.post(GOOGLE_SCRIPT_URL, json=payload)
        print("Logged to Google Sheets:", response.status_code)
    except Exception as e:
        print("Failed to log to Google Sheets:", str(e))
