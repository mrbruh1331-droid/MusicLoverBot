import os
import logging
import uuid
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
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

# فایل ذخیره‌سازی پایدار برای لینک‌ها
STORAGE_FILE = "storage.json"

def load_storage():
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_storage(data):
    try:
        with open(STORAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
    except:
        pass

storage = load_storage()

# 🌐 سرور سبک برای جلوگیری از به خواب رفتن ربات در هاست Render (Keep-Alive)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is active and running!")

def run_keep_alive():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"Keep-Alive server running on port {port}")
    server.serve_forever()

# تنظیمات پیشرفته و ضدبلاک (سازگار با Render بدون نیاز به FFmpeg)
def get_ydl_opts(extra_opts=None):
    opts = {
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'geo_bypass': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'mweb', 'android', 'web']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        },
    }
    if extra_opts:
        opts.update(extra_opts)
    return opts

# دستور استارت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "✨ **به ربات هوشمند دانلود موزیک و ویدیو خوش آمدید!** 🎵🎬\n\n"
        "🌐 **امکانات جامع ربات:**\n"
        " 🔗 **ارسال لینک:** دانلود و ارسال ویدیو به صورت MP4 از هر پلتفرمی همراه با دکمه **🎵 دانلود آهنگ**.\n"
        " 🎵 **ارسال نام آهنگ:** جستجو و دریافت مستقیم فایل MP4.\n"
        " 🎤 **ارسال نام خواننده:** دریافت لیست کامل آثار (بدون انقضای دکمه‌ها) و دانلود آنی.\n\n"
        "👇 *لینک یا نام مورد نظرتان را بفرستید!*"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# مدیریت پیام‌ها و لینک‌ها
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    os.makedirs('downloads', exist_ok=True)

    # حالت اول: اگر کاربر لینک ارسال کرد (از هر پلتفرمی)
    if text.startswith("http://") or text.startswith("https://"):
        status_msg = await update.message.reply_text("📥 در حال پردازش لینک و دانلود فایل MP4...")
        try:
            with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
                info = ydl.extract_info(text, download=False)
                title = info.get('title', 'محتوا')
                
            video_opts = get_ydl_opts({
                'format': 'best[ext=mp4]/best/bestvideo+bestaudio',
                'outtmpl': 'downloads/%(id)s.%(ext)s',
            })
            with yt_dlp.YoutubeDL(video_opts) as ydl:
                info_dl = ydl.extract_info(text, download=True)
                video_file = ydl.prepare_filename(info_dl)

            if os.path.exists(video_file):
                uid = str(uuid.uuid4())[:8]
                storage[uid] = {'url': text, 'title': title}
                save_storage(storage)

                keyboard = [[InlineKeyboardButton("🎵 دانلود آهنگ این ویدیو", callback_data=f"aud_{uid}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                with open(video_file, 'rb') as vid:
                    await update.message.reply_video(
                        video=vid,
                        caption=f"🎬 **{title}**\n\n👇 برای دریافت فایل صوتی این اثر به صورت MP4 روی دکمه زیر کلیک کنید:",
                        parse_mode="Markdown",
                        reply_markup=reply_markup
                    )
                os.remove(video_file)
                await status_msg.delete()
            else:
                await status_msg.edit_text("❌ خطا در دانلود فایل MP4 از لینک ارسالی.")

        except Exception as e:
            logger.error(e)
            await status_msg.edit_text("❌ خطا در پردازش لینک. لطفاً لینک معتبر بفرستید.")
    
    # حالت دوم: اگر کاربر نام آهنگ یا خواننده فرستاد (جستجوی سراسری)
    else:
        status_msg = await update.message.reply_text(f"🔍 در حال جستجو در پلتفرم‌ها برای: *{text}*...", parse_mode="Markdown")
        try:
            search_query = f"ytsearch15:{text}"
            with yt_dlp.YoutubeDL(get_ydl_opts({'extract_flat': True})) as ydl:
                info = ydl.extract_info(search_query, download=False)
                entries = info.get('entries', [])

            if not entries:
                await status_msg.edit_text("❌ متأسفانه هیچ نتیجه‌ای پیدا نشد.")
                return

            keyboard = []
            for entry in entries:
                video_title = entry.get('title', 'آهنگ بدون عنوان')
                video_id = entry.get('id', '')
                if not video_id:
                    continue
                
                button_text = f"🎵 {video_title[:38]}..." if len(video_title) > 38 else f"🎵 {video_title}"
                # استفاده از شناسه پایدار ویدیو برای دکمه‌ها (ضد انقضا صددرصد)
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"ytid_{video_id}")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await status_msg.edit_text("✨ **لیست نتایج آماده است:**\n👇 آهنگ مورد نظر خود را انتخاب کنید:", reply_markup=reply_markup, parse_mode="Markdown")

        except Exception as e:
            logger.error(e)
            await status_msg.edit_text("❌ خطایی در جستجو رخ داد.")

# مدیریت دکمه‌های شیشه‌ای برای دانلود و ارسال MP4
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # ۱. انتخاب آهنگ از لیست جستجوی نام خواننده/آهنگ با شناسه پایدار
    if data.startswith("ytid_"):
        video_id = data.replace("ytid_", "")
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        await query.message.reply_text("📥 در حال دانلود و ارسال فایل MP4...", parse_mode="Markdown")
        
        try:
            os.makedirs('downloads', exist_ok=True)
            video_opts = get_ydl_opts({
                'format': 'best[ext=mp4]/best',
                'outtmpl': 'downloads/%(id)s.%(ext)s',
            })
            
            with yt_dlp.YoutubeDL(video_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'موزیک')
                video_file = ydl.prepare_filename(info)

            if os.path.exists(video_file):
                with open(video_file, 'rb') as vid:
                    await query.message.reply_video(
                        video=vid,
                        caption=f"🎵 **{title}**\n✨ فایل MP4",
                        parse_mode="Markdown"
                    )
                os.remove(video_file)
            else:
                await query.message.reply_text("❌ خطا در آماده‌سازی فایل MP4.")

        except Exception as e:
            logger.error(e)
            await query.message.reply_text("❌ خطا در دانلود فایل.")

    # ۲. کلیک روی دکمه «دانلود آهنگ» زیر ویدیوهای ارسالی
    elif data.startswith("aud_"):
        uid = data.replace("aud_", "")
        item = storage.get(uid)
        if not item:
            await query.message.reply_text("❌ اطلاعات لینک منقضی شده است. لطفاً لینک را دوباره بفرستید.")
            return

        url = item['url']
        title = item['title']
        await query.message.reply_text(f"📥 در حال استخراج و دانلود فایل MP4 آهنگ...", parse_mode="Markdown")
        
        try:
            os.makedirs('downloads', exist_ok=True)
            video_opts = get_ydl_opts({
                'format': 'best[ext=mp4]/best',
                'outtmpl': 'downloads/%(id)s.%(ext)s',
            })
            
            with yt_dlp.YoutubeDL(video_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                video_file = ydl.prepare_filename(info)

            if os.path.exists(video_file):
                with open(video_file, 'rb') as vid:
                    await query.message.reply_video(
                        video=vid,
                        caption=f"🎵 **{title}**\n✨ فایل MP4 آهنگ",
                        parse_mode="Markdown"
                    )
                os.remove(video_file)
            else:
                await query.message.reply_text("❌ خطا در آماده‌سازی فایل MP4.")

        except Exception as e:
            logger.error(e)
            await query.message.reply_text("❌ خطا در دانلود آهنگ از ویدیو.")

def main():
    # استارت سرور Keep-Alive در پس‌زمینه برای جلوگیری از خاموشی در رندر
    threading.Thread(target=run_keep_alive, daemon=True).start()

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("Universal MP4 Bot with Keep-Alive is running successfully...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
