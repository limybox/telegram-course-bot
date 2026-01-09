"""
Модели данных (простые классы, без SQLAlchemy).
"""

from datetime import datetime


class OrderStatus:
    """Статусы заказов."""
    PENDING = "pending"
    WAITING_PROOF = "waiting_proof"
    WAITING_REVIEW = "waiting_review"
    PAID = "paid"
    CANCELED = "canceled"


class User:
    """Модель пользователя."""
    def __init__(self, id: int, tg_id: int, username: str | None = None):
        self.id = id
        self.tg_id = tg_id
        self.username = username
        self.created_at = datetime.utcnow()
        self.last_seen = datetime.utcnow()


class Order:
    """Модель заказа."""
    def __init__(self, id: int, user_id: int, course_id: int, amount_usdt: float, 
                 currency: str, wallet_address: str, status: str = OrderStatus.PENDING):
        self.id = id
        self.user_id = user_id
        self.course_id = course_id
        self.amount_usdt = amount_usdt
        self.currency = currency
        self.status = status
        self.wallet_address = wallet_address
        self.tx_hash = None
        self.proof_file_id = None
        self.created_at = datetime.utcnow()
        self.paid_at = None


class Access:
    """Модель доступа к курсу."""
    def __init__(self, id: int, user_id: int, course_id: int, volumes_count: int = 2):
        self.id = id
        self.user_id = user_id
        self.course_id = course_id
        self.volumes_count = volumes_count
        self.granted_at = datetime.utcnow()
