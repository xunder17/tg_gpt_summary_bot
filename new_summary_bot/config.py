import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "123456"))
API_HASH = os.getenv("API_HASH", "")
# BOT_TOKEN (для основного бота Aiogram)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

PAYMENT_PROVIDER_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN", "")
STANDARD_PRICE = int(os.getenv("STANDARD_PRICE", "450"))
PRO_PRICE = int(os.getenv("PRO_PRICE", "950"))

DB_URL = "sqlite+aiosqlite:///database.db"
