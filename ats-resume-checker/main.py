from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
import docx
import pdfplumber
import requests
from datetime import datetime

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Helper functions ---

def extract_text_from_docx(file):
    doc = docx.Document(file)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_text_from_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

def calculate_score(text):
    if not text or len(text.strip()) < 100:
        return 0
    score = min(100, len(text) // 30)
    return score

def log_to_google_sheets(filename, score):
    try:
        requests.post(
            "https://script.google.com/macros/s/AKfycbxbSbii1A86bMyvCdMLzOOAY8YND-XAxhFmoNg3OpVCt09-VTnCu_sPkDvNvCKgFc85/exec",
            json={"filename": filename, "score": score, "timestamp": datetime.now().isoformat()}
        )
    except Exception as e:
        print("Logging error:", e)

# --- Routes ---

@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        file.file.seek(0)

        if file.filename.endswith(".docx"):
            text = extract_text_from_docx(file.file)
        elif file.filename.endswith(".pdf"):
            text = extract_text_from_pdf(file.file)
        else:
            return JSONResponse(status_code=400, content={"error": "Unsupported file format."})

        score = calculate_score(text)
        log_to_google_sheets(file.filename, score)

        return {"score": score}

    except Exception as e:
        print("ERROR:", e)
        return JSONResponse(status_code=500, content={"error": "Failed to analyze resume. Please try again."})
