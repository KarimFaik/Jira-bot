import logging 
from logging.handlers import RotatingFileHandler
import os

log_path = os.path.dirname(os.path.abspath(__file__))
os.makedirs(log_path,exist_ok=True)

log_file_path = os.path.join(log_path, 'bot.log')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = RotatingFileHandler(log_file_path, maxBytes=5000000, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

logger.addHandler(handler)
