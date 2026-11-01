import os
import logging
import yt_dlp
import lyricsgenius
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# توکن‌های شما
TELEGRAM_BOT_TOKEN = "9166492186:AAHNeV9s7HUDDMlLKAlZy2QtCAD4ZVocIZw"
GENIUS_ACCESS_TOKEN = "BHPrJB0SuxHzFhtxkZRhVd0xjKHYb78FNjGl3CS7Aqwjy1GYE1yM3k2mSaicD-1z"

# اتصال به Genius API
genius = lyricsgenius.Genius(GENIUS_ACCESS_TOKEN)
genius.verbose = False
genius.remove_section_headers = True

# دستور start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        "سلام! 👋\n\n"
        "🎶 **طرز کار ربات:**\n"
        "1️⃣ اگر **اسم آهنگ** رو به صورت متن بفرستی، هم موزیک رو دانلود می‌کنم و برات می‌فرستم و هم متن کاملش رو!\n"
        "2️⃣ اگر **فایل صوتی (موزیک)** برام بفرستی، متن (Lyrics) اون رو استخراج می‌کنم و برات می‌فرستم."
    )
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

# پردازش پیام‌ها (متن یا فایل صوتی)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = None

    # حالت اول: کاربر فایل صوتی فرستاده
    if update.message.audio:
        audio = update.message.audio
        query = f"{audio.performer} {audio.title}" if audio.performer else audio.file_name
        
        status_msg = await update.message.reply_text("🔎 در حال جستجوی متن آهنگ از روی فایل...")
        try:
            song = genius.search_song(query)
            if song:
                response = f"🎵 **{song.title}** - **{song.artist}**\n\n{song.lyrics}"
                if len(response) > 4000:
                    for i in range(0, len(response), 4000):
                        await update.message.reply_text(response[i:i+4000])
                else:
                    await status_msg.edit_text(response, parse_mode='Markdown')
            else:
                await status_msg.edit_text("❌ متأسفانه متن این آهنگ پیدا نشد.")
        except Exception as e:
            await status_msg.edit_text("⚠️ خطایی هنگام دریافت متن رخ داد.")
            print(f"Error: {e}")
            
    # حالت دوم: کاربر اسم آهنگ رو به صورت متن فرستاده
    elif update.message.text and not update.message.text.startswith('/'):
        query = update.message.text
        status_msg = await update.message.reply_text("🎧 در حال دانلود موزیک و جستجوی متن...")

        audio_file = None
        try:
            # تنظیمات دانلود موزیک با yt-dlp
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': 'downloaded_song.%(ext)s',
                'quiet': True,
                'noplaylist': True,
            }
            
            # جستجو و دانلود از اینترنت
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=True)
                filename = ydl.prepare_filename(info)
                base, _ = os.path.splitext(filename)
                for ext in ['.mp3', '.m4a', '.webm', '.opus', '.mp4']:
                    if os.path.exists(base + ext):
                        audio_file = base + ext
                        break

            # جستجوی متن در Genius
            song = genius.search_song(query)
            lyrics_text = f"🎵 **{song.title}** - **{song.artist}**\n\n{song.lyrics}" if song else "❌ متن این آهنگ پیدا نشد."

            # ارسال فایل صوتی به کاربر
            if audio_file and os.path.exists(audio_file):
                with open(audio_file, 'rb') as audio:
                    await update.message.reply_audio(audio=audio, caption=f"🎵 {query}")
                os.remove(audio_file)
            
            # ارسال متن آهنگ
            if len(lyrics_text) > 4000:
                for i in range(0, len(lyrics_text), 4000):
                    await update.message.reply_text(lyrics_text[i:i+4000])
            else:
                await status_msg.edit_text(lyrics_text, parse_mode='Markdown')

        except Exception as e:
            await status_msg.edit_text("⚠️ خطا در دانلود موزیک یا دریافت متن. لطفاً اسم دقیق‌تری بفرستید.")
            print(f"Error: {e}")
            if audio_file and os.path.exists(audio_file):
                os.remove(audio_file)

def main():
    # تنظیمات شبکه و تایم‌اوت برای عبور از تحریم
    request = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0)
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).request(request).build()

    # ثبت هندلرها (اصلاح شده و سازگار با نسخه جدید)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler((filters.TEXT | filters.AUDIO) & ~filters.COMMAND, handle_message))

    print("ربات فعال شد...")
    app.run_polling()

if __name__ == "__main__":
    main()
