import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]

USDT_TRC20_WALLET = os.getenv("USDT_TRC20_WALLET")
USDT_ERC20_WALLET = os.getenv("USDT_ERC20_WALLET")
BTC_WALLET = os.getenv("BTC_WALLET")
ETH_WALLET = os.getenv("ETH_WALLET")

COURSES = {
    1: {
        "name": "Эскортопедия. Полное издание",
        "price": 200,
        "description": "Полный гайд по сфере в двух томах",
        "volumes": [
            {
                "title": "Том 1: Старт",
                "description": "Первое практическое руководство по работе",
                "pdf_path": "data/course1.pdf"
            },
            {
                "title": "Том 2: Продвинутый",
                "description": "Самая полная и подробная инструкция по работе",
                "pdf_path": "data/course2.pdf"
            }
        ]
    }
}

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bot.db")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
META_PIXEL_ID = os.getenv("META_PIXEL_ID", "")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
