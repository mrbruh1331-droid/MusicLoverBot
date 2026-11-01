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

# فایل ذخیره‌سازی پایدار
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

# 🌐 سرور Keep-Alive برای روشن ماندن ربات در Render
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"WhatsMusic Bot is active and running!")

def run_keep_alive():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"Keep-Alive server running on port {port}")
    server.serve_forever()

# تنظیمات ضد بلاک و چند پلتفرمی yt-dlp
def get_ydl_opts(extra_opts=None):
    opts = {
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'geo_bypass': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        },
    }
    if extra_opts:
        opts.update(extra_opts)
    return opts

# دستور استارت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "✨ **به ربات هوشمند دانلود موزیک خوش آمدید!** 🎵\n\n"
        "🎧 **راهنمای ربات:**\n"
        " 🔗 **ارسال لینک:** استخراج اطلاعات اثر و دریافت دکمه دانلود موزیک.\n"
        " 🔍 **جستجوی اسم خواننده/آهنگ:** ارسال نام برای دریافت لیست کامل و دانلود مستقیم موزیک.\n\n"
        "👇 *همین حالا نام خواننده یا لینک مورد نظرتان را ارسال کنید!*"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# مدیریت پیام‌ها
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    os.makedirs('downloads', exist_ok=True)

    # حالت اول: اگر کاربر لینک ارسال کرد
    if text.startswith("http://") or text.startswith("https://"):
        status_msg = await update.message.reply_text("🔍 در حال شناسایی موزیک...")
        try:
            with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
                info = ydl.extract_info(text, download=False)
                title = info.get('title', 'موزیک شناسایی شده')
                webpage_url = info.get('webpage_url', text)

            uid = str(uuid.uuid4())[:8]
            storage[uid] = {'query': title, 'url': webpage_url}
            save_storage(storage)

            keyboard = [
                [
                    InlineKeyboardButton("Google", url=f"https://www.google.com/search?q={title}"),
                    InlineKeyboardButton("YouTube Music", url=webpage_url),
                ],
                [
                    InlineKeyboardButton("🎵 دانلود فایل صوتی", callback_data=f"dl_{uid}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            caption_text = (
                f"🎵 **{title}**\n\n"
                f"🔍 شناسایی شده توسط ربات | @whatsmusicbot_clone"
            )

            await status_msg.delete()
            await update.message.reply_text(caption_text, parse_mode="Markdown", reply_markup=reply_markup)

        except Exception as e:
            logger.error(e)
            await status_msg.edit_text("❌ خطا در پردازش لینک.")

    # حالت دوم: جستجوی نام خواننده یا آهنگ (مثل ویدیو ارسال شده)
    else:
        status_msg = await update.message.reply_text(f"🔍 در حال جستجوی آثار برای: *{text}*...", parse_mode="Markdown")
        try:
            # اولویت جستجو در ساندکلاد و یوتیوب برای موفقیت دانلود روی سرور ابری
            search_query = f"scsearch15:{text}"
            with yt_dlp.YoutubeDL(get_ydl_opts({'extract_flat': True})) as ydl:
                info = ydl.extract_info(search_query, download=False)
                entries = info.get('entries', [])

            # اگر ساندکلاد نتیجه نداشت، یوتیوب سرچ میشه
            if not entries:
                search_query = f"ytsearch15:{text}"
                with yt_dlp.YoutubeDL(get_ydl_opts({'extract_flat': True})) as ydl:
                    info = ydl.extract_info(search_query, download=False)
                    entries = info.get('entries', [])

            if not entries:
                await status_msg.edit_text("❌ متأسفانه هیچ نتیجه‌ای پیدا نشد.")
                return

            keyboard = []
            for entry in entries[:15]:
                video_title = entry.get('title', 'آهنگ بدون عنوان')
                
                uid = str(uuid.uuid4())[:8]
                storage[uid] = {'query': video_title, 'url': entry.get('url') or entry.get('webpage_url')}
                save_storage(storage)

                button_text = f"🎵 {video_title[:40]}..." if len(video_title) > 40 else f"🎵 {video_title}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"dl_{uid}")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await status_msg.edit_text("✨ **نتایج جستجو:**\n👇 موزیک مورد نظر را جهت دانلود انتخاب کنید:", reply_markup=reply_markup, parse_mode="Markdown")

        except Exception as e:
            logger.error(e)
            await status_msg.edit_text("❌ خطایی در جستجو رخ داد.")

# مدیریت دکمه دانلود (استخراج از چند منبع برای دور زدن بلاکی Render)
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("dl_"):
        uid = data.replace("dl_", "")
        item = storage.get(uid)
        if not item:
            await query.message.reply_text("❌ اطلاعات منقضی شده است. دوباره جستجو کنید.")
            return

        song_title = item['query']
        target_url = item.get('url')
        
        status_msg = await query.message.reply_text(f"📥 در حال دانلود فایل صوتی: *{song_title[:30]}*...", parse_mode="Markdown")
        
        os.makedirs('downloads', exist_ok=True)
        audio_file = None
        success = False

        # لیست منابع دانلودی برای اطمینان از دانلود ۱۰۰٪ روی Render
        sources_to_try = []
        if target_url:
            sources_to_try.append(target_url)
        sources_to_try.append(f"scsearch1:{song_title}")
        sources_to_try.append(f"ytsearch1:{song_title}")

        for source in sources_to_try:
            try:
                audio_opts = get_ydl_opts({
                    'format': 'bestaudio/best',
                    'outtmpl': 'downloads/%(id)s.%(ext)s',
                })
                with yt_dlp.YoutubeDL(audio_opts) as ydl:
                    info = ydl.extract_info(source, download=True)
                    if 'entries' in info and info['entries']:
                        info = info['entries'][0]
                    audio_file = ydl.prepare_filename(info)

                if audio_file and os.path.exists(audio_file):
                    success = True
                    break
            except Exception as e:
                logger.error(f"Failed downloading from {source}: {e}")
                continue

        if success and audio_file and os.path.exists(audio_file):
            try:
                with open(audio_file, 'rb') as audio:
                    await query.message.reply_audio(
                        audio=audio,
                        caption=f"🎵 **{song_title}**\n✨ دانلود شده توسط ربات",
                        parse_mode="Markdown"
                    )
                os.remove(audio_file)
                await status_msg.delete()
            except Exception as send_err:
                logger.error(f"Send audio error: {send_err}")
                await status_msg.edit_text("❌ خطا در ارسال فایل صوتی به تلگرام.")
        else:
            await status_msg.edit_text("❌ دانلود این موزیک روی سرور با مشکل مواجه شد. لطفاً نام دیگری را امتحان کنید.")

def main():
    threading.Thread(target=run_keep_alive, daemon=True).start()

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("WhatsMusic Bot Clone is running...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
