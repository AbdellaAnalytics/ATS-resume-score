import os
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PyPDF2 import PdfReader
import docx2txt
from starlette.responses import JSONResponse
from dotenv import load_dotenv
import openai

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def extract_text_from_pdf(file):
    try:
        pdf = PdfReader(file)
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        print("PDF error:", str(e))
        return ""


def extract_text_from_docx(file):
    try:
        return docx2txt.process(file)
    except Exception as e:
        print("DOCX error:", str(e))
        return ""


def analyze_with_gpt(text):
    prompt = f"""
You are an ATS resume analyzer. Read the resume below and return a JSON report that includes:

- ats_score: out of 100
- summary: a short summary of the resume
- strengths: list of key strengths
- missing_points: list of missing or weak points
- recommendations: short tips to improve

Resume:
{text[:3000]}
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You're an expert ATS resume analyzer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
        )
        content = response.choices[0].message.content.strip()
        print("GPT Response:", content[:300])
        return content
    except Exception as e:
        print("GPT error:", str(e))
        return None


@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    try:
        extension = file.filename.split(".")[-1].lower()
        contents = await file.read()

        if extension == "pdf":
            with open("temp_resume.pdf", "wb") as f:
                f.write(contents)
            resume_text = extract_text_from_pdf("temp_resume.pdf")

        elif extension == "docx":
            with open("temp_resume.docx", "wb") as f:
                f.write(contents)
            resume_text = extract_text_from_docx("temp_resume.docx")

        else:
            return JSONResponse(content={"error": "Unsupported file format"}, status_code=400)

        print("Extracted Text Sample:", resume_text[:1000])

        # استخدم GPT لو المفتاح موجود
        if openai.api_key:
            gpt_response = analyze_with_gpt(resume_text)
            if gpt_response:
                return JSONResponse(content={"gpt_result": gpt_response})
            else:
                return JSONResponse(content={"error": "Failed to get GPT analysis"}, status_code=500)
        else:
            # تحليل تقليدي بدون GPT
            word_count = len(resume_text.split())
            score = min(100, max(10, word_count // 10))
            return {
                "ats_score": score,
                "summary": "Basic analysis completed (GPT not active).",
                "strengths": ["N/A"],
                "missing_points": ["N/A"],
                "recommendations": ["Enable GPT API key for detailed analysis."]
            }

    except Exception as e:
        print("Resume error:", str(e))
        return JSONResponse(content={"error": str(e)}, status_code=500)
