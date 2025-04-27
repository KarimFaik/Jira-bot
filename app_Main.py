import re
import os
import sys
import io

from email_validator import validate_email, EmailNotValidError
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from telegram.ext.filters import Text

#path to db 
path_to_db = os.path.abspath(os.path.join(os.path.dirname(__file__),"sqlite"))
sys.path.append(path_to_db)
#path to log
path_to_logs = os.path.abspath(os.path.join(os.path.dirname(__file__),"logs"))
sys.path.append(path_to_logs)

from api import create_issue, upload_attachment
from db import setup_database, add_to_database
from logs_ctrl import logger


load_dotenv()
#loads tokens from .env file
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


TOPIC, DESCRIPTION, PHONE, EMAIL, DEPARTMENT, NAME, CONFIRM, REDACT, SAVE, MEDIA, DECISION = range(11)


#Test
'''
async def request_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact_keyboard = KeyboardButton(text="send_contact", request_contact=True)
    custom_keyboard = [[contact_keyboard]]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard,one_time_keyboard=True,resize_keyboard=True)
    await context.bot.send_message(chat_id = update.effective_chat.id, text="Gimme ur phone", reply_markup = reply_markup)
'''


#Functions and class
skip_keys = ReplyKeyboardMarkup([[KeyboardButton('Пропустить поле'), KeyboardButton('Отмена задачи')]],resize_keyboard=True, one_time_keyboard=True)

start_keys = ReplyKeyboardMarkup([[KeyboardButton('Начать новую задачу'), KeyboardButton('Помощь')]],resize_keyboard=True, one_time_keyboard=True)

redact_keys = ReplyKeyboardMarkup([[KeyboardButton('Редактировать название задачи'), KeyboardButton('Редактировать описание задачи')],
                [KeyboardButton('Редактировать номер телефона'), KeyboardButton('Редактировать электронную почту')],
                [KeyboardButton('Редактировать название компании и название отдела'), KeyboardButton('Редактировать имя и фамилию')],
                [KeyboardButton('Отмена задачи')]], resize_keyboard=True, one_time_keyboard=True)

save_keys = ReplyKeyboardMarkup([[KeyboardButton("Да"), KeyboardButton("Редактировать данные"), KeyboardButton("Отмена задачи")]], resize_keyboard=True, one_time_keyboard=True)
 

#using regular expression to accept only russian phones
def validate_phone_number(phone_number,update):
    pattern = r"^(?:\+7|8)(?:[-.\s]|\s*\(\s*)?\d{3}(?:\s*\)?[-.\s]|\s*\)\s*)?\d{3}(?:[-.\s])?\d{2}(?:[-.\s])?\d{2}$"

    if re.match(pattern,phone_number):
        return True

    else:
        logger.info(f"Пользователь {update.message.chat.username} ввел некорректный номер: {update.message.text}")
        return False
#using regular expression to accept only valid email address
#email_validator lib checks domain using dns
def validate_email_(email,update):
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if re.match(pattern,email) and validate_email(email,check_deliverability=True):
        return True
    else:
        logger.info(f"Пользователь {update.message.chat.username} ввел некорректную почту: {update.message.text}")
        return False


fields_dictionary = {
    "topic": "название задачи",
    "description": "описание задачи",
    "phone": "номер телефона",
    "email": "электронная почта",
    "department": "название компании и название отдела",
    "name": "имя и фамилия"
}


class CancelFilter(Text):
    def check_update(self, update):
        if not update.message or not update.message.text:
            return False
        text = update.message.text.strip().lower()
        return text != "отмена задачи"
    



#Main code
#start works on starting bot and entering /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Пользователь %s начал бота",update.message.from_user)
    await context.bot.send_message(chat_id = update.effective_chat.id, text=f"Здравствуйте, {update.message.chat.first_name}! Я создам вам задачу в системе Jira.",reply_markup=start_keys)

