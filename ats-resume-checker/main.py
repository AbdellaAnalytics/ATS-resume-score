import os
import json
import fitz  # PyMuPDF
import docx2txt
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_text_from_pdf(file_path):
    text = ""
    try:
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        print("PDF extract error:", e)
    return text

def extract_text_from_docx(file_path):
    try:
        return docx2txt.process(file_path)
    except Exception as e:
        print("DOCX extract error:", e)
        return ""

def analyze_with_gpt(text):
    prompt = f"""
    Analyze the following resume:
    {text}

    Provide:
    - An ATS compatibility score from 0 to 100
    - A short summary of the resume
    - Strengths
    - Missing keywords or weaknesses
    - Actionable recommendations

    Respond in JSON with keys: ats_score, summary, strengths, weaknesses, recommendations.
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        gpt_reply = response.choices[0].message.content
        return json.loads(gpt_reply)
    except Exception as e:
        print("GPT error:", e)
        return None

@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    file_path = f"temp_{file.filename}"
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    if file.filename.endswith(".pdf"):
        text = extract_text_from_pdf(file_path)
    elif file.filename.endswith(".docx"):
        text = extract_text_from_docx(file_path)
    else:
        return JSONResponse(status_code=400, content={"error": "Unsupported file format."})

    os.remove(file_path)

    gpt_result = analyze_with_gpt(text)
    if gpt_result:
        return gpt_result
    else:
        return JSONResponse(status_code=500, content={"error": "Failed to get GPT analysis"})
