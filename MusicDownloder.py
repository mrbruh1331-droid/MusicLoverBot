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

# فایل ذخیره‌سازی برای لینک‌های مستقیم
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

# تنظیمات پیشرفته و ضدبلاک برای عبور از فیلترینگ یوتیوب روی سرورهای ابری
def get_ydl_opts(extra_opts=None):
    opts = {
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'geo_bypass': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'mweb', 'android']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        },
    }
    if extra_opts:
        opts.update(extra_opts)
    return opts

# دستور استارت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "✨ **به ربات حرفه‌ای دانلود موزیک و ویدیو خوش آمدید!** 🎵\n\n"
        "🌐 **امکانات جامع ربات:**\n"
        " 🎬 **ارسال لینک:** دانلود ویدیو همراه با دکمه **🎵 دانلود آهنگ**.\n"
        " 🔍 **جستجوی خواننده/آهنگ:** دریافت لیست کامل آثار و دانلود آنی.\n\n"
        "👇 *لینک یا نام خواننده مورد نظرتان را بفرستید!*"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# مدیریت پیام‌ها و لینک‌ها
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    os.makedirs('downloads', exist_ok=True)

    # حالت اول: اگر کاربر لینک فرستاد (دانلود ویدیو + دکمه آهنگ)
    if text.startswith("http://") or text.startswith("https://"):
        status_msg = await update.message.reply_text("📥 در حال دانلود ویدیو از لینک ارسالی...")
        try:
            with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
                info = ydl.extract_info(text, download=False)
                title = info.get('title', 'موزیک / ویدیو')
                
            video_opts = get_ydl_opts({
                'format': 'bestvideo+bestaudio/best/best',
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
                await status_msg.edit_text("❌ خطا در دانلود ویدیو از لینک ارسالی.")

        except Exception as e:
            logger.error(e)
            await status_msg.edit_text("❌ خطا در پردازش لینک.")
    
    # حالت دوم: اگر کاربر نام خواننده یا آهنگ فرستاد (جستجوی لیست آثار)
    else:
        status_msg = await update.message.reply_text(f"🔍 در حال جستجوی آثار: *{text}*...", parse_mode="Markdown")
        try:
            search_query = f"ytsearch20:{text}"
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
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"ytid_{video_id}")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await status_msg.edit_text("✨ **لیست نتایج آماده است:**\n👇 آهنگ مورد نظر خود را انتخاب کنید:", reply_markup=reply_markup, parse_mode="Markdown")

        except Exception as e:
            logger.error(e)
            await status_msg.edit_text("❌ خطایی در جستجو رخ داد.")

# مدیریت دکمه‌های شیشه‌ای برای دانلود صوت
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # ۱. اگر کاربر آهنگی را از لیست جستجوی خواننده انتخاب کرد
    if data.startswith("ytid_"):
        video_id = data.replace("ytid_", "")
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        await query.message.reply_text("🎵 در حال دانلود مستقیم صوت با کیفیت عالی...", parse_mode="Markdown")
        
        try:
            os.makedirs('downloads', exist_ok=True)
            audio_opts = get_ydl_opts({
                'format': 'bestaudio[ext=m4a]/bestaudio/best',
                'outtmpl': 'downloads/%(id)s.%(ext)s',
            })
            
            with yt_dlp.YoutubeDL(audio_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'موزیک')
                audio_file = ydl.prepare_filename(info)

            if os.path.exists(audio_file):
                with open(audio_file, 'rb') as audio:
                    await query.message.reply_audio(audio, caption=f"🎵 **{title}**\n✨ کیفیت عالی", parse_mode="Markdown")
                os.remove(audio_file)
            else:
                await query.message.reply_text("❌ خطا در آماده‌سازی فایل صوتی.")

        except Exception as e:
            logger.error(e)
            await query.message.reply_text("❌ خطایی در دانلود موزیک رخ داد. (احتمال محدودیت موقت سرور)")

    # ۲. اگر کاربر روی دکمه «دانلود آهنگ»ِ زیر ویدیوهای ارسالی کلیک کرد
    elif data.startswith("aud_"):
        uid = data.replace("aud_", "")
        item = storage.get(uid)
        if not item:
            await query.message.reply_text("❌ اطلاعات لینک منقضی شده است. لطفاً لینک را دوباره بفرستید.")
            return

        url = item['url']
        title = item['title']
        await query.message.reply_text(f"🎵 در حال استخراج صوت از ویدیو: *{title[:30]}*...", parse_mode="Markdown")
        
        try:
            os.makedirs('downloads', exist_ok=True)
            audio_opts = get_ydl_opts({
                'format': 'bestaudio[ext=m4a]/bestaudio/best',
                'outtmpl': 'downloads/%(id)s.%(ext)s',
            })
            
            with yt_dlp.YoutubeDL(audio_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                audio_file = ydl.prepare_filename(info)

            if os.path.exists(audio_file):
                with open(audio_file, 'rb') as audio:
                    await query.message.reply_audio(audio, caption=f"🎵 **{title}**\n✨ کیفیت عالی", parse_mode="Markdown")
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

    print("Stable Music Bot is running successfully...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
