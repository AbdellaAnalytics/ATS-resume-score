from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import docx2txt
import pdfplumber
import tempfile
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

# Keywords in English and Arabic
keywords = [
    "Python", "SQL", "Excel", "Power BI", "data analysis", "communication",
    "بايثون", "إكسل", "تحليل البيانات", "تنسيق", "مهارات التواصل", "باور بي آي"
]

def extract_text_from_docx(file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name
    text = docx2txt.process(tmp_path)
    os.remove(tmp_path)
    return text

def extract_text_from_pdf(file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name
    text = ""
    with pdfplumber.open(tmp_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    os.remove(tmp_path)
    return text

@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    try:
        filename = file.filename.lower()
        if filename.endswith(".docx"):
            text = extract_text_from_docx(file)
        elif filename.endswith(".pdf"):
            text = extract_text_from_pdf(file)
        else:
            return {"error": "Unsupported file format. Please upload a .pdf or .docx file."}

        text = text.lower()
        score = sum(1 for word in keywords if word.lower() in text)
        ats_score = int((score / len(keywords)) * 100)

        return {"ats_score": ats_score}

    except Exception as e:
        return {"error": str(e)}
