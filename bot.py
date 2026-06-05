import os
import json
import logging
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))  # آیدی عددی ادمین
CHANNELS_FILE = "channels.json"

# ─── مدیریت کانال‌ها ───────────────────────────────────────

def load_channels():
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, "r") as f:
            return json.load(f)
    return ["@Jetnetir"]

def save_channels(channels):
    with open(CHANNELS_FILE, "w") as f:
        json.dump(channels, f)

# ─── چک جوین اجباری ────────────────────────────────────────

async def check_membership(user_id, context):
    channels = load_channels()
    not_joined = []
    for ch in channels:
        try:
            member = await context.bot.get_chat_member(ch, user_id)
            if member.status in ("left", "kicked"):
                not_joined.append(ch)
        except Exception:
            not_joined.append(ch)
    return not_joined

async def send_join_message(update, not_joined):
    buttons = [[InlineKeyboardButton(f"عضویت در {ch}", url=f"https://t.me/{ch.lstrip('@')}")] for ch in not_joined]
    buttons.append([InlineKeyboardButton("✅ عضو شدم", callback_data="check_join")])
    markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(
        "⚠️ برای استفاده از ربات باید عضو کانال‌های زیر بشی:",
        reply_markup=markup
    )

# ─── هندلرها ───────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    not_joined = await check_membership(user_id, context)
    if not_joined:
        await send_join_message(update, not_joined)
        return

    await update.message.reply_text(
        "👋 سلام به ربات Freeuploadir!\n\n"
        "لینک ویدیو بفرست تا دانلودش کنم 📥\n\n"
        "✅ پلتفرم‌های پشتیبانی‌شده:\n"
        "📸 اینستاگرام\n"
        "🎵 تیک‌تاک\n"
        "▶️ یوتیوب"
    )

async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    not_joined = await check_membership(user_id, context)
    if not_joined:
        buttons = [[InlineKeyboardButton(f"عضویت در {ch}", url=f"https://t.me/{ch.lstrip('@')}")] for ch in not_joined]
        buttons.append([InlineKeyboardButton("✅ عضو شدم", callback_data="check_join")])
        await query.edit_message_reply_markup(InlineKeyboardMarkup(buttons))
        await query.answer("هنوز عضو همه کانال‌ها نشدی! ❌", show_alert=True)
    else:
        await query.edit_message_text("✅ ممنون! حالا میتونی از ربات استفاده کنی.\n\nلینک ویدیو بفرست 👇")

