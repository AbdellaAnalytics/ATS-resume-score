from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import docx2txt
import pdfplumber
import tempfile
import os
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_text(file: UploadFile):
    if file.filename.endswith(".pdf"):
        file.file.seek(0)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file.file.read())
            tmp_path = tmp.name
        text = ""
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        os.unlink(tmp_path)
        return text

    elif file.filename.endswith(".docx"):
        file.file.seek(0)
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
        temp.write(file.file.read())
        temp.close()
        text = docx2txt.process(temp.name)
        os.unlink(temp.name)
        return text
    else:
        return ""

def calculate_ats_score(text: str) -> int:
    score = 0
    keywords = ["experience", "skills", "education", "summary", "achievements", "projects"]
    for word in keywords:
        if word in text.lower():
            score += 15
    return min(score, 100)

@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    print("📩 Received file:", file.filename)
    print("📄 Content type:", file.content_type)
    file.file.seek(0)

    text = extract_text(file)
    print("📝 Extracted text length:", len(text))

    if not text.strip():
        print("⚠️ No text extracted.")
        return {"error": "Could not read file."}

    score = calculate_ats_score(text)
    print("✅ ATS Score:", score)

    # Send metadata to Google Sheets
    try:
        requests.post(
            "https://script.google.com/macros/s/AKfycbxbSbii1A86bMyvCdMLzOOAY8YND-XAxhFmoNg3OpVCt09-VTnCu_sPkDvNvCKgFc85/exec",
            json={
                "filename": file.filename,
                "ats_score": score,
                "timestamp": datetime.datetime.now().isoformat()
            }
        )
    except Exception as e:
        print("⚠️ Failed to log to Google Sheets:", e)

    return {"ats_score": score}
