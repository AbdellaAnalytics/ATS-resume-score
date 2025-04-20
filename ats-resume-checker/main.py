from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
import openai
import os
from docx import Document
import PyPDF2
from io import BytesIO

openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://bookmejob.com", 
        "https://www.bookmejob.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_text_from_pdf(file_data):
    try:
        reader = PyPDF2.PdfReader(BytesIO(file_data))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        raise Exception("Error reading PDF: " + str(e))

def extract_text_from_docx(file_data):
    try:
        doc = Document(BytesIO(file_data))
        text = "\n".join([para.text for para in doc.paragraphs])
        return text.strip()
    except Exception as e:
        raise Exception("Error reading DOCX: " + str(e))

def analyze_with_gpt(resume_text, job_description):
    try:
        prompt = f"""
        You are an ATS system. Compare the resume with the job description.
        Give:
        - Match percentage
        - Missing skills
        - Summary

        Resume:
        {resume_text}

        Job Description:
        {job_description}
        """

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            timeout=20  # ⏰ مهم جدًا عشان تمنع الـ hang
        )

        result = response.choices[0].message.content.strip()
        print("GPT Response:", result)
        return result
    except Exception as e:
        raise Exception("GPT error: " + str(e))

@app.post("/upload-resume/")
async def upload_resume(
    file: UploadFile = File(...),
    job_description: str = Form(...)
):
    try:
        contents = await file.read()
        if file.filename.endswith(".pdf"):
            resume_text = extract_text_from_pdf(contents)
        elif file.filename.endswith(".docx"):
            resume_text = extract_text_from_docx(contents)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")

        if not resume_text.strip():
            raise HTTPException(status_code=400, detail="Empty resume content")

        if not job_description.strip():
            raise HTTPException(status_code=400, detail="Job description is missing")

        gpt_result = analyze_with_gpt(resume_text, job_description)

        return JSONResponse(content={
            "status": "success",
            "analysis": gpt_result
        })

    except Exception as e:
        print("Server Error:", str(e))
        raise HTTPException(status_code=500, detail=str(e))
