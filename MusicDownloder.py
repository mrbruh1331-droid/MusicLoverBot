import os
import logging
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

# تنظیمات لاگ‌گیری
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# توکن ربات
TELEGRAM_TOKEN = "9166492186:AAHNeV9s7HUDDMlLKAlZy2QtCAD4ZVocIZw"

# حافظه موقت برای ذخیره لینک‌ها و شناسه‌ها
storage = {}

# دستور استارت با طراحی شیک و جذاب
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "✨ **به ربات حرفه‌ای و هوشمند موزیک خوش آمدید!** 🎵\n\n"
        "🚀 **امکانات فوق‌العاده ربات:**\n"
        " 🎬 **ارسال لینک ویدیو:** دریافت ویدیو به همراه دکمه شیشه‌ای **«🎵 دانلود آهنگ»**.\n"
        " 🎧 **ارسال لینک مستقیم موزیک:** دانلود آنی فایل صوتی.\n"
        " 🔍 **جستجوی موزیک:** ارسال نام خواننده یا آهنگ برای دریافت لیست نتایج و دانلود.\n\n"
        "👇 *همین حالا لینک یا نام آهنگ مورد نظرتان را بفرستید!*"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# مدیریت پیام‌ها (تشخیص لینک یا متن جستجو)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # حالت اول: کاربر لینک فرستاده است
    if text.startswith("http://") or text.startswith("https://"):
        status_msg = await update.message.reply_text("📥 در حال پردازش لینک و بررسی محتوا...")
        try:
            ydl_opts = {'noplaylist': True, 'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(text, download=False)
                duration = info.get('duration', 0)
                is_audio_only = info.get('vcodec') == 'none' or 'audio' in info.get('format', '')

            # اگر لینک مستقیماً فایل صوتی یا موزیک بود
            if is_audio_only or "soundcloud" in text.lower():
                await status_msg.edit_text("🎵 در حال دانلود فایل صوتی...")
                audio_opts = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
                    'outtmpl': 'downloads/%(title)s.%(ext)s',
                    'noplaylist': True,
                }
                os.makedirs('downloads', exist_ok=True)
                with yt_dlp.YoutubeDL(audio_opts) as ydl:
                    info = ydl.extract_info(text, download=True)
                    title = info.get('title', 'موزیک')
                    filename = ydl.prepare_filename(info)
                    audio_file = os.path.splitext(filename)[0] + ".mp3"

                if os.path.exists(audio_file):
                    with open(audio_file, 'rb') as audio:
                        await update.message.reply_audio(audio, caption=f"🎵 **{title}**", parse_mode="Markdown")
                    os.remove(audio_file)
                    await status_msg.delete()
                else:
                    await status_msg.edit_text("❌ خطا در دانلود فایل صوتی.")
            
            else:
                # اگر لینک ویدیو بود، ویدیو را دانلود کرده و دکمه دانلود آهنگ را زیر آن می‌گذاریم
                await status_msg.edit_text("📥 در حال دانلود ویدیو...")
                video_opts = {
                    'format': 'best[ext=mp4]/best',
                    'outtmpl': 'downloads/%(title)s.%(ext)s',
                    'noplaylist': True,
                }
                os.makedirs('downloads', exist_ok=True)
                with yt_dlp.YoutubeDL(video_opts) as ydl:
                    info = ydl.extract_info(text, download=True)
                    video_file = ydl.prepare_filename(info)
                    title = info.get('title', 'ویدیو')

                if os.path.exists(video_file):
                    uid = str(uuid.uuid4())[:8]
                    storage[uid] = {'content': text, 'title': title}

                    # دکمه شیشه‌ای جذاب زیر ویدیو
                    keyboard = [[InlineKeyboardButton("🎵 دانلود آهنگ", callback_data=f"aud_{uid}")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    with open(video_file, 'rb') as vid:
                        await update.message.reply_video(
                            vid,
                            caption=f"🎬 **{title}**\n\n👇 برای دریافت فایل صوتی این اثر روی دکمه زیر کلیک کنید:",
                            parse_mode="Markdown",
                            reply_markup=reply_markup
                        )
                    os.remove(video_file)
                    await status_msg.delete()
                else:
                    await status_msg.edit_text("❌ خطا در دانلود ویدیو.")

        except Exception as e:
            logger.error(e)
            await status_msg.edit_text("❌ خطا در پردازش لینک. لطفاً لینک معتبر دیگری بفرستید.")
    
    # حالت دوم: جستجوی نام آهنگ یا خواننده در سراسر وب
    else:
        status_msg = await update.message.reply_text(f"🔍 در حال جستجوی گسترده برای: *{text}*...", parse_mode="Markdown")
        try:
            search_query = f"ytsearch8:{text}"
            ydl_opts = {'noplaylist': True, 'quiet': True}
            
            with yt_dlp.YoutubeDL(ydl_
