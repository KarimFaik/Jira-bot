import logging
import re
import os
import requests
import pandas as pd

from email_validator import validate_email, EmailNotValidError
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.helpers import escape_markdown
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from telegram.ext.filters import Text

from api import create_issue

'''
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
'''
load_dotenv()
#loads tokens from .env file
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


CSV_FILE = 'list.csv'

TOPIC, DESCRIPTION, PHONE, EMAIL, DEPARTMENT, NAME, CONFIRM, REDACT, SAVE = range(9)



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


def save_data(data):
    df = pd.DataFrame([data])
    ex_df = pd.read_csv(CSV_FILE)
    df = pd.concat([ex_df, df], ignore_index=True)
    df.to_csv(CSV_FILE, index=False, encoding="utf-8")
    print("data_saved")

def validate_phone_number(phone_number):
    pattern = r"^(?:\+7|8)(?:[-.\s]|\s*\(\s*)?\d{3}(?:\s*\)?[-.\s]|\s*\)\s*)?\d{3}(?:[-.\s])?\d{2}(?:[-.\s])?\d{2}$"

    if re.match(pattern,phone_number):
        return True

    else:
        print("Неверный номер телефона")
        return False
    
def validate_email_(email):
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if re.match(pattern,email) and validate_email(email,check_deliverability=True):
        return True
    else:
        print("Неверная почта")
        return False


fields_dictionary = {
    "topic": "название задачи",
    "description": "описание задачи",
    "phone": "номер телефона",
    "email": "электронная почта",
    "department": "название компании и название отдела",
    "name": "имя и фамилия"
}

'''
def unfilled_fields_exist(context:ContextTypes.DEFAULT_TYPE):
    fields = ["topic","description","phone","email","department","name"]
    unfilled_fields = [field for field in fields if context.user_data.get(field,"empty") in ("empty","")]
    return unfilled_fields

def temp(data):
    lines = data.splitlines()
    for line in lines:
        print(line)


def data_not_empty(context:ContextTypes.DEFAULT_TYPE):
    fields = ["topic","description","phone","email","department","name"]
    for i in fields:
        try:
            context.user_data[i]
        except KeyError as e:
            print(e)
'''

class CancelFilter(Text):
    def check_update(self, update):
        if not update.message or not update.message.text:
            return False
        text = update.message.text.strip().lower()
        return text != "отмена задачи"
    
'''
class SkipFilter(Text):
    def check_update(self, update):
        if not update.message or not update.message.text:
            return False
        text = update.message.text.strip().lower()
        return text != "skip"
'''


def is_email_valid(email):
    try :
        validate_email(email,check_deliverability=True)
    except EmailNotValidError as e:
        print(e)
        return False



#Main
#start works on starting bot and entering /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"@{update.message.chat.username} начал бота")
    await context.bot.send_message(chat_id = update.effective_chat.id, text=f"Здарвствуйте, {update.message.chat.first_name}! я создам вам задачу в системе Jira.",reply_markup=start_keys)

#starts on entering /new_task and typing "start new task"
#the cycle of getting data works automatically check conv_handler at the end
async def new_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("new_task")
    await update.message.reply_text(f"Пожалуйста, введите название задачи",reply_markup=skip_keys)
    return TOPIC

