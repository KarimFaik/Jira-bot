import sqlite3
import sys
import os

path_to_logs = os.path.abspath(os.path.join(os.path.dirname(__file__),"logs"))
sys.path.append(path_to_logs)
from logs_ctrl import logger

path_db = os.path.join(os.path.dirname(__file__),"saved_data.sqlite")


def setup_database():
    conn = sqlite3.connect(path_db)
    cur = conn.cursor()

    cur.execute('''
    CREATE TABLE IF NOT EXISTS sent_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT,
        description TEXT,
        phone INTEGER,
        email TEXT,
        company TEXT,
        name TEXT,
        tg_username TEXT,
        attachment INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
    conn.commit()
    conn.close()
    logger.info("Таблица 'sent_data' существует") 


def add_to_database(user_data,update):
    conn = sqlite3.connect(path_db)
    cur = conn.cursor()

    cur.execute('''
    INSERT INTO sent_data (topic, description, phone, email, company, name, tg_username,attachment)
    VALUES (?,?,?,?,?,?,?,?)
''', (
    user_data.get("название задачи", ""),
    user_data.get("описание задачи", ""),
    user_data.get("номер телефона", ""),
    user_data.get("электронная почта", ""),
    user_data.get("название компании и название отдела", ""),
    user_data.get("имя и фамилия", ""),
    update.message.chat.username,
    user_data.get("attachment_flag", "")
))
    conn.commit()
    conn.close()
    logger.info("Данные добавленны в таблицу 'sent_data'")



setup_database()