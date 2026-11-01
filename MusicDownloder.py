import os
import logging
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import lyricsgenius
import yt_dlp

# تنظیمات لاگ‌گیری
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# توکن‌ها
TELEGRAM_TOKEN = "9166492186:AAHNeV9s7HUDDMlLKAlZy2QtCAD4ZVocIZw"
GENIUS_TOKEN = "BHPrJB0SuxHzFhtxkZRhVd0xjKHYb78FNjGl3CS7Aqwjy1GYE1yM3k2mSaicD-1z"

genius = lyricsgenius.Genius(GENIUS_TOKEN)
genius.verbose = False
genius.remove_section_headers = True

# حافظه موقت برای نگهداری اطلاعات لینک‌ها
link_store = {}

# دستور استارت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "سلام! 🎵 به ربات حرفه‌ای دانلود موزیک و ویدیو خوش آمدید.\n\n"
        "🔗 کافی است **لینک** مورد نظر خود (یوتیوب، اینستاگرام، تیک‌تاک و...) را بفرستید تا ویدیو به همراه دکمه شیشه‌ای دریافت موزیک کامل و متن برایتان ارسال شود!"
    )
    await update.message.reply_text(welcome_text)

# مدیریت پیام‌ها و لینک‌ها
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text.startswith("http://") or text.startswith("https://"):
        status_msg = await update.message.reply_text("📥 در حال پردازش لینک و دانلود ویدیو...")
        try:
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'outtmpl': 'downloads/%(title)s.%(ext)s',
                'noplaylist': True,
            }
            os.makedirs('downloads', exist_ok=True)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(text, download=True)
                video_file = ydl.prepare_filename(info)
                title = info.get('title', 'موزیک ویدیو')

            if os.path.exists(video_file):
                # ذخیره لینک و عنوان ویدیو در حافظه موقت با یک شناسهتا
                uid = str(uuid.uuid4())[:8]
                link_store[uid] = {'url': text, 'title': title}

                # ایجاد دکمه شیشه‌ای زیر ویدیو
                keyboard = [[InlineKeyboardButton("🎵 دریافت موزیک کامل به همراه متن", callback_data=f"aud_{uid}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                with open(video_file, 'rb') as vid:
                    await update.message.reply_video(
                        vid,
                        caption=f"🎬 **{title}**\n\n👇 برای دریافت صوت کامل و متن ترانه، روی دکمه زیر کلیک کنید:",
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
    else:
        await update.message.reply_text("🔍 لطفاً یک **لینک معتبر** (یوتیوب، اینستاگرام، تیک‌تاک و...) ارسال کنید.")

# مدیریت کلیک روی دکمه‌های شیشه‌ای
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("aud_"):
        uid = data.replace("aud_", "")
        stored_data = link_store.get(uid)
        if not stored_data:
            await query.message.reply_text("❌ اطلاعات لینک منقضی شده است. لطفاً دوباره لینک را ارسال کنید.")
            return

        title = stored_data['title']
        await query.message.reply_text(f"🔍 در حال جستجوی نسخه کامل و متن آهنگ: *{title}*...", parse_mode="Markdown")
        
        try:
            # ۱. جستجوی نسخه کامل و باکیفیت آهنگ در یوتیوب بر اساس نام ویدیو (به جای خود لینک کلیپ)
            search_query = f"ytsearch1:{title}"
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
                'outtmpl': 'downloads/%(title)s.%(ext)s',
                'noplaylist': True,
            }
            os.makedirs('downloads', exist_ok=True)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=True)
                if 'entries' in info:
                    info = info['entries'][0]
                song_title = info.get('title', title)
                filename = ydl.prepare_filename(info)
                audio_file = os.path.splitext(filename)[0] + ".mp3"

            # ۲. پیدا کردن متن کامل ترانه از Genius بر اساس عنوان
            song = genius.search_song(song_title)
            lyrics_text = ""
            if song and song.lyrics:
                lyrics_text = f"\n\n📜 **متن ترانه:**\n\n{song.lyrics[:3000]}"
            else:
                lyrics_text = "\n\n⚠️ متن این آهنگ در پایگاه داده یافت نشد."

            # ۳. ارسال فایل صوتی کامل به همراه متن
            if os.path.exists(audio_file):
                caption_text = f"🎵 **{song_title}**{lyrics_text}"
                
                if len(caption_text) > 1024:
                    with open(
