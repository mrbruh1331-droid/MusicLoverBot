import os
import logging
import uuid
import json
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

# تنظیمات پیشرفته و ضدبلاک برای عبور از محدودیت‌ها
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
        "✨ **به ربات هوشمند و چندپلتفرمی دانلود موزیک و ویدیو خوش آمدید!** 🎵\n\n"
        "🌐 **امکانات ربات:**\n"
        " 🎬 **ارسال لینک:** دانلود ویدیو از هر پلتفرمی همراه با دکمه دریافت فایل صوتی.\n"
        " 🔍 **جستجوی هوشمند:** جستجوی هم‌زمان در تمام پلتفرم‌ها (YouTube, SoundCloud و...) با ارسال نام خواننده یا آهنگ.\n\n"
        "👇 *همین حالا لینک یا نام خواننده/آهنگ مورد نظرتان را بفرستید!*"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# مدیریت پیام‌ها و لینک‌ها
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    os.makedirs('downloads', exist_ok=True)

    # حالت اول: اگر کاربر لینک ارسال کرد (از هر پلتفرمی)
    if text.startswith("http://") or text.startswith("https://"):
        status_msg = await update.message.reply_text("📥 در حال پردازش و دانلود از پلتفرم مربوطه...")
        try:
            with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
                info = ydl.extract_info(text, download=False)
                title = info.get('title', 'موزیک / ویدیو')
                
            video_opts = get_ydl_opts({
                'format': 'best/bestvideo+bestaudio',
                'outtmpl': 'downloads/%(id)s.%(ext)s',
            })
            with yt_dlp.YoutubeDL(video_opts) as ydl:
                info_dl = ydl.extract_info(text, download=True)
                video_file = ydl.prepare_filename(info_dl)

            if os.path.exists(video_file):
                uid = str(uuid.uuid4())[:8]
                storage[uid] = {'url': text, 'title': title}
                save_storage(storage)

                keyboard = [[InlineKeyboardButton("🎵 دانلود فایل صوتی این ویدیو", callback_data=f"aud_{uid}")]]
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
                await status_msg.edit_text("❌ خطا در دانلود محتوا از لینک ارسالی.")

        except Exception as e:
            logger.error(e)
            await status_msg.edit_text("❌ خطا در پردازش لینک.")
    
    # حالت دوم: جستجوی نام خواننده یا آهنگ در تمام پلتفرم‌ها
    else:
        status_msg = await update.message.reply_text(f"🔍 در حال جستجوی سراسری در پلتفرم‌ها برای: *{text}*...", parse_mode="Markdown")
        try:
            search_queries = [f"ytsearch10:{text}", f"scsearch10:{text}"]
            entries = []
            
            for sq in search_queries:
                try:
                    with yt_dlp.YoutubeDL(get_ydl_opts({'extract_flat': True})) as ydl:
                        info = ydl.extract_info(sq, download=False)
                        if info and 'entries' in info:
                            entries.extend(info['entries'])
                except Exception as sub_e:
                    logger.error(f"Search query {sq} failed: {sub_e}")
                    continue

            if not entries:
                await status_msg.edit_text("❌ متأسفانه هیچ نتیجه‌ای پیدا نشد. لطفاً نام دیگری را امتحان کنید.")
                return

            keyboard = []
            for entry in entries[:15]:
                video_title = entry.get('title', 'آهنگ بدون عنوان')
                uid = str(uuid.uuid4())[:8]
                storage[uid] = {'title': video_title, 'query': video_title}
                save_storage(storage)

                button_text = f"🎵 {video_title[:38]}..." if len(video_title) > 38 else f"🎵 {video_title}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"multidl_{uid}")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await status_msg.edit_text("✨ **نتایج جستجوی چندپلتفرمی آماده است:**\n👇 آهنگ مورد نظر خود را انتخاب کنید:", reply_markup=reply_markup, parse_mode="Markdown")

        except Exception as e:
            logger.error(e)
            await status_msg.edit_text("❌ خطایی در جستجو رخ داد.")

