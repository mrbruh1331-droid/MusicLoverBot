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
        "سلام! 🎵 به ربات حرفه‌ای موسیقی خوش آمدید.\n\n"
        "🔗 **ارسال لینک:** دانلود ویدیو به همراه دکمه شیشه‌ای دریافت موزیک.\n"
        "🔍 **ارسال نام خواننده یا آهنگ:** جستجو در بین هزاران موزیک و دانلود آنی."
    )
    await update.message.reply_text(welcome_text)

# مدیریت پیام‌ها (تشخیص لینک یا متن جستجو)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # حالت اول: کاربر لینک فرستاده است
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
                link_store[uid] = {'title': title}

                # دکمه شیشه‌ای برای دانلود موزیک زیر ویدیو
                keyboard = [[InlineKeyboardButton("🎵 دریافت موزیک", callback_data=f"aud_{uid}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                with open(video_file, 'rb') as vid:
                    await update.message.reply_video(
                        vid,
                        caption=f"🎬 **{title}**\n\n👇 برای دریافت فایل صوتی کامل روی دکمه زیر کلیک کنید:",
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
    
    # حالت دوم: کاربر نام خواننده یا آهنگ فرستاده است
    else:
        status_msg = await update.message.reply_text(f"🔍 در حال جستجوی آهنگ برای: *{text}*...", parse_mode="Markdown")
        try:
            songs = genius.search_songs(text, per_page=5)
            if not songs or 'songs' not in songs or not songs['songs']:
                await status_msg.edit_text("❌ متأسفانه نتیجه‌ای پیدا نشد.")
                return

            keyboard = []
            for item in songs['songs']:
                song_title = item.title
                song_artist = item.primary_artist.name
                callback_data = f"dl_{item.id}"
                keyboard.append([InlineKeyboardButton(f"🎵 {song_artist} - {song_title}", callback_data=callback_data)])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await status_msg.edit_text("👇 لطفاً آهنگ مورد نظر خود را از لیست زیر انتخاب کنید:", reply_markup=reply_markup)

        except Exception as e:
            logger.error(e)
            await status_msg.edit_text("❌ خطایی در جستجو رخ داد.")

# مدیریت دکمه‌های شیشه‌ای
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # اگر دکمه مربوط به دانلود موزیک از روی لینک بود
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

    # اگر کاربر آهنگی را از لیست جستجوی متنی انتخاب کرد
    elif data.startswith("dl_"):
        song_id = data.replace("dl_", "")
        await query.edit_message_text("🔍 در حال دریافت و دانلود آهنگ انتخابی...")
        try:
            song_info = genius.search_song_by_id(int(song_id))
            if song_info and song_info.song:
                title = song_info.song.title
                artist = song_info.song.primary_artist.name
                
                search_query = f"ytsearch1:{artist} - {title}"
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
                    filename = ydl.prepare_filename(info)
                    audio_file = os.path.splitext(filename)[0] + ".mp3"

                if os.path.exists(audio_file):
                    with open(audio_file, 'rb') as audio:
                        await query.message.reply_audio(audio, caption=f"🎵 {title} - {artist}")
                    os.remove(audio_file)
                else:
                    await query.message.reply_text("❌ فایل صوتی پیدا نشد.")
            else:
                await query.message.reply_text("❌ اطلاعات آهنگ یافت نشد.")
        except Exception as e:
            logger.error(e)
            await query.message.reply_text("❌ خطایی در پردازش درخواست رخ داد.")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
