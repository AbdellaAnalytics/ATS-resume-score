import os
import openai

# تحميل مفتاح API من المتغير البيئي
openai.api_key = os.getenv("OPENAI_API_KEY")

def analyze_resume(resume_text):
    resume_text = resume_text[:2000]  # تحديد الحد الأقصى للنص لتفادي أخطاء الطول

    messages = [
        {
            "role": "system",
            "content": (
                "You are an ATS (Applicant Tracking System) resume analyzer. "
                "Analyze the resume and return:\n\n"
                "1. ✅ ATS Score (percentage)\n"
                "2. 📄 Summary of the resume\n"
                "3. 💪 Strengths\n"
                "4. ❌ Missing important keywords\n"
                "5. 🛠 Suggestions to improve the resume\n\n"
                "Be clear, structured and professional."
            )
        },
        {"role": "user", "content": resume_text}
    ]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.3
    )

    return response.choices[0].message.content

# مثال لاختبار الكود
if __name__ == "__main__":
    example_resume = """
    Mohamed Abdella is a data analyst and accountant with 11 years at Coca-Cola. 
    He is skilled in Excel, Power BI, SQL, Python, Tableau, and financial analysis.
    He has worked in roles like Sales Analyst, Business Intelligence, and Cost Control.
    """
    result = analyze_resume(example_resume)
    print(result)