# ─── پنل ادمین ─────────────────────────────────────────────

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ دسترسی ندارید!")
        return

    channels = load_channels()
    text = "⚙️ پنل مدیریت کانال‌های جوین اجباری\n\n"
    text += "📋 کانال‌های فعلی:\n"
    for i, ch in enumerate(channels, 1):
        text += f"{i}. {ch}\n"

    buttons = [
        [InlineKeyboardButton("➕ اضافه کردن کانال", callback_data="add_channel")],
        [InlineKeyboardButton("🗑 حذف کانال", callback_data="remove_channel")],
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    if query.data == "add_channel":
        context.user_data["state"] = "waiting_add_channel"
        await query.edit_message_text(
            "یوزرنیم کانال رو بفرست:\n(مثال: @mychannel)"
        )

    elif query.data == "remove_channel":
        channels = load_channels()
        if not channels:
            await query.edit_message_text("هیچ کانالی وجود نداره!")
            return
        buttons = [[InlineKeyboardButton(f"🗑 {ch}", callback_data=f"del_{ch}")] for ch in channels]
        buttons.append([InlineKeyboardButton("🔙 برگشت", callback_data="back_admin")])
        await query.edit_message_text("کدوم کانال رو حذف کنم؟", reply_markup=InlineKeyboardMarkup(buttons))

    elif query.data.startswith("del_"):
        ch = query.data[4:]
        channels = load_channels()
        if ch in channels:
            channels.remove(ch)
            save_channels(channels)
        await query.edit_message_text(f"✅ کانال {ch} حذف شد!")

    elif query.data == "back_admin":
        channels = load_channels()
        text = "⚙️ پنل مدیریت کانال‌های جوین اجباری\n\n📋 کانال‌های فعلی:\n"
        for i, ch in enumerate(channels, 1):
            text += f"{i}. {ch}\n"
        buttons = [
            [InlineKeyboardButton("➕ اضافه کردن کانال", callback_data="add_channel")],
            [InlineKeyboardButton("🗑 حذف کانال", callback_data="remove_channel")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") == "waiting_add_channel":
        ch = update.message.text.strip()
        if not ch.startswith("@"):
            ch = "@" + ch
        channels = load_channels()
        if ch in channels:
            await update.message.reply_text("این کانال قبلاً اضافه شده!")
        else:
            channels.append(ch)
            save_channels(channels)
            await update.message.reply_text(f"✅ کانال {ch} اضافه شد!")
        context.user_data["state"] = None
        return True
    return False

# ─── دانلود ویدیو ──────────────────────────────────────────

SUPPORTED_SITES = {
    "instagram.com": "اینستاگرام",
    "tiktok.com": "تیک‌تاک",
    "youtube.com": "یوتیوب",
    "youtu.be": "یوتیوب",
}

def detect_platform(url):
    for domain, name in SUPPORTED_SITES.items():
        if domain in url:
            return name
    return None

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # چک ادمین state
    if update.effective_user.id == ADMIN_ID:
        handled = await handle_admin_input(update, context)
        if handled:
            return

    user_id = update.effective_user.id
    not_joined = await check_membership(user_id, context)
    if not_joined:
        await send_join_message(update, not_joined)
        return

    url = update.message.text.strip()
    platform = detect_platform(url)

    if not platform:
        await update.message.reply_text(
            "❌ لینک پشتیبانی نمیشه!\n\n"
            "فقط اینستاگرام، تیک‌تاک و یوتیوب قبول میکنم 🙏"
        )
        return

    msg = await update.message.reply_text(f"⏳ دارم از {platform} دانلود می‌کنم...")

    try:
        ydl_opts = {
            'outtmpl': '/tmp/%(id)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'format': 'best[filesize<50M]/best[height<=720]/best',
        }
        if "youtube" in url or "youtu.be" in url:
            ydl_opts['format'] = 'bestvideo[height<=720]+bestaudio/best[height<=720]/best'
            ydl_opts['merge_output_format'] = 'mp4'

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            if not os.path.exists(file_path):
                file_path = file_path.rsplit('.', 1)[0] + '.mp4'

        await msg.edit_text("📤 دارم آپلود می‌کنم...")

        title = info.get('title', f'ویدیو از {platform}')
        caption = f"✅ دانلود شد!\n📌 {title[:200]}\n\n🤖 @jetnetuploadbot"

        with open(file_path, 'rb') as f:
            ext = file_path.split('.')[-1].lower()
            if ext in ('mp4', 'mov', 'avi', 'mkv', 'webm'):
                await update.message.reply_video(video=f, caption=caption)
            elif ext in ('jpg', 'jpeg', 'png', 'webp'):
                await update.message.reply_photo(photo=f, caption=caption)
            else:
                await update.message.reply_document(document=f, caption=caption)

        os.remove(file_path)
        await msg.delete()

    except yt_dlp.utils.DownloadError:
        await msg.edit_text("❌ نشد دانلود کنم!\n\nاحتمالاً محتوا خصوصیه یا لینک اشتباهه 🙏")
    except Exception as e:
        logging.error(f"Error: {e}")
        await msg.edit_text("❌ یه مشکلی پیش اومد، دوباره امتحان کن!")

# ─── main ──────────────────────────────────────────────────

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(check_join_callback, pattern="^check_join$"))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^(add_channel|remove_channel|back_admin|del_.+)$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))
    print("✅ ربات Freeuploadirbot شروع به کار کرد!")
    app.run_polling()

if __name__ == "__main__":
    main()
