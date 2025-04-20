from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import docx2txt
from PyPDF2 import PdfReader
import openai
from tempfile import NamedTemporaryFile

# OpenAI API Key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_text_from_file(file: UploadFile) -> str:
    if file.filename.endswith(".pdf"):
        reader = PdfReader(file.file)
        return " ".join(page.extract_text() for page in reader.pages if page.extract_text())
    elif file.filename.endswith(".docx"):
        with NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp.write(file.file.read())
            tmp_path = tmp.name
        return docx2txt.process(tmp_path)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type.")

def get_gpt_analysis(text: str) -> dict:
    prompt = f"""
You are an expert ATS (Applicant Tracking System) resume evaluator.

Analyze the following resume and provide:
1. ATS Score (out of 100)
2. Short Summary
3. Strengths
4. Weak Points
5. Recommendations to improve

Resume Content:
{text[:3000]}
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful resume analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4
        )
        return {"gpt_analysis": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GPT analysis failed: {str(e)}")

@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    try:
        resume_text = extract_text_from_file(file)
        gpt_response = get_gpt_analysis(resume_text)
        return gpt_response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