#starts on entering /new_task and typing "start new task"
#the cycle of getting data works automatically check conv_handler at the end
async def new_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Пользователь %s начал новую задачу",update.message.from_user)
    await update.message.reply_text(f"Пожалуйста, введите название задачи\nПример: Миграция серверов",reply_markup=skip_keys)
    return TOPIC

#in each get_<> there is skip option that was hardcoded
async def get_topic (update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    if user_input.lower() == "пропустить поле":
        #if user whats to skip bot goes to next state, skipping this one
        logger.info(f"Пользователь {update.message.chat.username} пропустил ввод название задачи")
        await update.message.reply_text(f"Пожалуйста, введите описание задачи\nПример: Миграция серверов с помощью Ansible",reply_markup=skip_keys)
        return DESCRIPTION
        
        
        #because this bot uses conversation handler, he prints to user what info to enter one 
        #state earlier then that info will be saved.
        #each new state firslty wait for user input then continues to what is coded
    else:
        logger.info(f"Пользователь {update.message.chat.username} ввел название задачи: {update.message.text}")
        user_input = update.message.text.strip()
        context.user_data["название задачи"] = user_input
        await update.message.reply_text(f"Пожалуйста, введите описание задачи\nПример: Миграция серверов с помощью Ansible",reply_markup=skip_keys)
    
    return DESCRIPTION


async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    if "пропустить поле" in user_input.lower():
        logger.info(f"Пользователь {update.message.chat.username} пропустил ввод описание задачи")
        await update.message.reply_text(f"Пожалуйста, введите номер телефона\nПример: 81234567890",reply_markup=skip_keys)
        return PHONE
    else: 
        logger.info(f"Пользователь {update.message.chat.username} ввел описание задачи: {update.message.text}")
        user_input = update.message.text.strip()
        context.user_data["описание задачи"] = user_input
        await update.message.reply_text(f"Пожалуйста, введите номер телефона\nПример: 81234567890",reply_markup=skip_keys)
    
    return PHONE

#get phone uses regular expresion to only allow correct form of phone number
#if the form entered is not as it is needed user will have to enter it again 
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    if "пропустить поле" in user_input.lower():
        logger.info(f"Пользователь {update.message.chat.username} пропустил ввод  номера телефона")
        await update.message.reply_text(f"Пожалуйста, введите электронную почту\nПример: ivan_01@mail.ru",reply_markup=skip_keys)
        return EMAIL
         
    else:  
        logger.info(f"Пользователь {update.message.chat.username} ввел номер телефона: {update.message.text}")
        user_input = update.message.text.strip()
        if validate_phone_number(user_input,update):
            context.user_data["номер телефона"] = user_input
            await update.message.reply_text(f"Пожалуйста, введите электронную почту\nПример: ivan_01@mail.ru",reply_markup=skip_keys)
            return EMAIL

        else:    
            await update.message.reply_text(
                text="Некорректный номер телефона!\nПожалуйста, введите корректный номер телефонаn\nПример: 81234567890 ",
                reply_markup=skip_keys
            )
            return PHONE
    

#get email also check corectnesss of email + email_validator library check domain using dns
async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    if "пропустить поле" in user_input.lower():
        logger.info(f"Пользователь {update.message.chat.username} пропустил ввод электронной почты")
        await update.message.reply_text(f"Пожалуйста, введите название компании и название отдела\nПример: ООО Орешки, отдел IT",reply_markup=skip_keys)
        return DEPARTMENT
    else:
        logger.info(f"Пользователь {update.message.chat.username} ввел электронную почту: {update.message.text}")
        user_input = update.message.text.strip()
        if validate_email_(user_input,update):
            context.user_data["электронная почта"] = user_input
            await update.message.reply_text(f"Пожалуйста, введите название компании и название отдела\nПример: ООО Орешки, отдел IT",reply_markup=skip_keys)
            return DEPARTMENT
        else:
            await update.message.reply_text(f"Некорректная почта!\nПожалуйста проверите и введите корректную электронную почту\nПример: ivan_01@mail.ru")
            return EMAIL

async def get_department(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    if "пропустить поле" in user_input.lower():
        logger.info(f"Пользователь {update.message.chat.username} пропустил ввод название компании и название отдела")
        await update.message.reply_text(f"Пожалуйста, введите имя и фамилию\nПример: Иван Иванов",reply_markup=skip_keys)
        return NAME
    else:
        logger.info(f"Пользователь {update.message.chat.username} ввел название компании и название отдела: {update.message.text}")
        user_input = update.message.text.strip()
        context.user_data["название компании и название отдела"] = user_input
        await update.message.reply_text(f"Пожалуйста, введите имя и фамилию\nПример: Иван Иванов",reply_markup=skip_keys)
        return NAME

#Because this code uses conversation handler on entering new state bot waits for user input
#so requirements for user input are given to user one state earlier
#so first bot send whats data to enter then goes to that state and waits for user input
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    if "пропустить поле" in user_input.lower():
        logger.info(f"Пользователь {update.message.chat.username} пропустил ввод имени и фамилии")

        context.user_data['attachment_flag'] = 0
        keyboard = [[KeyboardButton("Да"),KeyboardButton("Нет")]]
        reply_markup = ReplyKeyboardMarkup(keyboard,resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("Хотите прикрепить вложение к заданию?",reply_markup=reply_markup)
        return DECISION
    else:
        logger.info(f"Пользователь {update.message.chat.username} ввел имя и фамилию: {update.message.text}")
        user_input = update.message.text.strip()
        context.user_data["имя и фамилия"] = user_input
        

        context.user_data['attachment_flag'] = 0
        keyboard = [[KeyboardButton("Да"),KeyboardButton("Нет")]]
        reply_markup = ReplyKeyboardMarkup(keyboard,resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("Хотите прикрепить вложение к заданию?",reply_markup=reply_markup)
        return DECISION
        
#Asking if user wanna attach document or photo
async def decision_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Пользователь {update.message.chat.username} перешел в промежуточный этап выбора")
    user_input = update.message.text.strip().lower()
    if user_input == "да":
        await update.message.reply_text("Отправьте фото или документ размером не больше 10МБ",reply_markup=ReplyKeyboardRemove())
        return MEDIA
    
    elif user_input == "нет":
        #prints entered data to user and waits order what to do with that data
        logger.info(f"Вывод данных для пользователя {update.message.chat.username}")
        data_display = "Введенные данные:\n"
        fields = ["название задачи", "описание задачи", "номер телефона", "электронная почта", "название компании и название отдела", "имя и фамилия"]
        for field in fields:
            value = context.user_data.get(field,"пусто")
            data_display += f"{field.capitalize()}: {value}\n"
            
        await update.message.reply_text(data_display)
        await update.message.reply_text("Хотите сохранить данные?", reply_markup=save_keys)
        return CONFIRM
    else:
        logger.info(f"Пользователь {update.message.chat.username} ввел не подходящий ответ")
        await update.message.reply_text("Пожалуйста выберите 'Да' или 'Нет'.")
        return DECISION


# Handler for attachments
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Пользователь {update.message.chat.username} перешел в этап добавления вложения")
    if update.message.document:
        logger.info(f"Пользователь {update.message.chat.username} приклепил документ к задаче")
        file = await update.message.document.get_file()
        file_size = update.message.document.file_size  
        file_name = update.message.document.file_name
    # Check if the message contains a photo
    elif update.message.photo:
        logger.info(f"Пользователь {update.message.chat.username} приклепил фото к задаче")
        # Get the highest resolution photo
        file = await update.message.photo[-1].get_file()
        file_size = update.message.photo[-1].file_size  
        file_name = f"photo_{update.message.message_id}.jpg"  
    else:
        logger.info(f"Пользователь {update.message.chat.username} отправил текст вместо файла")
        await update.message.reply_text("Пожалуйста, отправь документ или фото.")
        return MEDIA

    # Check file size
    if file_size > MAX_FILE_SIZE:
        logger.info(f"Пользователь {update.message.chat.username} приклепил файл размером больше 10МБ")
        await update.message.reply_text(
            f"Файл слишком большой! Размер: {file_size / 1024 / 1024:.2f} МБ.\n"
            f"Максимальный размер: 10 МБ."
        )
        return MEDIA
    try:
        # Download the file
        file_bytes = await file.download_as_bytearray()
        file_stream = io.BytesIO(file_bytes)
        file_stream.name = file_name

        context.user_data['attachment_stream'] = file_stream
        context.user_data['attachment_name'] = file_name
        context.user_data['attachment_flag'] = 1
        
        logger.info(f"Файл от успешно получен от пользователя {update.message.chat.username}")
        await update.message.reply_text(f"Файл получен! Размер: {file_size / 1024 / 1024:.2f} МБ. ")
        
        logger.info(f"Вывод данных для пользователя {update.message.chat.username}")
        data_display = "Введенные данные:\n"
        fields = ["название задачи", "описание задачи", "номер телефона", "электронная почта", "название компании и название отдела", "имя и фамилия"]
        for field in fields:
            value = context.user_data.get(field,"пусто")
            data_display += f"{field.capitalize()}: {value}\n"
            
        await update.message.reply_text(data_display)
        await update.message.reply_text("Хотите сохранить данные?", reply_markup=save_keys)
        return CONFIRM
    

    except Exception as e:
        await update.message.reply_text(f"Ошибка при загрузке файла {e}")
        logger.error(f"Ошибка при получении файла {e} от пользователя {update.message.chat.username}")
        return MEDIA


#User needs to confirm saving data before saving
async def confirm_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Пользователь {update.message.chat.username} перешел в этап подтверждения данных")
    user_input = update.message.text.strip().lower()
    if user_input == "да":
        #Validation that all fields are filled and not empty
        fields = ["название задачи", "описание задачи", "номер телефона", "электронная почта", "название компании и название отдела", "имя и фамилия"]
        empty_fields = []
        for field in fields:
            try:
                context.user_data[field]
            except KeyError as e:
                logger.info(f"Пользователь {update.message.chat.username} не заполнил поле: {e}")
                empty_fields.append(e)
                await update.message.reply_text(
                f"Поле {e} не заполнено")
            
        #if there are empty fields, then user have to fill them
        if empty_fields:
            #print(f"User didnt fill: {empty_fields}")
            keyboard = [[KeyboardButton("Редактировать данные"),KeyboardButton("Отмена задачи")]]
            reply_markup = ReplyKeyboardMarkup(keyboard,resize_keyboard=True, one_time_keyboard=True)
            await update.message.reply_text(
            f"Перед отправкой надо заполнить все поля, пожалуйста заполните пустые поля",
            reply_markup=reply_markup)
            return CONFIRM
        # if there isnt empty fields then continue to save
        else:
            logger.info(f"Пользователя {update.message.chat.username} хочет сохранить данные")
            keyboard = [[KeyboardButton("Да!"),KeyboardButton("Отмена задачи")]]
            reply_markup = ReplyKeyboardMarkup(keyboard,resize_keyboard=True, one_time_keyboard=True)
            await update.message.reply_text("Создать задачю в Jira?",reply_markup=reply_markup)
            return SAVE 
            
    elif user_input == "редактировать данные":
        logger.info(f"Пользователь {update.message.chat.username} хочет редактировать данные")
        await update.message.reply_text(
            "Пожалуйста, выберите поля для редактирования.",
            reply_markup=redact_keys
        )
        return REDACT  
    else:
        # Invalid input
        logger.info(f"Пользователь {update.message.chat.username} ввел не подходящий ответ")
        await update.message.reply_text(
            "Пожалуйста выберите 'Да', 'Редактировать данные', или 'Отмена задачи'.",
            reply_markup=save_keys
        )
        return CONFIRM
    

#user redacts fields of choice
async def redact_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Пользователь {update.message.chat.username} перешел в этап редактирования данных")
    user_input = update.message.text.strip().lower()
    #if there were redacted fields check for not empty and adds redacted fields to user data
    if "redact_field" in context.user_data:
        logger.info(f"Проверка отредактированных данных от пользователя {update.message.chat.username}")
        field_to_redact = context.user_data["redact_field"]
        if not user_input:  #input is checked for emptiness
            await update.message.reply_text(
                f"{field_to_redact.capitalize()} не может быть пустым. Пожалуйста введите новое значение.",
                reply_markup=ReplyKeyboardRemove()
            )
            return REDACT 
        
        context.user_data[field_to_redact] = user_input
        logger.info(f"Пользователь {update.message.chat.username} отредактировал поле {field_to_redact}  на : {user_input}")
        del context.user_data["redact_field"]
        # Show updated data
        logger.info(f"Вывод отредактированных данных для пользователя {update.message.chat.username}")
        data_display = "Обновленные данные:\n"
        fields = ["название задачи", "описание задачи", "номер телефона", "электронная почта", "название компании и название отдела", "имя и фамилия"]
        for field in fields:
            value = context.user_data.get(field, "не предоставлено")
            data_display += f"{field.capitalize()}: {value}\n"

        await update.message.reply_text(data_display)
        await update.message.reply_text(
            text="Хотите сохранить обновленные данные?",
            reply_markup=save_keys
        )
        return CONFIRM 
    
    # choosing field to redact
    if user_input == "редактировать название задачи":
        context.user_data["redact_field"] = "название задачи"
        await update.message.reply_text(
            "Пожалуйста, введите новое название задачи:",
            reply_markup=ReplyKeyboardRemove()
        )
        return REDACT
    elif user_input == "редактировать описание задачи":
        context.user_data["redact_field"] = "описание задачи"
        await update.message.reply_text(
            "Пожалуйста, введите новое описание задачи:",
            reply_markup=ReplyKeyboardRemove()
        )
        return REDACT
    elif user_input == "редактировать номер телефона":
        context.user_data["redact_field"] = "номер телефона"
        await update.message.reply_text(
            "Пожалуйста, введите новый номер телефона:",
            reply_markup=ReplyKeyboardRemove()
        )
        return REDACT
    elif user_input == "редактировать электронную почту":
        context.user_data["redact_field"] = "электронная почта"
        await update.message.reply_text(
            "Пожалуйста, введите новую электронную почту:",
            reply_markup=ReplyKeyboardRemove()
        )
        return REDACT
    elif user_input == "редактировать название компании и название отдела":
        context.user_data["redact_field"] = "название компании и название отдела"
        await update.message.reply_text(
            "Пожалуйста, введите новое название компании и название отдела:",
            reply_markup=ReplyKeyboardRemove()
        )
        return REDACT
    elif user_input == "редактировать имя и фамилию":
        context.user_data["redact_field"] = "имя и фамилия"
        await update.message.reply_text(
            "Пожалуйста, введите новое имя и фамилию:",
            reply_markup=ReplyKeyboardRemove()
        )
        return REDACT
    else:
        await update.message.reply_text(
            "Пожалуйста, выбирите поле для редактирования.",
            reply_markup=redact_keys
        )
        return REDACT  
        

#Saving data 
async def handle_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Пользователь {update.message.chat.username} перешел в этап сохранения и отправки данных")
    setup_database()
    #JIRA Create issue
    #sending saved data to jira
    issue_key, error_msg  = create_issue(
        project_key= "TEMT",
        summary = context.user_data["название задачи"],
        description = f"описание задачи: {context.user_data["описание задачи"]}\nномер телефона: {context.user_data["номер телефона"]}\nэлектронная почта: {context.user_data["электронная почта"]}\nназвание компании и название отдела: {context.user_data["название компании и название отдела"]}\nимя и фамилия: {context.user_data["имя и фамилия"]}\nTelegram username: @{update.message.chat.username}\nTelegram имя: {update.message.chat.first_name, update.message.chat.last_name}"
        )
    if issue_key is not None:
        #prints issue key to user
        logger.info(f"Пользователь {update.message.chat.username} узпешно создал задачу ({issue_key}) в Jira")
        await update.message.reply_text(f"Задача создана успешно\nIssue key: {issue_key}")
        add_to_database(context.user_data, update)
        #if attachment was added sends it to created issue
        if context.user_data.get('attachment_flag') == 1:
            file_stream = context.user_data['attachment_stream']
            file_name = context.user_data['attachment_name']
            attachment_error = upload_attachment(issue_key, file_stream, file_name)
            if attachment_error:
                logger.error(f"Не удалось прикрепить файл {file_name} к задаче {issue_key} для пользователя {update.message.chat.username}")
                await update.message.reply_text(f"Не удалось прикрепить файл:\n{attachment_error}")
            file_stream.close()#close the stream to free memory

    #if error, prints error to user
    else:
        logger.error(f"Не удалось создать задачу {issue_key} для пользователя {update.message.chat.username}")
        logger.error(error_msg)
        await update.message.reply_text(f"Возникла ошибка при создание задачи в Jira: \n'{error_msg}'") 
        await update.message.reply_text(f"Пожалуйста попробуйте еще раз позже")
    
    #ends conversation cycle
    await update.message.reply_text(
        "Что будем делать дальше?",
        reply_markup=start_keys
    )
    context.user_data.clear()
    return ConversationHandler.END
    


#just little help
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Commands:\n /new_task: start a new task. ")
    logger.info(f"Пользователь {update.message.chat.username} воспользовался командой 'помощь'")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Пользователь {update.message.chat.username} отменил создание задачи")
    context.user_data.clear()
    await update.message.reply_text("Задача отменена",reply_markup=start_keys)
    return ConversationHandler.END




#bot init
def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    #THE conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("new_task", new_task),
                      MessageHandler(filters.Regex('(?i)^начать новую задачу$'), new_task)],
        #each state triggers once have been called
        #all states have cancel filter so that when user whats to cancel the data will be
        #forgoten and conv handler will be exited
        #order of states in conv_handler doesnt matter
        states={
            TOPIC: [MessageHandler(CancelFilter() & ~filters.COMMAND, get_topic)],
            DESCRIPTION: [MessageHandler(CancelFilter() & ~filters.COMMAND, get_description)],
            PHONE: [MessageHandler(CancelFilter() & ~filters.COMMAND, get_phone)],
            EMAIL: [MessageHandler(CancelFilter() & ~filters.COMMAND, get_email)],
            DEPARTMENT: [MessageHandler(CancelFilter() & ~filters.COMMAND, get_department)],
            NAME: [MessageHandler(CancelFilter() & ~filters.COMMAND, get_name)],
            CONFIRM : [MessageHandler(CancelFilter() & ~filters.COMMAND, confirm_data)],
            SAVE: [MessageHandler(CancelFilter() & ~filters.COMMAND, handle_save)],
            REDACT: [MessageHandler(CancelFilter() & ~filters.COMMAND, redact_data)],
            MEDIA: [MessageHandler(filters.Document.ALL | filters.PHOTO, handle_media)],
            DECISION: [MessageHandler(CancelFilter() & ~filters.COMMAND, decision_handler)]
        },
        fallbacks=[CommandHandler("cancel", cancel), MessageHandler(filters.Regex('(?i)^Отмена задачи$'), cancel)]
    )

    #request_phone_handler = CommandHandler("request_phone", request_phone)

    start_handler = CommandHandler("start", start)  
    help_handler = MessageHandler(filters.Regex('(?i)^помощь$'), help)
    #redact_data_handler = MessageHandler(filters.Regex('(?i)^redact_data$'), redact_data)
    #cancel_handler = MessageHandler(filters.Regex('(?i)^cancel$'), cancel)

    #app.add_handler(request_phone_handler)
    
    app.add_handler(start_handler)
    app.add_handler(help_handler)
    #app.add_handler(redact_data_handler)
    #app.add_handler(cancel_handler)
    app.add_handler(conv_handler)
    

    app.run_polling()

#bot start
if __name__ == '__main__':
    main()