logger.info("Bot is starting...")
import logging
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder, ContextTypes,
    CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ConversationHandler
)
from asyncio import sleep

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ['BOT_TOKEN']
ADMIN_IDS = list(map(int, os.environ['ADMIN_IDS'].split(',')))
CHANNEL_ID = os.environ['CHANNEL_ID']

# States
WAITING_MEDIA, WAITING_CAPTION = range(2)

# Temp user data
user_state = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("شما اجازه استفاده از این ربات را ندارید.")
    await update.message.reply_text("سلام! یه پیام فوروارد شده بفرست.")

    return WAITING_MEDIA

async def receive_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return

    message = update.message
    if not message.forward_date:
        return await message.reply_text("لطفاً فقط پیام *فوروارد شده* ارسال کنید.", parse_mode="Markdown")

    user_id = update.effective_user.id
    user_state[user_id] = {
        'message': message,
        'media_type': 'media_group_id' if message.media_group_id else 'single',
        'files': [message],
    }

    await message.reply_text("کپشن دلخواه رو بنویس یا روی دکمه بازگشت بزن.",
                             reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت", callback_data="back")]]))
    return WAITING_CAPTION

async def receive_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    if user_id not in user_state:
        return await update.message.reply_text("دوباره شروع کن.")

    formatted_caption = f"{text}\n\n🔥@hottof | تُفِ داغ"
    user_state[user_id]['caption'] = formatted_caption

    # پیش‌نمایش
    files = user_state[user_id]['files']
    preview_msg = await update.message.reply_text("پیش‌نمایش آماده‌ست. یکی از گزینه‌ها رو انتخاب کن:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("ارسال", callback_data="send_now")],
            [InlineKeyboardButton("تایمر", callback_data="set_timer")],
            [InlineKeyboardButton("بازگشت", callback_data="back")]
        ])
    )

    user_state[user_id]['preview_msg'] = preview_msg
    return ConversationHandler.END

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "back":
        user_state.pop(user_id, None)
        return await query.message.reply_text("فرایند لغو شد. از نو شروع کن. لطفاً یک پیام فوروارد بفرست.")

    if query.data == "send_now":
        await send_to_channel(context, user_id)
        return await query.message.reply_text("ارسال شد! برای پیام جدید، فوروارد بده.")

    if query.data == "set_timer":
        await query.message.reply_text("لطفاً عدد دقیقه رو بفرست.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت", callback_data="back")]]))
        return 3  # state برای گرفتن عدد

async def timer_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        minutes = int(update.message.text)
    except:
        return await update.message.reply_text("عدد معتبر وارد کن.")

    await update.message.reply_text(f"{minutes} دقیقه بعد ارسال میشه...")
    await sleep(minutes * 60)
    await send_to_channel(context, user_id)
    return await update.message.reply_text("ارسال زمان‌دار انجام شد! برای پیام جدید، فوروارد بده.")

async def send_to_channel(context, user_id):
    data = user_state.get(user_id)
    if not data:
        return

    caption = data.get('caption')
    files = data['files']
    for msg in files:
        if msg.photo:
            await context.bot.send_photo(CHANNEL_ID, photo=msg.photo[-1].file_id, caption=caption)
        elif msg.video:
            await context.bot.send_video(CHANNEL_ID, video=msg.video.file_id, caption=caption)
        elif msg.document:
            await context.bot.send_document(CHANNEL_ID, document=msg.document.file_id, caption=caption)
    user_state.pop(user_id, None)

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_MEDIA: [MessageHandler(filters.ALL & filters.FORWARDED, receive_forward)],
            WAITING_CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_caption)],
            3: [MessageHandler(filters.TEXT, timer_input)]
        },
        fallbacks=[CallbackQueryHandler(button_handler)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler))

    # Webhook setup
    app.run_webhook(
        listen="0.0.0.0",
        port=10000,
        webhook_url=os.environ['WEBHOOK_URL']
    )

if __name__ == "__main__":
    main()
