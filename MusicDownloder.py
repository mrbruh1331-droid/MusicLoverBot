import os
import logging
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

# توکن‌ها و کلیدها
TELEGRAM_TOKEN = "9166492186:AAHNeV9s7HUDDMlLKAlZy2QtCAD4ZVocIZw"
GENIUS_TOKEN = "BHPrJB0SuxHzFhtxkZRhVd0xjKHYb78FNjGl3CS7Aqwjy1GYE1yM3k2mSaicD-1z"

genius = lyricsgenius.Genius(GENIUS_TOKEN)
genius.verbose = False
genius.remove_section_headers = True

# دستور استارت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "سلام! 🎵 به ربات پیشرفته موسیقی خوش آمدید.\n\n"
        "▫️ **ارسال لینک** (یوتیوب، اینستاگرام، تیک‌تاک و...): انتخاب بین ویدیو، موزیک یا متن.\n"
        "▫️ **ارسال نام خواننده/آهنگ**: جستجوی هوشمند و دریافت هم‌زمان موزیک و متن از لیست."
    )
    await update.message.reply_text(welcome_text)

# مدیریت پیام‌ها و تشخیص لینک از نام خواننده
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # حالت اول: کاربر لینک فرستاده است
    if text.startswith("http://") or text.startswith("https://"):
        context.user_data['media_url'] = text
        
        keyboard = [
            [InlineKeyboardButton("📥 دریافت ویدیو", callback_data="get_video")],
            [InlineKeyboardButton("🎵 دریافت موزیک", callback_data="get_audio")],
            [InlineKeyboardButton("📜 دریافت متن موزیک", callback_data="get_lyrics")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🔗 لینک شما دریافت شد. لطفاً یکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=reply_markup)
    
    # حالت دوم: کاربر اسم خواننده یا آهنگ فرستاده است
    else:
        await update.message.reply_text(f"🔍 در حال جستجوی آهنگ‌ها برای: *{text}*...", parse_mode="Markdown")
        try:
            songs = genius.search_songs(text, per_page=5)
            if not songs or not songs.get('songs'):
                await update.message.reply_text("❌ متأسفانه نتیجه‌ای پیدا نشد.")
                return

            keyboard = []
            for item in songs['songs']:
                song_title = item.title
                song_artist = item.primary_artist.name
                callback_data = f"dl_{item.id}"
                keyboard.append([InlineKeyboardButton(f"🎵 {song_artist} - {song_title}", callback_data=callback_data)])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("👇 لطفاً آهنگ مورد نظر خود را از لیست زیر انتخاب کنید:", reply_markup=reply_markup)

        except Exception as e:
            logger.error(f"Search error: {e}")
            await update.message.reply_text("❌ خطایی در جستجو رخ داد.")

# مدیریت دکمه‌های شیشه‌ای
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # اگر دکمه‌های مربوط به لینک بود
    if data in ["get_video", "get_audio", "get_lyrics"]:
        url = context.user_data.get('media_url')
        if not url:
            await query.edit_message_text("❌ لینک منقضی شده است. لطفاً دوباره لینک را بفرستید.")
            return

        if data == "get_lyrics":
            await query.edit_message_text("📜 در حال استخراج متن موزیک...")
            try:
                with yt_dlp.YoutubeDL({'extract_flat': True, 'skip_download': True}) as ydl:
                    info = ydl.extract_info(url, download=False)
                    title = info.get('title', '')
                
                song = genius.search_song(title)
                if song and song.lyrics:
                    lyrics_text = song.lyrics[:3900]
                    await query.message.reply_text(f"📜 متن ترانه:\n\n{lyrics_text}")
                else:
                    await query.edit_message_text("❌ متأسفانه متن این آهنگ پیدا نشد.")
            except Exception:
                await query.edit_message_text("❌ خطا در دریافت متن آهنگ.")

        elif data == "get_audio":
            await query.edit_message_text("🎵 در حال دانلود و تبدیل موزیک (لطفاً کمی صبر کنید)...")
            try:
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
                    'outtmpl': 'downloads/%(title)s.%(ext)s',
                    'noplaylist': True,
                }
                os.makedirs('downloads', exist_ok=True)
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    audio_file = os.path.splitext(filename)[0] + ".mp3"

                if os.path.exists(audio_file):
                    with open(audio_file, 'rb') as audio:
                        await query.message.reply_audio(audio)
                    os.remove(audio_file)
                    await query.edit_message_text("✅ موزیک با موفقیت ارسال شد.")
                else:
                    await query.edit_message_text("❌ خطا در آماده‌سازی فایل صوتی.")
            except Exception as e:
                logger.error(e)
                await query.edit_message_text("❌ خطا در دانلود موزیک.")

        elif data == "get_video":
            await query.edit_message_text("📥 در حال دانلود ویدیو (لطفاً کمی صبر کنید)...")
            try:
                ydl_opts = {
                    'format': 'best[ext=mp4]/best',
                    'outtmpl': 'downloads/%(title)s.%(ext)s',
                    'noplaylist': True,
                }
                os.makedirs('downloads', exist_ok=True)
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    video_file = ydl.prepare_filename(info)

                if os.path.exists(video_file):
                    with open(video_file, 'rb') as vid:
                        await query.message.reply_video(vid)
                    os.remove(video_file)
                    await query.edit_message_text("✅ ویدیو با موفقیت ارسال شد.")
                else:
                    await query.edit_message_text("❌ خطا در دانلود ویدیو.")
            except Exception as e:
                logger.error(e)
                await query.edit_message_text("❌ خطا در دانلود ویدیو.")

    # اگر کاربر از لیست نام خواننده، آهنگی را انتخاب کرد
    elif data.startswith("dl_"):
        song_id = data.replace("dl_", "")
        await query.edit_message_text("🔍 در حال دریافت اطلاعات آهنگ و متن...")
        try:
            song_info = genius.search_song_by_id(int(song_id))
            if song_info and song_info.song:
                title = song_info.song.title
                artist = song_info.song.primary_artist.name
                lyrics = song_info.song.lyrics[:3500] if song_info.song.lyrics else "متنی ثبت نشده است."
                
                # ارسال متن ترانه
                await query.message.reply_text(f"🎶 **{title}**\n👤 {artist}\n\n{lyrics}", parse_mode="Markdown")
                
                # جستجو و ارسال فایل صوتی از یوتیوب
                await query.message.reply_text("🎵 در حال جستجو و ارسال فایل صوتی...")
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
                await query.message.reply_text("❌ اطلاعات آهنگ یافت نشد.")
        except Exception as e:
            logger.error(e)
            await query.message.reply_text("❌ خطایی در پردازش درخواست رخ داد.")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("Advanced Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()

