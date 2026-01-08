from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from datetime import datetime

from config import DATABASE_URL
from models import Base, User, Order, Access, OrderStatus

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_or_create_user(session: AsyncSession, tg_id: int, username: str | None):
    res = await session.execute(select(User).where(User.tg_id == tg_id))
    user = res.scalar_one_or_none()
    if user:
        user.last_seen = datetime.utcnow()
        return user
    user = User(tg_id=tg_id, username=username)
    session.add(user)
    await session.flush()
    return user


async def create_order(session: AsyncSession, user: User, course_id: int, amount_usdt: float, currency: str, wallet_address: str):
    order = Order(
        user_id=user.id,
        course_id=course_id,
        amount_usdt=amount_usdt,
        currency=currency,
        wallet_address=wallet_address,
        status=OrderStatus.PENDING,
    )
    session.add(order)
    await session.flush()
    return order


async def get_last_pending_order(session: AsyncSession, user: User):
    res = await session.execute(
        select(Order)
        .where(Order.user_id == user.id)
        .where(Order.status.in_([OrderStatus.PENDING, OrderStatus.WAITING_PROOF, OrderStatus.WAITING_REVIEW]))
        .order_by(Order.id.desc())
    )
    return res.scalar_one_or_none()


async def grant_access(session: AsyncSession, user: User, course_id: int, volumes_count: int = 2):
    res = await session.execute(
        select(Access).where(Access.user_id == user.id).where(Access.course_id == course_id)
    )
    if res.scalar_one_or_none():
        return None
    access = Access(user_id=user.id, course_id=course_id, volumes_count=volumes_count)
    session.add(access)
    await session.flush()
    return access


async def user_has_access(session: AsyncSession, user: User, course_id: int) -> bool:
    res = await session.execute(
        select(Access).where(Access.user_id == user.id).where(Access.course_id == course_id)
    )
    return res.scalar_one_or_none() is not None
