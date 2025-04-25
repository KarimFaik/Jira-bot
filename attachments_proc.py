import io
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes


MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# Handler for documents and photos
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document:
        file = await update.message.document.get_file()
        file_size = update.message.document.file_size  
        file_name = update.message.document.file_name
    # Check if the message contains a photo
    elif update.message.photo:
        # Get the highest resolution photo (last in the list)
        file = await update.message.photo[-1].get_file()
        file_size = update.message.photo[-1].file_size  
        file_name = f"photo_{update.message.message_id}.jpg"  
    else:
        await update.message.reply_text("Пожалуйста, отправь документ или фото.")
        return MEDIA

    # Check file size
    if file_size > MAX_FILE_SIZE:
        await update.message.reply_text(
            f"Файл слишком большой! Размер: {file_size / 1024 / 1024:.2f} МБ. "
            f"Максимальный размер: 10 МБ."
        )
        return MEDIA

    # Download the file
    file_bytes = await file.downlaod_as_bytearray()
    file_stream = io.BytesIO(file_bytes)
    file_stream.name = file_name

    context.user_data['attacment_stream'] = file_stream
    context.user_data['attacment_name'] = file_name
