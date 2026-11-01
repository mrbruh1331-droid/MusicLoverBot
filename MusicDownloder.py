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

# حافظه موقت برای ذخیره اطلاعات
storage = {}

# تنظیمات عمومی و ضدبلاک برای پشتیبانی از تمام پلتفرم‌ها
def get_ydl_opts(extra_opts=None):
    opts = {
        'noplaylist': True,
        'quiet': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        },
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
    }
    if extra_opts:
        opts.update(extra_opts)
    return opts

# دستور استارت شیک و جذاب
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "✨ **به ربات جامع و هوشمند دانلود موسیقی و ویدیو خوش آمدید!** 🎵\n\n"
        "🌐 **پشتیبانی از تمامی پلتفرم‌ها:**\n"
        " یوتیوب، اینستاگرام، تیک‌تاک، ساندکلاد، فیسبوک، توییتر و...\n\n"
        "🚀 **امکانات ربات:**\n"
        " 🎬 **ارسال لینک:** دریافت ویدیو/موتور همراه با دکمه شیشه‌ای **«🎵 دانلود آهنگ»**.\n"
        " 🔍 **جستجوی موزیک:** ارسال نام خواننده یا آهنگ برای دریافت لیست نتایج و دانلود.\n\n"
        "👇 *همین حالا لینک یا نام آهنگ مورد نظرتان را بفرستید!*"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# مدیریت پیام‌ها
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    os.makedirs('downloads', exist_ok=True)

    # حالت اول: ارسال لینک از هر پلتفرمی
    if text.startswith("http://") or text.startswith("https://"):
        status_msg = await update.message.reply_text("📥 در حال پردازش لینک از پلتفرم مربوطه...")
        try:
            with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
                info = ydl.extract_info(text, download=False)
                title = info.get('title', 'موزیک / ویدیو')
                
            # دانلود ویدیو یا رسانه اصلی برای نمایش به کاربر همراه با دکمه
            video_opts = get_ydl_opts({
                'format': 'best[ext=mp4]/best/bestvideo+bestaudio/best',
                'outtmpl': 'downloads/%(id)s.%(ext)s',
            })
            with yt_dlp.YoutubeDL(video_opts) as ydl:
                info_dl = ydl.extract_info(text, download=True)
                file_id = info_dl.get('id', str(uuid.uuid4())[:8])
                video_file = ydl.prepare_filename(info_dl)

            if os.path.exists(video_file):
                uid = str(uuid.uuid4())[:8]
                storage[uid] = {'url': text, 'title': title}

                keyboard = [[InlineKeyboardButton("🎵 دانلود آهنگ", callback_data=f"aud_{uid}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                # ارسال به عنوان ویدیو یا فایل صوتی بر اساس نوع خروجی
                if video_file.endswith(('.mp3', '.m4a', '.webm', '.opus', '.wav')):
                    with open(video_file, 'rb') as audio:
                        await update.message.reply_audio(audio, caption=f"🎵 **{title}**", parse_mode="Markdown")
                    os.remove(video_file)
                else:
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
                await status_msg.edit_text("❌ خطا در دانلود محتوا از لینک ارسالی.")

        except Exception as e:
            logger.error(e)
            await status_msg.edit_text("❌ خطا در پردازش لینک. لطفاً از پلتفرم دیگری امتحان کنید.")
    
    # حالت دوم: جستجوی نام آهنگ یا خواننده
    else:
        status_msg = await update.message.reply_text(f"🔍 در حال جستجو برای: *{text}*...", parse_mode="Markdown")
        try:
            search_query = f"ytsearch6:{text}"
            with yt_dlp.YoutubeDL(get_ydl_opts({'extract_flat': True})) as ydl:
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
                
                button_text = f"🎵 {video_title[:40]}..." if len(video_title) > 40 else f"🎵 {video_title}"
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
        uid = data.split("_")[1]
        item = storage.get(uid)
        if not item:
            await query.message.reply_text("❌ اطلاعات لینک منقضی شده است. لطفاً دوباره تلاش کنید.")
            return

        url = item['url']
        title = item['title']
        await query.message.reply_text(f"🎵 در حال استخراج و دانلود صوت: *{title[:30]}*...", parse_mode="Markdown")
        
        try:
            os.makedirs('downloads', exist_ok=True)
            audio_opts = get_ydl_opts({
                'format': 'bestaudio/best',
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
                'outtmpl': 'downloads/%(id)s.%(ext)s',
            })
            
            with yt_dlp.YoutubeDL(audio_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_id = info.get('id', str(uuid.uuid4())[:8])
                audio_file = os.path.join('downloads', f"{file_id}.mp3")

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

    print("Universal Music Bot is running successfully...")
    application.run_polling()

if __name__ == '__main__':
    main()
