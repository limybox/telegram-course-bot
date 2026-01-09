"""
Асинхронная работа с SQLite БД без SQLAlchemy.
"""

import aiosqlite
from datetime import datetime
from models import OrderStatus

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
            await db.execute(
                "UPDATE users SET last_seen = ? WHERE tg_id = ?",
                (datetime.utcnow().isoformat(), tg_id)
            )
            await db.commit()
            return {"id": row[0], "tg_id": tg_id, "username": username}
        
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
        return {"id": cursor.lastrowid, "user_id": user_id, "status": OrderStatus.PENDING}


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
        row = await cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "user_id": row[1],
                "course_id": row[2],
                "amount_usdt": row[3],
                "currency": row[4],
                "status": row[5],
                "wallet_address": row[6],
                "tx_hash": row[7],
                "proof_file_id": row[8]
            }
        return None


async def grant_access(user_id: int, course_id: int, volumes_count: int = 2) -> bool:
    """Выдать доступ к курсу."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id FROM access WHERE user_id = ? AND course_id = ?",
            (user_id, course_id)
        )
        if await cursor.fetchone():
            return False
        
        await db.execute(
            "INSERT INTO access (user_id, course_id, volumes_count) VALUES (?, ?, ?)",
            (user_id, course_id, volumes_count)
        )
        await db.commit()
        return True


async def user_has_access(user_id: int, course_id: int) -> bool:
    """Проверить, есть ли доступ к курсу."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id FROM access WHERE user_id = ? AND course_id = ?",
            (user_id, course_id)
        )
        return await cursor.fetchone() is not None


async def update_order_status(order_id: int, status: str, tx_hash: str | None = None, proof_file_id: str | None = None):
    """Обновить статус заказа."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE orders SET status = ?, tx_hash = ?, proof_file_id = ?
               WHERE id = ?""",
            (status, tx_hash, proof_file_id, order_id)
        )
        await db.commit()


async def confirm_payment(order_id: int):
    """Подтвердить оплату."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET status = ?, paid_at = ? WHERE id = ?",
            (OrderStatus.PAID, datetime.utcnow().isoformat(), order_id)
        )
        await db.commit()
