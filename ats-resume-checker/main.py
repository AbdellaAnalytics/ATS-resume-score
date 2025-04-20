from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from docx import Document
import PyPDF2
from io import BytesIO
import os

app = FastAPI()

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

def generate_resume_score(resume_text):
    length = len(resume_text)
    keyword_count = sum(resume_text.lower().count(word) for word in [
        "python", "excel", "sql", "data", "project", "kpi", "power bi", "report", "analysis", "dashboard"
    ])
    score = min(100, 40 + keyword_count * 6)
    return f"""✅ Resume scanned.
Keywords found: {keyword_count}
Estimated ATS Score: {score}%"""

@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
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

        result = generate_resume_score(resume_text)

        return JSONResponse(content={
            "status": "success",
            "analysis": result
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
