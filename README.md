
# ATSBot Telegram Project

## 📄 Overview

**ATSBot** is a Telegram bot that:

✅ Analyzes resumes (PDF/DOCX) against job descriptions using Google Gemini API.  
✅ Provides ATS (Applicant Tracking System) match scores, missing keywords, strengths, weaknesses, and improvement tips.  
✅ Generates professional cover letters tailored to your resume and job description.

---

## 🚀 Features

- Upload resume only → Get ATS insights.
- Upload resume + job description → Get ATS comparison.
- Generate a customized cover letter from your resume (with or without a job description).
- Telegram-friendly, interactive buttons and prompts.
- Supports PDF and DOCX files.

---

## 🔧 Setup

1️⃣ **Clone the repository**
```
git clone https://github.com/kaustubhdww/ats-bot.git
cd ats-bot
```

2️⃣ **Create a `.env` file** (in the project root):
```
TELEGRAM_BOT_TOKEN=your_telegram_token
GEMINI_API_KEY=your_gemini_api_key
```

3️⃣ **Install requirements**
```
pip install -r requirements.txt
```

4️⃣ **Run the bot**
```
python app.py
```

---

## 📂 Project Structure

- `app.py` → Main Telegram bot logic.
- `downloads/` → Temporary storage for uploaded resumes.
- `.env` → Stores API keys (not committed to GitHub).
- `requirements.txt` → Python dependencies.

---

## 🌟 Future Features (Suggestions)

- Add user authentication or admin-only mode.
- Keep a log or database of past evaluations.
- Provide downloadable ATS reports (PDF or text).
- Support for other file formats (e.g., .txt, .odt).
- Add multi-language support.
- Integrate with LinkedIn profile parsing.

---

## 📜 License

This project is under the MIT License.

---

**Made with ❤️ by Kaustubh Dwivedi**