#in each get_<> there is skip option that was hardcoded
async def get_topic (update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    if user_input.lower() == "пропустить поле":
        #if user whats to skip bot goes to next stage, skipping this one
        print("пользователь пропустил поле get_topic")
        await update.message.reply_text(f"Пожалуйста, введите описание задачи",reply_markup=skip_keys)
        return DESCRIPTION
    else:
        print("get_topic")
        user_input = update.message.text.strip()
        context.user_data["название задачи"] = user_input
        await update.message.reply_text(f"Пожалуйста, введите описание задачи",reply_markup=skip_keys)
    
    return DESCRIPTION


async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    if "пропустить поле" in user_input.lower():
        print("пользователь пропустил поле get_description ")
        await update.message.reply_text(f"Пожалуйста, введите номер телефона",reply_markup=skip_keys)
        return PHONE
    else: 
        print("get_description")
        user_input = update.message.text.strip()
        context.user_data["описание задачи"] = user_input
        await update.message.reply_text(f"Пожалуйста, введите номер телефона",reply_markup=skip_keys)
    
    return PHONE

#get phone uses regular expresion to only allow correct form of phone number
#if the form entered is not as it is needed user will have to enter it again 
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    if "пропустить поле" in user_input.lower():
        print("пользователь пропустил поле get_phone ")
        await update.message.reply_text(f"Пожалуйста, введите электронную почту",reply_markup=skip_keys)
        return EMAIL
         
    else:  
        print("get_phone")
        user_input = update.message.text.strip()
        if validate_phone_number(user_input):
            context.user_data["номер телефона"] = user_input
            await update.message.reply_text(f"Пожалуйста, введите электронную почту",reply_markup=skip_keys)
            return EMAIL

        else:    
            await update.message.reply_text(
                text="Пожалуйста, введите корректный номер телефона",
                reply_markup=skip_keys
            )
            return PHONE
    

#get email also check corectnesss of email + email_validator library check domain using dns
async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    if "пропустить поле" in user_input.lower():
        print("пользователь пропустил поле get_email ")
        await update.message.reply_text(f"Пожалуйста, введите название компании и название отдела",reply_markup=skip_keys)
        return DEPARTMENT
    else:
        print("get_email")
        user_input = update.message.text.strip()
        if validate_email_(user_input):
            context.user_data["электронная почта"] = user_input
            await update.message.reply_text(f"Пожалуйста, введите название компании и название отдела",reply_markup=skip_keys)
            return DEPARTMENT
        else:
            await update.message.reply_text(f"Неверная почта\Пожалуйста проверите и введите корректный электронную почту")
            return EMAIL

async def get_department(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    if "пропустить поле" in user_input.lower():
        print("пользователь пропустил поле get_department")
        await update.message.reply_text(f"Пожалуйста, введите имя и фамилию",reply_markup=skip_keys)
        return NAME
    else:
        print("get_department")
        user_input = update.message.text.strip()
        context.user_data["название компании и название отдела"] = user_input
        await update.message.reply_text(f"Пожалуйста, введите имя и фамилию",reply_markup=skip_keys)
        return NAME

#Because this code uses conversation handler on entering new stage bot waits for user input
#so requirements for user input are given to user one stage earlier
#so first bot send whats data to enter then goes to that stage and waits for user input
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    if "пропустить поле" in user_input.lower():
        print("пользователь пропустил поле get_name")
        print("data proccessing")
        data_display = "Введенные данные:\n"
        fields = ["название задачи", "описание задачи", "номер телефона", "электронная почта", "название компании и название отдела", "имя и фамилия"]
        for field in fields:
            value = context.user_data.get(field,"пусто")
            data_display += f"{field.capitalize()}: {value}\n"
            
        await update.message.reply_text(data_display)
        await update.message.reply_text("Хотите сохранить данные?", reply_markup=save_keys)
        return CONFIRM
    else:
        print("get_name")
        user_input = update.message.text.strip()
        context.user_data["имя и фамилия"] = user_input
        
        
        
        #prints entered data to user and waits order what to do with that data
        print("data proccessing")
        data_display = "Введенные данные:\n"
        fields = ["название задачи", "описание задачи", "номер телефона", "электронная почта", "название компании и название отдела", "имя и фамилия"]
        for field in fields:
            value = context.user_data.get(field,"пусто")
            data_display += f"{field.capitalize()}: {value}\n"
            
        await update.message.reply_text(data_display)
        await update.message.reply_text("Хотите сохранить данные?", reply_markup=save_keys)
        return CONFIRM


#User needs to confirm saving data before saving
async def confirm_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print('confirm_data')
    user_input = update.message.text.strip().lower()
    if user_input == "да":
        #Validation that all fields are filled and not empty
        fields = ["название задачи", "описание задачи", "номер телефона", "электронная почта", "название компании и название отдела", "имя и фамилия"]
        empty_fields = []
        for field in fields:
            try:
                context.user_data[field]
            except KeyError as e:
                print(e)
                empty_fields.append(e)
                await update.message.reply_text(
                f"Поле {e} не заполнено")
            
        #if there are empty fields, then user have to fill them
        if empty_fields:
            print(f"User didnt fill: {empty_fields}")
            keyboard = [[KeyboardButton("Редактировать данные"),KeyboardButton("Отмена задачи")]]
            reply_markup = ReplyKeyboardMarkup(keyboard,resize_keyboard=True, one_time_keyboard=True)
            await update.message.reply_text(
            f"Некоторые поля не заполнены, пожалуйста заполните их",
            reply_markup=reply_markup)
            return CONFIRM
        # if there isnt empty fields then continue to save
        else:
            print("Saving")
            return SAVE 
            
    elif user_input == "редактировать данные":
        print("user wants to redact data")
        await update.message.reply_text(
            "Пожалуйста, выберите поля для редактирования.",
            reply_markup=redact_keys
        )
        return REDACT  
    else:
        # Invalid input
        await update.message.reply_text(
            text="Пожалуйста выберите 'Да', 'Редактировать данные', или 'Отмена задачи'.",
            reply_markup=save_keys
        )
        return CONFIRM
    

#user redacts fields of choice
async def redact_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    user_input = update.message.text.strip().lower()
    #if there were redacted fields check for not empty and adds redacted fields to user data
    if "redact_field" in context.user_data:
        print('redact: redacted data checking')
        field_to_redact = context.user_data["redact_field"]
        if not user_input:  #input is checked for emptiness
            await update.message.reply_text(
                f"{field_to_redact.capitalize()} не может быть пустым. Пожалуйста введите новое значение.",
                reply_markup=ReplyKeyboardRemove()
            )
            return REDACT 
        
        context.user_data[field_to_redact] = user_input
        print(f"{field_to_redact} updated to: {user_input}")
        del context.user_data["redact_field"]
        # Show updated data
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
    
    print('redact: choosing field')
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
        

#Saving data stage
async def handle_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("handle_save")
    save_data(context.user_data)
    await update.message.reply_text(
        "Data saved!!!",
        reply_markup=ReplyKeyboardRemove()
    )
    #JIRA Create issue
    
    try:#sending saved data to jira
        issue = create_issue(
            project_key= "TEMT",
            summary = context.user_data["название задачи"],
            description = f"описание задачи: {context.user_data["описание задачи"]}\nномер телефона: {context.user_data["номер телефона"]}\nэлектронная почта: {context.user_data["электронная почта"]}\nназвание компании и название отдела: {context.user_data["название компании и название отдела"]}\nимя и фамилия: {context.user_data["имя и фамилия"]}\nTelegram username: @{update.message.chat.username}\nTelegram name: {update.message.chat.first_name, update.message.chat.last_name}",
            issue_type = "Задача"
            )
        #prints issue key to user
        await update.message.reply_text(f"Task successfuly created at Jira\nIssue key: {issue}")
    
    except requests.exceptions.HTTPError as e:
        await context.bot.send_message(chat_id = update.effective_chat.id,text=f"Error creating task at Jira")
    
    #ends conversation cycle
    await update.message.reply_text(
        "What would you like to do next?",
        reply_markup=start_keys
    )
    context.user_data.clear()
    return ConversationHandler.END
    


#just little help
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Commands:\n /new_task: start a new task. ")
    print('help')

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("отмена задачи")
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
        #each stage triggers once have been called
        #all stages have cancel filter so that when user whats to cancel the data will be
        #forgoten and conv handler will be exited
        states={
            TOPIC: [MessageHandler(CancelFilter() & ~filters.COMMAND, get_topic)],
            DESCRIPTION: [MessageHandler(CancelFilter() & ~filters.COMMAND, get_description)],
            PHONE: [MessageHandler(CancelFilter() & ~filters.COMMAND, get_phone)],
            EMAIL: [MessageHandler(CancelFilter() & ~filters.COMMAND, get_email)],
            DEPARTMENT: [MessageHandler(CancelFilter() & ~filters.COMMAND, get_department)],
            NAME: [MessageHandler(CancelFilter() & ~filters.COMMAND, get_name)],
            CONFIRM : [MessageHandler(CancelFilter() & ~filters.COMMAND, confirm_data)],
            SAVE: [MessageHandler(CancelFilter() & ~filters.COMMAND, handle_save)],
            REDACT: [MessageHandler(CancelFilter() & ~filters.COMMAND, redact_data)]
        },
        fallbacks=[CommandHandler("cancel", cancel), MessageHandler(filters.Regex('(?i)^Отмена задачи$'), cancel)]
    )

    #request_phone_handler = CommandHandler("request_phone", request_phone)

    start_handler = CommandHandler("start", start)  
    help_handler = CommandHandler("help", help)
    helpp_handler = MessageHandler(filters.Regex('(?i)^need help$'), help)
    #redact_data_handler = MessageHandler(filters.Regex('(?i)^redact_data$'), redact_data)
    #cancel_handler = MessageHandler(filters.Regex('(?i)^cancel$'), cancel)

    #app.add_handler(request_phone_handler)
    
    app.add_handler(start_handler)
    app.add_handler(help_handler)
    app.add_handler(helpp_handler)
    #app.add_handler(redact_data_handler)
    #app.add_handler(cancel_handler)
    app.add_handler(conv_handler)
    

    app.run_polling()

#bot start
if __name__ == '__main__':
    main()