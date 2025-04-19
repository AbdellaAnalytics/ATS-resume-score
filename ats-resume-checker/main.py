from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import docx2txt
import fitz  # PyMuPDF
import json
import os
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load keywords
with open("universal_keywords.json", "r", encoding="utf-8") as f:
    KEYWORDS = json.load(f)

# Combine all keywords across all fields
ALL_KEYWORDS = []
for category_keywords in KEYWORDS.values():
    ALL_KEYWORDS.extend([kw.lower() for kw in category_keywords])

# Remove duplicates
ALL_KEYWORDS = list(set(ALL_KEYWORDS))

def extract_text_from_docx(file_path):
    try:
        return docx2txt.process(file_path)
    except Exception as e:
        return ""

def extract_text_from_pdf(file_path):
    try:
        text = ""
        with fitz.open(file_path) as pdf:
            for page in pdf:
                text += page.get_text()
        return text
    except Exception:
        return ""

def clean_text(text):
    text = text.lower()
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    return text

def calculate_score(text):
    text = clean_text(text)
    matched_keywords = [kw for kw in ALL_KEYWORDS if kw in text]
    score = round((len(set(matched_keywords)) / len(ALL_KEYWORDS)) * 100)
    return min(score, 100)

@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    file_ext = os.path.splitext(file.filename)[1].lower()
    temp_file_path = f"temp{file_ext}"

    try:
        with open(temp_file_path, "wb") as f:
            f.write(await file.read())

        if file_ext == ".pdf":
            text = extract_text_from_pdf(temp_file_path)
        elif file_ext == ".docx":
            text = extract_text_from_docx(temp_file_path)
        else:
            return {"error": "Unsupported file type. Please upload a PDF or DOCX."}

        if not text.strip():
            return {"error": "Could not extract text from the file."}

        score = calculate_score(text)
        return {"ats_score": score}

    except Exception as e:
        return {"error": f"Failed to analyze resume. Error: {str(e)}"}
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000, reload=True)
