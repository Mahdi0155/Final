import os
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler, CallbackContext
)
from datetime import timedelta
from aiohttp import web

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_USERNAME = '@hottof'
ADMINS = [7827493126, 6387942633, 5459406429, 7189616405]

WAITING_FOR_MEDIA, WAITING_FOR_CAPTION, WAITING_FOR_ACTION, WAITING_FOR_SCHEDULE = range(4)

application = Application.builder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text('شما دسترسی به این ربات ندارید.')
        return ConversationHandler.END
    await update.message.reply_text('سلام! لطفاً یک عکس یا ویدیو فوروارد کن.')
    return WAITING_FOR_MEDIA

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return ConversationHandler.END

    message = update.message
    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = 'photo'
    elif message.video:
        file_id = message.video.file_id
        media_type = 'video'
    else:
        await message.reply_text('فقط عکس یا ویدیو قابل قبول است.')
        return WAITING_FOR_MEDIA

    context.user_data['file_id'] = file_id
    context.user_data['media_type'] = media_type

    await message.reply_text('لطفاً کپشن مورد نظر خود را بنویسید:')
    return WAITING_FOR_CAPTION

async def handle_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = update.message.text
    final_caption = caption + "\n\n@hottof | تُفِ داغ"
    context.user_data['caption'] = final_caption

    keyboard = ReplyKeyboardMarkup(
        [['ارسال در کانال', 'ارسال در آینده'], ['برگشت به ابتدا']],
        resize_keyboard=True
    )

    media_type = context.user_data['media_type']
    file_id = context.user_data['file_id']

    if media_type == 'photo':
        await update.message.reply_photo(file_id, caption=final_caption, reply_markup=keyboard)
    elif media_type == 'video':
        await update.message.reply_video(file_id, caption=final_caption, reply_markup=keyboard)

    return WAITING_FOR_ACTION

async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == 'ارسال در کانال':
        await send_to_channel(context.user_data, context.bot)
        await update.message.reply_text('پیام ارسال شد. لطفاً مدیا بعدی را بفرستید.', reply_markup=ReplyKeyboardRemove())
        return WAITING_FOR_MEDIA
    elif text == 'ارسال در آینده':
        await update.message.reply_text('زمان ارسال (به دقیقه) را وارد کنید:', reply_markup=ReplyKeyboardRemove())
        return WAITING_FOR_SCHEDULE
    elif text == 'برگشت به ابتدا':
        await update.message.reply_text('لغو شد. لطفاً دوباره مدیا بفرستید.', reply_markup=ReplyKeyboardRemove())
        return WAITING_FOR_MEDIA
    else:
        await update.message.reply_text('یکی از گزینه‌ها را انتخاب کنید.')
        return WAITING_FOR_ACTION

async def handle_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        minutes = int(update.message.text)
        context.job_queue.run_once(send_scheduled, when=timedelta(minutes=minutes), data=context.user_data.copy())
        await update.message.reply_text(f'پیام برای {minutes} دقیقه بعد زمان‌بندی شد.', reply_markup=ReplyKeyboardRemove())
        return WAITING_FOR_MEDIA
    except ValueError:
        await update.message.reply_text('فقط عدد وارد کنید.')
        return WAITING_FOR_SCHEDULE

async def send_to_channel(data, bot):
    media_type = data['media_type']
    file_id = data['file_id']
    caption = data['caption']

    if media_type == 'photo':
        await bot.send_photo(chat_id=CHANNEL_USERNAME, photo=file_id, caption=caption)
    elif media_type == 'video':
        await bot.send_video(chat_id=CHANNEL_USERNAME, video=file_id, caption=caption)

async def send_scheduled(context: CallbackContext):
    data = context.job.data
    media_type = data['media_type']
    file_id = data['file_id']
    caption = data['caption']

    bot = context.bot
    if media_type == 'photo':
        await bot.send_photo(chat_id=CHANNEL_USERNAME, photo=file_id, caption=caption)
    elif media_type == 'video':
        await bot.send_video(chat_id=CHANNEL_USERNAME, video=file_id, caption=caption)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('لغو شد.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def ping_handler(request):
    return web.Response(text="I'm alive!")

def main():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            WAITING_FOR_MEDIA: [MessageHandler(filters.PHOTO | filters.VIDEO, handle_media)],
            WAITING_FOR_CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_caption)],
            WAITING_FOR_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_action)],
            WAITING_FOR_SCHEDULE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_schedule)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.web_app.router.add_get("/", ping_handler)

    WEBHOOK_URL = 'https://final-4oxs.onrender.com'

    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        webhook_url=WEBHOOK_URL
    )

if __name__ == '__main__':
    main()
