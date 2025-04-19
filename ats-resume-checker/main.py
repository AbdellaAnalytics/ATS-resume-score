import os
import openai
import docx2txt
from PyPDF2 import PdfReader
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# السماح بالتفاعل مع الفرونت
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

openai.api_key = os.getenv("OPENAI_API_KEY")

@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    try:
        contents = await file.read()

        # قراءة النص من الملف
        if file.filename.endswith(".pdf"):
            pdf_reader = PdfReader(file.file)
            resume_text = ""
            for page in pdf_reader.pages:
                resume_text += page.extract_text()
        elif file.filename.endswith(".docx"):
            with open("temp.docx", "wb") as f:
                f.write(contents)
            resume_text = docx2txt.process("temp.docx")
        else:
            return {"error": "Unsupported file format. Please upload a PDF or DOCX file."}

        print("First 1000 chars of resume:\n", resume_text[:1000])

        # استخدام GPT لتحليل السكور
        prompt = f"""You are an ATS (Applicant Tracking System) Resume Analyzer.
Analyze this resume and give a score from 0 to 100 based on how well it matches a generic professional job posting.
Score only based on formatting, keywords, layout, and professionalism.

Resume:
\"\"\"
{resume_text}
\"\"\"

Score:"""

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        result = response.choices[0].message.content.strip()

        score = int("".join(filter(str.isdigit, result.split("\n")[0]))[:3])  # استخراج أول رقم ثلاثي بوضوح

        return {"ats_score": score}

    except Exception as e:
        return {"error": str(e)}
