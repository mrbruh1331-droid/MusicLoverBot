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

# دستور استارت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "✨ **به ربات جامع و هوشمند دانلود موسیقی و ویدیو خوش آمدید!** 🎵\n\n"
        "🌐 **پشتیبانی از تمامی پلتفرم‌ها:**\n"
        " یوتیوب، اینستاگرام، تیک‌تاک، ساندکلاد، فیسبوک، توییتر و...\n\n"
        "🚀 **امکانات ربات:**\n"
        " 🎬 **ارسال لینک:** دریافت ویدیو همراه با دکمه شیشه‌ای **🎵 دانلود آهنگ**.\n"
        " 🔍 **جستجوی موزیک:** ارسال نام خواننده یا آهنگ برای دریافت لیست نتایج جامع و دانلود.\n\n"
        "👇 *همین حالا لینک یا نام آهنگ/خواننده مورد نظرتان را بفرستید!*"
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
                
            video_opts = get_ydl_opts({
                'format': 'best[ext=mp4]/best/bestvideo+bestaudio/best',
                'outtmpl': 'downloads/%(id)s.%(ext)s',
            })
            with yt_dlp.YoutubeDL(video_opts) as ydl:
                info_dl = ydl.extract_info(text
