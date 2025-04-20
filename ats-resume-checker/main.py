from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
import openai
import os
from docx import Document
import PyPDF2
from io import BytesIO

# ربط GPT
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

# السماح بالوصول من أي مصدر (تقدر تحدد دومين معين لاحقًا)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_text_from_pdf(file_data):
    reader = PyPDF2.PdfReader(BytesIO(file_data))
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text.strip()

def extract_text_from_docx(file_data):
    doc = Document(BytesIO(file_data))
    text = "\n".join([para.text for para in doc.paragraphs])
    return text.strip()

def analyze_with_gpt(resume_text, job_description):
    prompt = f"""
    Act like a professional ATS system.
    Compare this resume with the job description.
    Give:
    - Match percentage
    - Missing skills
    - One-line summary

    Resume:
    {resume_text}

    Job Description:
    {job_description}
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    return response.choices[0].message.content.strip()

@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...), job_description: str = ""):
    try:
        contents = await file.read()
        if file.filename.endswith(".pdf"):
            resume_text = extract_text_from_pdf(contents)
        elif file.filename.endswith(".docx"):
            resume_text = extract_text_from_docx(contents)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")

        if not job_description:
            raise HTTPException(status_code=400, detail="Job description is required")

        gpt_result = analyze_with_gpt(resume_text, job_description)

        return JSONResponse(content={
            "status": "success",
            "analysis": gpt_result
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
