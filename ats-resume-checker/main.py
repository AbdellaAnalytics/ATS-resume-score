from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from docx import Document
import PyPDF2
from io import BytesIO

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
    return f"""
✅ TEST MODE (No GPT)

📝 Resume Characters: {len(resume_text)}
📋 Job Description Characters: {len(job_description)}

📊 Analysis:
This is just a test response to confirm the frontend and backend are connected and working.
"""

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
        raise HTTPException(status_code=500, detail=str(e))
