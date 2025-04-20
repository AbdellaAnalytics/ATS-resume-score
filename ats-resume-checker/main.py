
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
    try:
        reader = PyPDF2.PdfReader(BytesIO(file_data))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        raise Exception("PDF extraction failed: " + str(e))

def extract_text_from_docx(file_data):
    try:
        doc = Document(BytesIO(file_data))
        text = "\n".join([para.text for para in doc.paragraphs])
        return text.strip()
    except Exception as e:
        raise Exception("DOCX extraction failed: " + str(e))

def calculate_score(text):
    keywords = [
        "python", "excel", "sql", "data", "project", "kpi", "power bi",
        "report", "analysis", "dashboard", "communication", "presentation"
    ]
    text_lower = text.lower()
    found = sum(text_lower.count(kw) for kw in keywords)
    score = min(100, 40 + found * 5)
    return f"✅ Resume scanned successfully.\n📌 Keywords matched: {found}\n📊 Estimated ATS Score: {score}%."

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

        result = calculate_score(resume_text)
        return JSONResponse(content={"status": "success", "analysis": result})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
