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

# دستور استارت شیک و جذاب
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

# مدیریت پیام‌ها
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # حالت اول: ارسال لینک
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
                # ذخیره لینک اصلی دقیقاً همان چیزی که کاربر فرستاده است
                storage[uid] = {'url': text, 'title': title}

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
    
    # حالت دوم: جستجوی نام آهنگ یا خواننده
    else:
        status_msg = await update.message.reply_text(f"🔍 در حال جستجو برای: *{text}*...", parse_mode="Markdown")
        try:
            search_query = f"ytsearch8:{text}"
            ydl_opts = {
                'noplaylist': True,
                'quiet': True,
                'extract_flat': True, # برای سرعت بالاتر و استخراج لیست نتایج
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                entries = info.get('entries', [])

            if not entries:
                await status_msg.edit_text("❌ متأسفانه هیچ نتیجه‌ای پیدا نشد. لطفاً عبارت دیگری را امتحان کنید.")
                return

            keyboard = []
            for entry in entries:
                video_title = entry.get('title', 'آهنگ بدون عنوان')
                video_id = entry.get('id', '')
                if not video_id:
                    continue
                
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                uid = str(uuid.uuid4())[:8]
                storage[uid] = {'url': video_url, 'title': video_title}
                
                button_text = f"🎵 {video_title[:42]}..." if len(video_title) > 42 else f"🎵 {video_title}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"dl_{uid}")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await status_msg.edit_text("✨ **نتایج جستجو آماده است:**\n👇 آهنگ مورد نظر خود را انتخاب کنید:", reply_markup=reply_markup, parse_mode="Markdown")

        except Exception as e:
            logger.error(e)
            await status_msg.edit_text("❌ خطایی در جستجو رخ داد.")

# مدیریت دکمه‌های شیشه‌ای
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("aud_") or data.startswith("dl_"):
        uid = data.replace("aud_", "").replace("dl_", "")
        item = storage.get(uid)
        if not item:
            await query.message.reply_text("❌ اطلاعات لینک منقضی شده است. لطفاً دوباره تلاش کنید.")
            return

        url = item['url']
        title = item['title']
        await query.message.reply_text(f"🎵 در حال دانلود صوت: *{title[:30]}*...", parse_mode="Markdown")
        
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
                    await query.message.reply_audio(audio, caption=f"🎵 **{title}**", parse_mode="Markdown")
                os.remove(audio_file)
            else:
                await query.message.reply_text("❌ خطا در آماده‌سازی فایل صوتی.")

        except Exception as e:
            logger.error(e)
            await query.message.reply_text("❌ خطایی در دانلود موزیک رخ داد.")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("Stunning Music Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
