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
        "🔗 کافی است **لینک** مورد نظر خود (یوتیوب، اینستاگرام، تیک‌تاک و...) را بفرستید تا ویدیو به همراه دکمه‌های جداگانه برای دریافت موزیک و متن برایتان ارسال شود!"
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
                uid = str(uuid.uuid4())[:8]
                link_store[uid] = {'url': text, 'title': title}

                # ساخت دو دکمه شیشه‌ای جداگانه برای موزیک و متن
                keyboard = [
                    [InlineKeyboardButton("🎵 دریافت موزیک", callback_data=f"aud_{uid}")],
                    [InlineKeyboardButton("📜 دریافت متن آهنگ", callback_data=f"lyr_{uid}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                with open(video_file, 'rb') as vid:
                    await update.message.reply_video(
                        vid,
                        caption=f"🎬 **{title}**\n\n👇 یکی از گزینه‌های زیر را انتخاب کنید:",
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

    # اگر کاربر روی دکمه دریافت موزیک کلیک کرد
    if data.startswith("aud_"):
        uid = data.replace("aud_", "")
        stored_data = link_store.get(uid)
        if not stored_data:
            await query.message.reply_text("❌ اطلاعات لینک منقضی شده است. لطفاً دوباره لینک را ارسال کنید.")
            return

        title = stored_data['title']
        await query.message.reply_text(f"🎵 در حال جستجو و دانلود نسخه کامل آهنگ: *{title}*...", parse_mode="Markdown")
        
        try:
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

            if os.path.exists(audio_file):
                with open(audio_file, 'rb') as audio:
                    await query.message.reply_audio(audio, caption=f"🎵 {song_title}")
                os.remove(audio_file)
            else:
                await query.message.reply_text("❌ خطا در آماده‌سازی فایل صوتی.")

        except Exception as e:
            logger.error(e)
            await query.message.reply_text("❌ خطایی در دانلود موزیک رخ داد.")

    # اگر کاربر روی دکمه دریافت متن آهنگ کلیک کرد
    elif data.startswith("lyr_"):
        uid = data.replace("lyr_", "")
        stored_data = link_store.get(uid)
        if not stored_data:
            await query.message.reply_text("❌ اطلاعات لینک منقضی شده است. لطفاً دوباره لینک را ارسال کنید.")
            return

        title = stored_data['title']
        await query.message.reply_text(f"📜 در حال جستجوی متن آهنگ: *{title}*...", parse_mode="Markdown")
        
        try:
            song = genius.search_song(title)
            if song and song.lyrics:
                lyrics_text = song.lyrics[:4000]
                await query.message.reply_text(f"📜 **متن ترانه ({title}):**\n\n{lyrics_text}", parse_mode="Markdown")
            else:
                await query.message.reply_text("❌ متأسفانه متن این آهنگ در پایگاه داده یافت نشد.")
        except Exception as e:
            logger.error(e)
            await query.message.reply_text("❌ خطایی در دریافت متن رخ داد.")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
