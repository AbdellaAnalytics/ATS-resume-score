from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from docx import Document
from PyPDF2 import PdfReader
import json
import os

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load all keywords from keywords.json
with open("keywords.json", "r", encoding="utf-8") as file:
    KEYWORDS = json.load(file)

# Helper function to extract text from PDF
def extract_text_from_pdf(file):
    try:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        return ""

# Helper function to extract text from DOCX
def extract_text_from_docx(file):
    try:
        doc = Document(file)
        return " ".join([para.text for para in doc.paragraphs])
    except Exception as e:
        return ""

# Score calculation
def calculate_score(text):
    text = text.lower()
    found_keywords = set()
    total_keywords = 0

    for category in KEYWORDS:
        keywords = category.get("keywords", [])
        total_keywords += len(keywords)
        for keyword in keywords:
            if keyword.lower() in text:
                found_keywords.add(keyword.lower())

    if total_keywords == 0:
        return 0

    score = round((len(found_keywords) / total_keywords) * 100)
    return score

@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    contents = await file.read()
    extension = os.path.splitext(file.filename)[1].lower()

    if extension == ".pdf":
        with open("temp.pdf", "wb") as f:
            f.write(contents)
        text = extract_text_from_pdf("temp.pdf")
        os.remove("temp.pdf")

    elif extension == ".docx":
        with open("temp.docx", "wb") as f:
            f.write(contents)
        text = extract_text_from_docx("temp.docx")
        os.remove("temp.docx")

    else:
        return {"error": "Unsupported file format. Please upload a PDF or DOCX file."}

    if not text.strip():
        return {"error": "Could not extract text from the resume. Make sure the file is not scanned or empty."}

    score = calculate_score(text)
    return {"ats_score": score}
