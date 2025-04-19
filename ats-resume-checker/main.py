from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
import docx2txt
import pdfplumber
import os
import requests
from datetime import datetime

app = FastAPI()

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dummy scoring logic
def calculate_ats_score(text):
    return min(100, int(len(text.strip()) / 30))  # Rough estimate

@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        filename = file.filename.lower()

        # Save uploaded file temporarily
        with open("temp_file", "wb") as f:
            f.write(contents)

        # Extract text
        if filename.endswith(".docx"):
            text = docx2txt.process("temp_file")
        elif filename.endswith(".pdf"):
            text = ""
            with pdfplumber.open("temp_file") as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
        else:
            os.remove("temp_file")
            return JSONResponse(status_code=400, content={"error": "Unsupported file format"})

        os.remove("temp_file")

        score = calculate_ats_score(text)

        # Send to Google Sheets
        try:
            response = requests.post(
                "https://script.google.com/macros/s/AKfycbxbSbii1A86bMyvCdMLzOOAY8YND-XAxhFmoNg3OpVCt09-VTnCu_sPkDvNvCKgFc85/exec",
                json={
                    "filename": file.filename,
                    "score": score,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            )
            print("Logged to Google Sheets:", response.status_code)
        except Exception as log_error:
            print("❌ Failed to log to Google Sheets:", log_error)

        return {"score": score}

    except Exception as e:
        print("❌ Resume analysis error:", e)
        return JSONResponse(status_code=500, content={"error": "Failed to analyze resume. Please try again."})
