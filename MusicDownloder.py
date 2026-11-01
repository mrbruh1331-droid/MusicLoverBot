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

# تنظیمات ضدبلاک و پیشرفته برای دور زدن محدودیت‌های سرور
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
        "✨ **به ربات جامع و هوشمند دانلود موزیک و ویدیو خوش آمدید!** 🎵\n\n"
        "🌐 **امکانات ربات:**\n"
        " 🎬 **ارسال لینک:** دانلود ویدیو از هر پلتفرمی همراه با دکمه **🎵 دانلود آهنگ**.\n"
        " 🔍 **جستجوی خواننده/آهنگ:** جستجوی سراسری در میان تمام پلتفرم‌ها و ارسال بهترین کیفیت صوتی.\n\n"
        "👇 *لینک یا نام خواننده/آهنگ مورد نظرتان را بفرستید!*"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# مدیریت پیام‌ها و لینک‌ها
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    os.makedirs('downloads', exist_ok=True)

    # حالت اول: اگر کاربر لینک فرستاد (دانلود ویدیو از هر پلتفرمی + دکمه آهنگ)
    if text.startswith("http://") or text.startswith("https://"):
        status_msg = await update.message.reply_text("📥 در حال پردازش لینک از پلتفرم مربوطه...")
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

                keyboard = [[InlineKeyboardButton("🎵 دانلود آهنگ با کیفیت عالی", callback_data=f"aud_{uid}")]]
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
    
    # حالت دوم: اگر کاربر نام خواننده یا آهنگ فرستاد (جستجوی چندپلتفرمی)
    else:
        status_msg = await update.message.reply_text(f"🔍 در حال جستجوی سراسری آثار: *{text}*...", parse_mode="Markdown")
        try:
            # جستجو در پلتفرم‌های مختلف برای جمع‌آوری کامل‌ترین لیست
            search_queries = [f"ytsearch10:{text}", f"scsearch10:{text}"]
            entries = []
            for sq in search_queries:
                try:
                    with yt_dlp.YoutubeDL(get_ydl_opts({'extract_flat': True})) as ydl:
                        info = ydl.extract_info(sq, download=False)
                        if info and 'entries' in info:
                            entries.extend(info['entries'])
                except:
                    continue

            if not entries:
                await status_msg.edit_text("❌ متأسفانه هیچ نتیجه‌ای پیدا نشد.")
                return

            keyboard = []
            for entry in entries[:20]:
                video_title = entry.get('title', 'آهنگ بدون عنوان')
                webpage_url = entry.get('url') or entry.get('id', '')
                if not webpage_url:
                    continue
                
                uid = str(uuid.uuid4())[:8]
                storage[uid] = {'url': webpage_url, 'title': video_title}
                save_storage(storage)

                button_text = f"🎵 {video_title[:38]}..." if len(video_title) > 38 else f"🎵 {video_title}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"dl_{uid}")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await status_msg.edit_text("✨ **لیست نتایج سراسری آماده است:**\n👇 آهنگ مورد نظر خود را انتخاب کنید:", reply_markup=reply_markup, parse_mode="Markdown")

        except Exception as e:
            logger.error(e)
            await status_msg.edit_text("❌ خطایی در جستجو رخ داد.")

# مدیریت دکمه‌های شیشه‌ای برای دانلود هوشمند و چندپلتفرمی صوت
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("dl_") or data.
