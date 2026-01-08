"""
Асинхронная работа с SQLite БД без SQLAlchemy.
"""

import aiosqlite
from datetime import datetime
from models import User, Order, Access, OrderStatus

DB_PATH = "bot.db"


async def init_db():
    """Инициализация БД."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_seen TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                amount_usdt FLOAT NOT NULL,
                currency TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                wallet_address TEXT NOT NULL,
                tx_hash TEXT,
                proof_file_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                paid_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS access (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                volumes_count INTEGER DEFAULT 2,
                granted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, course_id)
            )
        """)
        await db.commit()


async def get_or_create_user(tg_id: int, username: str | None) -> dict:
    """Получить или создать пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
        row = await cursor.fetchone()
        
        if row:
            # Обновляем last_seen
            await db.execute(
                "UPDATE users SET last_seen = ? WHERE tg_id = ?",
                (datetime.utcnow().isoformat(), tg_id)
            )
            await db.commit()
            return {"id": row[0], "tg_id": tg_id, "username": username}
        
        # Создаём нового пользователя
        cursor = await db.execute(
            "INSERT INTO users (tg_id, username) VALUES (?, ?)",
            (tg_id, username)
        )
        await db.commit()
        return {"id": cursor.lastrowid, "tg_id": tg_id, "username": username}


async def create_order(user_id: int, course_id: int, amount_usdt: float, currency: str, wallet_address: str) -> dict:
    """Создать заказ."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO orders (user_id, course_id, amount_usdt, currency, wallet_address, status)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, course_id, amount_usdt, currency, wallet_address, OrderStatus.PENDING)
        )
        await db.commit()
        order_id = cursor.lastrowid
        return {"id": order_id, "user_id": user_id, "status": OrderStatus.PENDING}


async def get_last_pending_order(user_id: int) -> dict | None:
    """Получить последний незавершённый заказ."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """SELECT id, user_id, course_id, amount_usdt, currency, status, wallet_address, tx_hash, proof_file_id
               FROM orders
               WHERE user_id = ? AND status IN (?, ?, ?)
               ORDER BY id DESC
               LIMIT 1""",
            (user_id, OrderStatus.PENDING, OrderStatus.WAITING_PROOF, OrderStatus.WAITING_REVIEW)
        )
        row = await cursor.fetcho
