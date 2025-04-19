from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from docx import Document
import PyPDF2
import os
import io

app = FastAPI()

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    text = ''
    for page in reader.pages:
        text += page.extract_text() or ''
    return text

def extract_text_from_docx(file):
    doc = Document(file)
    return '\n'.join([para.text for para in doc.paragraphs])

@app.post("/upload-resume/")
async def analyze_resume(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        extension = file.filename.split('.')[-1].lower()
        
        if extension == 'pdf':
            resume_text = extract_text_from_pdf(io.BytesIO(contents))
        elif extension == 'docx':
            resume_text = extract_text_from_docx(io.BytesIO(contents))
        else:
            return {"error": "Unsupported file format. Please upload a PDF or DOCX file."}
        
        prompt = f"""
You are an AI Resume Analyzer. Analyze the following resume text and provide:
1. ATS Score (as a percentage out of 100)
2. Short summary (3-4 lines)
3. Strengths in the resume (bullet points)
4. Missing sections or weaknesses (bullet points)
5. Suggestions for improvement (bullet points)

Resume Text:
{resume_text}
"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional ATS resume reviewer."},
                {"role": "user", "content": prompt}
            ]
        )

        analysis = response.choices[0].message.content

        return {"result": analysis}

    except Exception as e:
        return {"error": str(e)}
