import os
import glob
import logging
import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from PyPDF2 import PdfReader
import docx

# Load .env
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise ValueError("❌ Missing TELEGRAM_BOT_TOKEN or GEMINI_API_KEY in .env file!")

def extract_text_from_pdf(file_path):
    try:
        with open(file_path, 'rb') as f:
            reader = PdfReader(f)
            return ''.join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        logger.error(f"Error reading PDF: {str(e)}")
        return f"❌ Error reading PDF: {str(e)}"

def extract_text_from_docx(file_path):
    try:
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        logger.error(f"Error reading DOCX: {str(e)}")
        return f"❌ Error reading DOCX: {str(e)}"

def query_gemini(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        if 'candidates' in data and data['candidates']:
            return data['candidates'][0]['content']['parts'][0]['text']
        return "❌ No valid response from Gemini API."
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {str(e)}")
        return f"❌ API request failed: {str(e)}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📝 Provide Job Description", callback_data='provide_jd')],
        [InlineKeyboardButton("📄 Upload Resume Only", callback_data='upload_resume')],
        [InlineKeyboardButton("✉️ Generate Cover Letter", callback_data='generate_cover')],
        [InlineKeyboardButton("🔄 Restart (Start Fresh)", callback_data='restart')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text("👋 Welcome! Please choose an option:", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text("👋 Welcome! Please choose an option:", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'provide_jd':
        context.user_data['mode'] = 'waiting_for_jd'
        await query.edit_message_text("✏️ Please send the job description text.")

    elif query.data == 'upload_resume':
        context.user_data['mode'] = 'resume_only'
        await query.edit_message_text("📤 Please upload your resume (PDF or DOCX).")

    elif query.data == 'generate_cover':
        context.user_data['mode'] = 'waiting_for_cover_resume'
        await query.edit_message_text("📤 Please upload your resume (PDF or DOCX) for the cover letter.")

    elif query.data == 'skip_jd':
        await generate_cover_letter(update, context)

    elif query.data == 'restart':
        context.user_data.clear()
        await start(update, context)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    file_path = os.path.join("downloads", update.message.document.file_name)
    os.makedirs("downloads", exist_ok=True)
    await file.download_to_drive(file_path)
    logger.info(f"File downloaded: {file_path}")

    if file_path.endswith('.pdf'):
        resume_text = extract_text_from_pdf(file_path)
    elif file_path.endswith('.docx'):
        resume_text = extract_text_from_docx(file_path)
    else:
        await update.message.reply_text("❌ Unsupported file type. Please upload a PDF or DOCX.")
        return

    context.user_data['resume'] = resume_text

    if context.user_data.get('mode') == 'waiting_for_resume':
        await process_ats(update, context)
    elif context.user_data.get('mode') == 'resume_only':
        await process_ats(update, context)
    elif context.user_data.get('mode') == 'waiting_for_cover_resume':
        context.user_data['mode'] = 'waiting_for_cover_jd'
        keyboard = [[InlineKeyboardButton("Skip Job Description", callback_data='skip_jd')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("✏️ (Optional) Send the job description text, or tap 'Skip Job Description'.", reply_markup=reply_markup)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('mode') == 'waiting_for_jd':
        context.user_data['job_description'] = update.message.text
        context.user_data['mode'] = 'waiting_for_resume'
        await update.message.reply_text("📤 Now, please upload your resume (PDF or DOCX).")

    elif context.user_data.get('mode') == 'waiting_for_cover_jd':
        context.user_data['job_description'] = update.message.text
        await generate_cover_letter(update, context)

async def process_ats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resume = context.user_data.get('resume')
    job_description = context.user_data.get('job_description')

    if context.user_data.get('mode') == 'resume_only' and resume:
        prompt = f"""
You are an ATS evaluator. Analyze this resume briefly.

Resume:
{resume}

Provide only:
✅ ATS Match Percentage 
✅ Top 3-5 Missing Keywords
✅ 2 Key Strengths
✅ 2 Main Weaknesses
✅ 2-3 Concrete Improvement Suggestions

Keep the response clear, short, and within ~500 words.
"""
    elif resume and job_description:
        prompt = f"""
You are an ATS evaluator. Compare this resume and job description briefly.

Resume:
{resume}

Job Description:
{job_description}

Provide only:
✅ ATS Match Percentage 
✅ Top 3-5 Missing Keywords
✅ 2 Key Strengths
✅ 2 Main Weaknesses
✅ 2-3 Concrete Improvement Suggestions

Keep the response clear, short, and within ~500 words.
"""
    else:
        await update.message.reply_text("❌ Missing resume or job description.")
        return

    result = query_gemini(prompt)

    if len(result) > 3800:
        result = result[:3800] + "\n\n⚠️ Output truncated to fit Telegram limits."

    await update.message.reply_text(f"🎯 Here’s your ATS Evaluation:\n\n{result}")
    keyboard = [[InlineKeyboardButton("🔄 Restart", callback_data='restart')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("✅ Done! You can restart if you want:", reply_markup=reply_markup)
    cleanup_files()

async def generate_cover_letter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resume = context.user_data.get('resume')
    job_description = context.user_data.get('job_description', '')

    prompt = f"""
You are a professional cover letter writer.

Based on the following resume and {( 'job description' if job_description else 'general job market' )}, draft a concise, engaging, and tailored cover letter.

Resume:
{resume}

{f"Job Description:\n{job_description}" if job_description else ""}

Provide only the cover letter, structured with:
✅ A strong opening paragraph
✅ Key highlights/skills
✅ Closing paragraph with a call to action

Keep it under 400 words, friendly yet professional.
"""

    result = query_gemini(prompt)

    if not result or len(result.strip()) == 0:
        if update.callback_query:
            await update.callback_query.message.reply_text("❌ Error: No response received for cover letter generation.")
        else:
            await update.message.reply_text("❌ Error: No response received for cover letter generation.")
        return

    if update.callback_query:
        await update.callback_query.message.reply_text(f"✉️ Here’s your Cover Letter:\n\n{result}")
        keyboard = [[InlineKeyboardButton("🔄 Restart", callback_data='restart')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.reply_text("✅ Done! You can restart if you want:", reply_markup=reply_markup)
    else:
        await update.message.reply_text(f"✉️ Here’s your Cover Letter:\n\n{result}")
        keyboard = [[InlineKeyboardButton("🔄 Restart", callback_data='restart')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("✅ Done! You can restart if you want:", reply_markup=reply_markup)

    cleanup_files()

def cleanup_files():
    try:
        files = glob.glob(os.path.join("downloads", "*"))
        for f in files:
            os.remove(f)
        logger.info("✅ Cleaned up downloads folder.")
    except Exception as e:
        logger.error(f"⚠️ Failed to clean up downloads folder: {str(e)}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(button))
    logger.info("Bot started!")
    app.run_polling()

if __name__ == "__main__":
    main()
