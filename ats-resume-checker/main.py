from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import tempfile
import fitz  # PyMuPDF for PDF
import requests
from docx import Document

app = FastAPI()

# CORS setup for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with specific domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def root():
    return "✅ ATS Resume Score API is running."

@app.post("/upload-resume/")
async def analyze_resume(file: UploadFile = File(...)):
    try:
        filename = file.filename
        print("Received file:", filename)
        print("Content type:", file.content_type)

        with tempfile.NamedTemporaryFile(delete=False) as temp:
            temp.write(await file.read())
            temp.flush()
            text = ""

            # PDF handling
            if filename.endswith(".pdf"):
                doc = fitz.open(temp.name)
                for page in doc:
                    text += page.get_text()
                doc.close()

            # DOCX handling
            elif filename.endswith(".docx"):
                try:
                    docx_file = Document(temp.name)
                    text = "\n".join([para.text for para in docx_file.paragraphs])
                except Exception as e:
                    print("DOCX parsing error:", e)
                    return JSONResponse(status_code=400, content={"error": "DOCX parsing failed"})

            else:
                return JSONResponse(status_code=400, content={"error": "Unsupported file type"})

            extracted_length = len(text)
            print("Extracted text length:", extracted_length)

            # Dummy score logic based on length
            score = min(100, int(extracted_length / 30)) if extracted_length > 0 else 0
            print("ATS Score:", score)

            # Google Sheets Logging
            try:
                log_url = "https://script.google.com/macros/s/AKfycbxbSbii1A86bMyvCdMLzOOAY8YND-XAxhFmoNg3OpVCt09-VTnCu_sPkDvNvCKgFc85/exec"
                params = {
                    "filename": filename,
                    "score": score,
                    "timestamp": "now"
                }
                response = requests.get(log_url, params=params)
                print("Logged to Google Sheets:", response.status_code)
            except Exception as e:
                print("Google Sheets logging error:", e)

            return {"score": score}

    except Exception as e:
        print("General error:", str(e))
        return JSONResponse(status_code=500, content={"error": "Unknown issue"})

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000)