# مدیریت دکمه‌های شیشه‌ای (ارسال آهنگ به عنوان فایل سند / Document)
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # ۱. دانلود از لیست جستجوی خواننده/آهنگ با بررسی چندپلتفرمی
    if data.startswith("multidl_"):
        uid = data.replace("multidl_", "")
        item = storage.get(uid)
        if not item:
            await query.message.reply_text("❌ اطلاعات این آهنگ منقضی شده است. لطفاً دوباره جستجو کنید.")
            return

        song_title = item['query']
        await query.message.reply_text(f"🎵 در حال بررسی تمام پلتفرم‌ها و آماده‌سازی فایل صوتی: *{song_title[:30]}*...", parse_mode="Markdown")
        
        platforms_to_check = [
            f"ytsearch1:{song_title}",
            f"scsearch1:{song_title}"
        ]
        
        success = False
        audio_file = None
        final_title = song_title
        os.makedirs('downloads', exist_ok=True)

        for platform_query in platforms_to_check:
            try:
                audio_opts = get_ydl_opts({
                    'format': 'bestaudio/best',
                    'outtmpl': 'downloads/%(id)s.%(ext)s',
                })
                
                with yt_dlp.YoutubeDL(audio_opts) as ydl:
                    info = ydl.extract_info(platform_query, download=True)
                    if 'entries' in info and info['entries']:
                        info = info['entries'][0]
                    
                    final_title = info.get('title', song_title)
                    audio_file = ydl.prepare_filename(info)
                    
                    if audio_file and os.path.exists(audio_file):
                        success = True
                        break
            except Exception as e:
                logger.error(f"Platform {platform_query} failed: {e}")
                continue

        if success and audio_file and os.path.exists(audio_file):
            # ارسال به صورت فایل سند (Document) دقیقاً مانند ربات‌های دانلود موزیک
            with open(audio_file, 'rb') as audio:
                await query.message.reply_document(
                    document=audio,
                    caption=f"🎵 **{final_title}**\n✨ دانلود شده با موفقیت",
                    parse_mode="Markdown"
                )
            os.remove(audio_file)
        else:
            await query.message.reply_text("❌ متأسفانه این آهنگ در هیچ‌کدام از پلتفرم‌ها برای دانلود در دسترس نبود.")

    # ۲. دانلود فایل صوتی از دکمه زیر ویدیوهای ارسالی
    elif data.startswith("aud_"):
        uid = data.replace("aud_", "")
        item = storage.get(uid)
        if not item:
            await query.message.reply_text("❌ اطلاعات لینک منقضی شده است. لطفاً لینک را دوباره بفرستید.")
            return

        url = item['url']
        title = item['title']
        await query.message.reply_text(f"🎵 در حال استخراج و ارسال فایل صوتی از ویدیو...", parse_mode="Markdown")
        
        try:
            os.makedirs('downloads', exist_ok=True)
            audio_opts = get_ydl_opts({
                'format': 'bestaudio/best',
                'outtmpl': 'downloads/%(id)s.%(ext)s',
            })
            
            with yt_dlp.YoutubeDL(audio_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                audio_file = ydl.prepare_filename(info)

            if os.path.exists(audio_file):
                with open(audio_file, 'rb') as audio:
                    await query.message.reply_document(
                        document=audio,
                        caption=f"🎵 **{title}**\n✨ فایل صوتی اصلی",
                        parse_mode="Markdown"
                    )
                os.remove(audio_file)
            else:
                await query.message.reply_text("❌ خطا در آماده‌سازی فایل صوتی.")

        except Exception as e:
            logger.error(e)
            await query.message.reply_text("❌ خطا در دانلود موزیک از ویدیو.")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("Document-based Multi-Platform Bot is running successfully...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
