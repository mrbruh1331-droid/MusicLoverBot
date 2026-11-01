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

# 🌐 سرور Keep-Alive برای روشن ماندن ۲۴ ساعته در هاست Render
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

# تنظیمات ضد بلاک yt-dlp
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
        "✨ **به ربات هوشمند دانلود موزیک و ویدیو خوش آمدید!** 🎵🎬[span_3](start_span)[span_3](end_span)\n\n"
        "🎧 **امکانات ربات:**\n"
        " 🔗 **ارسال لینک (یوتیوب، اینستاگرام و...):** دانلود ویدیو + دانلود فایل صوتی کامل اثر[span_4](start_span)[span_4](end_span).\n"
        " 🔍 **ارسال نام خواننده/آهنگ:** جستجوی هوشمند و دریافت مستقیم فایل صوتی[span_5](start_span)[span_5](end_span).\n\n"
        "👇 *همین حالا نام آهنگ یا لینک مورد نظرتان را بفرستید!*"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# مدیریت پیام‌ها
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    os.makedirs('downloads', exist_ok=True)

    # حالت اول: اگر کاربر لینک ارسال کرد (دانلود ویدیو + قرار دادن دکمه دانلود موزیک)
    if text.startswith("http://") or text.startswith("https://"):
        status_msg = await update.message.reply_text("📥 در حال پردازش لینک و دانلود ویدیو...")
        try:
            # دریافت اطلاعات اولیه لینک
            with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
                info = ydl.extract_info(text, download=False)
                title = info.get('title', 'ویدیو شناسایی شده')
                webpage_url = info.get('webpage_url', text)

            # دانلود فایل ویدیویی (MP4)
            video_opts = get_ydl_opts({
                'format': 'best[ext=mp4]/best/bestvideo+bestaudio',
                'outtmpl': 'downloads/%(id)s.%(ext)s',
            })
            with yt_dlp.YoutubeDL(video_opts) as ydl:
                info_dl = ydl.extract_info(text, download=True)
                video_file = ydl.prepare_filename(info_dl)

            uid = str(uuid.uuid4())[:8]
            storage[uid] = {'query': title, 'url': webpage_url}
            save_storage(storage)

            # طراحی دکمه‌ها
            keyboard = [
                [
                    InlineKeyboardButton("Google", url=f"https://www.google.com/search?q={title}"),
                    InlineKeyboardButton("YouTube Music", url=webpage_url),
                ],
                [
                    InlineKeyboardButton("🎵 دانلود آهنگ کامل این ویدیو", callback_data=f"dl_{uid}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            caption_text = (
                f"🎬 **{title}**\n\n"
                f"👇 برای دریافت فایل صوتی کامل این اثر روی دکمه زیر کلیک کنید:[span_6](start_span)[span_6](end_span)"
            )

            if os.path.exists(video_file):
                with open(video_file, 'rb') as vid:
                    await update.message.reply_video(
                        video=vid,
                        caption=caption_text,
                        parse_mode="Markdown",
                        reply_markup=reply_markup
                    )
                os.remove(video_file)
                await status_msg.delete()
            else:
                await status_msg.edit_text("❌ خطا در آماده‌سازی فایل ویدیو.")

        except Exception as e:
            logger.error(e)
            await status_msg.edit_text("❌ خطا در پردازش و دانلود لینک.")

    # حالت دوم: جستجوی نام خواننده یا آهنگ (مثل WhatsMusicBot)
    else:
        status_msg = await update.message.reply_text(f"🔍 در حال جستجوی آثار برای: *{text}*...", parse_mode="Markdown")
        try:
            search_query = f"scsearch15:{text}"
            with yt_dlp.YoutubeDL(get_ydl_opts({'extract_flat': True})) as ydl:
                info = ydl.extract_info(search_query, download=False)
                entries = info.get('entries', [])

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
            await status_msg.edit_text("✨ **نتایج جستجو:**\n👇 موزیک مورد نظر را جهت دانلود انتخاب کنید:[span_7](start_span)[span_7](end_span)", reply_markup=reply_markup, parse_mode="Markdown")

        except Exception as e:
            logger.error(e)
            await status_msg.edit_text("❌ خطایی در جستجو رخ داد.")

# مدیریت دکمه دانلود فایل صوتی
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("dl_"):
        uid = data.replace("dl_", "")
        item = storage.get(uid)
        if not item:
            await query.message.reply_text("❌ اطلاعات منقضی شده است. لطفاً دوباره امتحان کنید.")
            return

        song_title = item['query']
        target_url = item.get('url')
        
        status_msg = await query.message.reply_text(f"📥 در حال دانلود فایل صوتی: *{song_title[:30]}*...", parse_mode="Markdown")
        
        os.makedirs('downloads', exist_ok=True)
        audio_file = None
        success = False

        sources_to_try = []
        if target_url:
            sources_to_try.append(target_url)
        sources_to_try.append(f"scsearch1:{song_title}")
        sources_to_try.append(f"ytsearch1:{song_title}")

        for source in sources_to_try:
            try:
                audio_opts = get_ydl_opts({
                    'format': 'bestaudio[ext=m4a]/bestaudio/best',
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
                logger.error(f"Failed downloading audio from {source}: {e}")
                continue

        if success and audio_file and os.path.exists(audio_file):
            try:
                with open(audio_file, 'rb') as audio:
                    await query.message.reply_audio(
                        audio=audio,
                        caption=f"🎵 **{song_title}**\n✨ فایل صوتی کامل[span_8](start_span)[span_8](end_span)",
                        parse_mode="Markdown"
                    )
                os.remove(audio_file)
                await status_msg.delete()
            except Exception as send_err:
                logger.error(f"Send audio error: {send_err}")
                await status_msg.edit_text("❌ خطا در ارسال فایل صوتی.")
        else:
            await status_msg.edit_text("❌ دانلود این فایل صوتی با مشکل مواجه شد.")

def main():
    threading.Thread(target=run_keep_alive, daemon=True).start()

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("WhatsMusic Complete Bot is running...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
