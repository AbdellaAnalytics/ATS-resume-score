from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from docx import Document
import pdfplumber
import datetime
import requests
import traceback

app = FastAPI()

# Allow cross-origin for frontend (WordPress)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GOOGLE_SHEET_ENDPOINT = "https://script.google.com/macros/s/AKfycbxbSbii1A86bMyvCdMLzOOAY8YND-XAxhFmoNg3OpVCt09-VTnCu_sPkDvNvCKgFc85/exec"

def extract_text_from_docx(file):
    doc = Document(file)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_text_from_pdf(file):
    with pdfplumber.open(file) as pdf:
        return "\n".join(page.extract_text() or '' for page in pdf.pages)

def calculate_ats_score(text):
    score = 0
    keywords = ["python", "sql", "excel", "data", "analysis", "power bi", "tableau", "machine learning"]
    score += sum(1 for kw in keywords if kw.lower() in text.lower()) * 10
    return min(score, 100)

def log_to_google_sheets(name, score):
    try:
        requests.post(GOOGLE_SHEET_ENDPOINT, data={
            "filename": name,
            "score": score,
            "timestamp": datetime.datetime.now().isoformat()
        })
    except Exception as e:
        print("⚠️ Failed to log to Google Sheets:", str(e))


@app.post("/upload-resume/")
async def analyze_resume(file: UploadFile = File(...)):
    try:
        filename = file.filename.lower()
        contents = await file.read()

        # Determine file type
        if filename.endswith(".docx"):
            with open("temp.docx", "wb") as f:
                f.write(contents)
            text = extract_text_from_docx("temp.docx")

        elif filename.endswith(".pdf"):
            with open("temp.pdf", "wb") as f:
                f.write(contents)
            text = extract_text_from_pdf("temp.pdf")

        else:
            return JSONResponse(status_code=400, content={"error": "Unsupported file format"})

        score = calculate_ats_score(text)
        print(f"✅ ATS Score: {score}")

        # Log upload
        log_to_google_sheets(file.filename, score)

        return {"score": score}

    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": f"Unexpected error: {str(e)}"}
        )
