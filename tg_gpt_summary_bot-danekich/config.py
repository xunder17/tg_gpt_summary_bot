# config.py

import os
from dotenv import load_dotenv
import logging

# Загружаем переменные окружения из .env файла
load_dotenv(r"C:\python\tg_gpt_summary_bot-main\peremennie.env")

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем значения из переменных окружения
try:
    api_id = int(os.environ.get("API_ID"))
except (TypeError, ValueError):
    logger.error("API_ID не задан или не является числом!")
    api_id = None

api_hash = os.environ.get("API_HASH")
bot_token = os.environ.get("BOT_TOKEN")

if not (api_id and api_hash and bot_token):
    logger.error("Проверьте, что все переменные окружения (API_ID, API_HASH, BOT_TOKEN) установлены в файле .env")

