from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber
import tempfile
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔍 كلمات مفتاحية عامة شاملة لأغلب الوظائف (هندسة، محاسبة، تسويق، برمجة، خدمة عملاء، مبيعات...)
keywords = [
    # 🧑‍💻 برمجة وتقنية
    "python", "java", "sql", "html", "css", "javascript", "data analysis", "machine learning", "api", "software engineer",
    # 📊 تحليل بيانات وذكاء أعمال
    "excel", "power bi", "tableau", "dashboard", "visualization", "insights", "kpi", "business intelligence",
    # 📞 خدمة عملاء
    "customer service", "crm", "call center", "support", "resolve", "ticketing system",
    # 📢 تسويق ومبيعات
    "marketing", "sales", "seo", "social media", "facebook ads", "campaign", "promotion", "target",
    # 🏗️ هندسة ومجال صناعي
    "autocad", "welding", "pipeline", "mechanical", "electrical", "civil", "fabrication", "technical drawing", "maintenance",
    # 🧾 محاسبة ومالية
    "accounting", "tax", "journal", "ledger", "erp", "sap", "oracle", "budget", "financial analysis", "balance sheet",
    # 💼 إدارة ومهارات ناعمة
    "project management", "leadership", "teamwork", "communication", "problem solving", "time management",
    # 📚 تعليم وتدريب
    "training", "e-learning", "instruction", "curriculum", "teacher", "coach",
    # 💬 عربي (أساسي)
    "محاسبة", "ضرائب", "مشروعات", "تحليل البيانات", "مهارات التواصل", "دعم فني", "مشرف", "إدارة فريق", "إكسل", "تقارير"
]

def extract_text_from_pdf(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.file.read())
        tmp_path = tmp.name
    text = ''
    with pdfplumber.open(tmp_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    os.remove(tmp_path)
    return text

@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...)):
    try:
        text = extract_text_from_pdf(file)
        text_lower = text.lower()
        matched = [kw for kw in keywords if kw.lower() in text_lower]
        score = int((len(matched) / len(keywords)) * 100)
        return {
            "ats_score": score,
            "matched_keywords": matched,
            "total_keywords": len(keywords)
        }
    except Exception as e:
        return {"error": str(e)}
