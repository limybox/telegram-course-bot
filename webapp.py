"""
FastAPI сервер для Render.com вебхука Telegram.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from aiogram.types import Update

from config import TELEGRAM_BOT_TOKEN
from bot import dp, bot
from storage import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация при запуске."""
    await init_db()
    logger.info("Database initialized")
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """Вебхук для Telegram."""
    try:
        update_data = await request.json()
        update = Update.model_validate(update_data)
        await dp.feed_update(bot, update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"ok": False, "error": str(e)}


@app.get("/")
async def health_check():
    """Проверка здоровья сервера."""
    return {"status": "ok", "message": "Bot is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
