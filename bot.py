import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.client.default import DefaultBotProperties

from config import TELEGRAM_BOT_TOKEN, ADMIN_IDS, COURSES, USDT_TRC20_WALLET, USDT_ERC20_WALLET, BTC_WALLET, ETH_WALLET
from storage import SessionLocal, init_db, get_or_create_user, create_order, get_last_pending_order, grant_access, user_has_access
from models import OrderStatus, Order

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher(storage=MemoryStorage())

class BuyStates(StatesGroup):
    CHOOSING_CURRENCY = State()
    WAITING_PAYMENT = State()
    WAITING_PROOF = State()


def get_main_menu_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🛍️ Купить Эскортопедию", callback_data="buy_course")],
        [InlineKeyboardButton(text="📚 Мои томы", callback_data="my_courses_list")],
        [InlineKeyboardButton(text="📖 О курсе", callback_data="courses_info")],
        [InlineKeyboardButton(text="💬 Поддержка", url="https://t.me/your_support")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_currency_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="USDT TRC20", callback_data="cur_USDT_TRC20"), InlineKeyboardButton(text="USDT ERC20", callback_data="cur_USDT_ERC20")],
        [InlineKeyboardButton(text="BTC", callback_data="cur_BTC"), InlineKeyboardButton(text="ETH", callback_data="cur_ETH")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_order")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_payment_actions_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="💡 Как купить крипту?", callback_data="how_to_buy_crypto")],
        [InlineKeyboardButton(text="✅ Я оплатил(а)", callback_data="i_paid")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_order")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    async with SessionLocal() as session:
        await get_or_create_user(session, message.from_user.id, message.from_user.username)
        await session.commit()

    text = (
        "Привет! 👋\n\n"
        "Добро пожаловать в <b>Эскортопедию</b> — твой полный гайд по сфере!\n\n"
        "Здесь ты найдёшь:\n"
        "• 💡 Эскортопедию (Том 1)\n"
        "• 📈 Эскортопедию (Том 2)\n"
        "<b>Стоимость: 200 USDT за оба тома</b> 💰"
    )
    await state.clear()
    await message.answer(text, reply_markup=get_main_menu_kb())


@dp.callback_query(F.data == "courses_info")
async def courses_info(callback: CallbackQuery):
    course_info = COURSES[1]
    text = f"<b>📖 {course_info['name']}</b>\n\n💵 <b>Цена: {course_info['price']} USDT</b> за оба тома\n\n<b>Содержание:</b>\n\n"
    for idx, volume in enumerate(course_info["volumes"], 1):
        text += f"<b>📕 {volume['title']}</b>\n{volume['description']}\n\n"
    text += "Нажми «Купить Эскортопедию» чтобы начать."
    await callback.message.edit_text(text, reply_markup=get_main_menu_kb())
    await callback.answer()


@dp.callback_query(F.data == "my_courses_list")
async def my_courses_list(callback: CallbackQuery):
    async with SessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        has_access = await user_has_access(session, user, 1)
        await session.commit()

    if not has_access:
        text = "У тебя ещё нет доступа к Эскортопедии. 😔\n\nНажми «Купить Эскортопедию» чтобы получить доступ!"
        await callback.message.edit_text(text, reply_markup=get_main_menu_kb())
        await callback.answer()
        return

    course_info = COURSES[1]
    text = f"<b>✅ У тебя есть доступ!</b>\n\n<b>{course_info['name']}</b>\n\n"
    kb = []
    for idx, volume in enumerate(course_info["volumes"], 1):
        text += f"✅ {volume['title']}\n"
        kb.append([InlineKeyboardButton(text=f"📥 {volume['title']}", callback_data=f"download_volume_{idx}")])
    kb.append([InlineKeyboardButton(text="📚 Оба тома", callback_data="download_all_volumes")])
    kb.append([InlineKeyboardButton(text="← Назад", callback_data="back_to_menu")])
    reply_kb = InlineKeyboardMarkup(inline_keyboard=kb)
    await callback.message.edit_text(text, reply_markup=reply_kb)
    await callback.answer()


@dp.callback_query(F.data.startswith("download_volume_"))
async def download_volume(callback: CallbackQuery):
    volume_idx = int(callback.data.split("_")[-1]) - 1
    course_info = COURSES[1]
    if volume_idx >= len(course_info["volumes"]):
        await callback.answer("Том не найден.", show_alert=True)
        return
    volume = course_info["volumes"][volume_idx]
    try:
        pdf = FSInputFile(volume["pdf_path"])
        await callback.message.answer_document(pdf, caption=f"📕 <b>{volume['title']}</b>")
        await callback.answer("✅ Том отправлен!")
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


@dp.callback_query(F.data == "download_all_volumes")
async def download_all_volumes(callback: CallbackQuery):
    course_info = COURSES[1]
    for volume in course_info["volumes"]:
        try:
            pdf = FSInputFile(volume["pdf_path"])
            await callback.message.answer_document(pdf, caption=f"📕 <b>{volume['title']}</b>")
        except Exception as e:
            await callback.answer(f"❌ Ошибка: {e}", show_alert=True)
            return
    await callback.answer("✅ Оба тома отправлены!")


@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text = "Привет! 👋\n\nДобро пожаловать в <b>Эскортопедию</b>"
    await callback.message.edit_text(text, reply_markup=get_main_menu_kb())
    await callback.answer()


@dp.callback_query(F.data == "buy_course")
async def buy_course(callback: CallbackQuery, state: FSMContext):
    async with SessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        has_access = await user_has_access(session, user, 1)
        await session.commit()
    if has_access:
        await callback.answer("У тебя уже есть доступ ✅", show_alert=True)
        return
    course_info = COURSES[1]
    text = f"<b>🎓 {course_info['name']}</b>\n\n💵 <b>{course_info['price']} USDT</b>\n\nВыбери валюту:"
    await state.update_data(course_id=1)
    await state.set_state(BuyStates.CHOOSING_CURRENCY)
    await callback.message.edit_text(text, reply_markup=get_currency_kb())
    await callback.answer()


@dp.callback_query(BuyStates.CHOOSING_CURRENCY, F.data.startswith("cur_"))
async def choose_currency(callback: CallbackQuery, state: FSMContext):
    currency_code = callback.data.split("_", 1)[1]
    wallet_map = {"USDT_TRC20": USDT_TRC20_WALLET, "USDT_ERC20": USDT_ERC20_WALLET, "BTC": BTC_WALLET, "ETH": ETH_WALLET}
    wallet_address = wallet_map.get(currency_code)
    if not wallet_address:
        await callback.answer("Недоступно", show_alert=True)
        return
    course_info = COURSES[1]
    async with SessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        order = await create_order(session, user, 1, course_info["price"], currency_code, wallet_address)
        await session.commit()
    await state.update_data(order_id=order.id)
    human_name = currency_code.replace("_", " ")
    text = f"<b>💳 Оплата</b>\n\n📊 Сумма: <b>{course_info['price']} USDT</b>\n\n📍 Адрес:\n<code>{wallet_address}</code>\n\n⚠️ Проверь адрес и сеть!"
    await state.set_state(BuyStates.WAITING_PAYMENT)
    await callback.message.edit_text(text, reply_markup=get_payment_actions_kb())
    await callback.answer()


@dp.callback_query(BuyStates.WAITING_PAYMENT, F.data == "how_to_buy_crypto")
async def how_to_buy_crypto(callback: CallbackQuery):
    text = "<b>💡 Как купить USDT</b>\n\n1) Зарегистрируйся на Binance.com\n2) Пополни баланс с карты\n3) Купи USDT\n4) Выбери сеть (TRC20/ERC20)\n5) Отправь на адрес из бота\n\nПосле копируй txid и вернись в бот."
    await callback.answer()
    await callback.message.answer(text)


@dp.callback_query(BuyStates.WAITING_PAYMENT, F.data == "i_paid")
async def i_paid(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BuyStates.WAITING_PROOF)
    text = "Отправь чек / скрин или txid.\n\nПосле проверки получишь оба тома!"
    await callback.message.answer(text)
    await callback.answer()


@dp.message(BuyStates.WAITING_PROOF)
async def receive_proof(message: Message, state: FSMContext):
    async with SessionLocal() as session:
        user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
        order = await get_last_pending_order(session, user)
        if not order:
            await message.answer("Заказ не найден. /start")
            await state.clear()
            return
        proof_file_id = None
        tx_hash = None
        if message.photo:
            proof_file_id = message.photo[-1].file_id
        elif message.document:
            proof_file_id = message.document.file_id
        elif message.text:
            tx_hash = message.text.strip()
        order.status = OrderStatus.WAITING_REVIEW
        if proof_file_id:
            order.proof_file_id = proof_file_id
        if tx_hash:
            order.tx_hash = tx_hash
        await session.commit()
    course_info = COURSES[1]
    for admin_id in ADMIN_IDS:
        text = f"🔔 <b>НОВАЯ ОПЛАТА</b>\n\n📚 {course_info['name']}\n👤 @{message.from_user.username or message.from_user.id}\n💵 {course_info['price']} USDT\n"
        if tx_hash:
            text += f"\n🔗 TXID: <code>{tx_hash}</code>\n"
        text += f"\n✅ /confirm {order.id} {message.from_user.id}"
        await bot.send_message(admin_id, text)
        if proof_file_id:
            await bot.send_photo(admin_id, proof_file_id)
    await state.clear()
    await message.answer("✅ Чек получен! Проверим и отправим томы!")


@dp.callback_query(F.data == "cancel_order")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Отменено.")
    await callback.answer()


@dp.message(Command("confirm"))
async def cmd_confirm(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    parts = message.text.strip().split()
    if len(parts) != 3:
        await message.answer("Формат: /confirm <order_id> <user_id>")
        return
    try:
        order_id = int(parts[1])
        user_tg_id = int(parts[2])
    except ValueError:
        await message.answer("Должны быть числа.")
        return
    async with SessionLocal() as session:
        res = await session.get(Order, order_id)
        if not res:
            await message.answer("❌ Заказ не найден.")
            return
        order = res
        order.status = OrderStatus.PAID
        order.paid_at = datetime.utcnow()
        user = await get_or_create_user(session, user_tg_id, None)
        await grant_access(session, user, 1, volumes_count=2)
        await session.commit()
    course_info = COURSES[1]
    try:
        for volume in course_info["volumes"]:
            pdf = FSInputFile(volume["pdf_path"])
            await bot.send_document(chat_id=user_tg_id, document=pdf, caption=f"📕 <b>{volume['title']}</b>")
        await bot.send_message(chat_id=user_tg_id, text="🎉 <b>Оплата подтверждена!</b>\n\n✅ Том 1\n✅ Том 2\n\nУдачи! 💪")
    except Exception as e:
        await message.answer(f"❌ {e}")
        return
    await message.answer(f"✅ Заказ #{order_id} готов!")


@dp.message(Command("my_books"))
async def my_books_cmd(message: Message):
    async with SessionLocal() as session:
        user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
        has_access = await user_has_access(session, user, 1)
        await session.commit()
    if not has_access:
        await message.answer("❌ Нет доступа. /start")
        return
    course_info = COURSES[1]
    kb = []
    for idx, volume in enumerate(course_info["volumes"], 1):
        kb.append([InlineKeyboardButton(text=f"📥 {volume['title']}", callback_data=f"download_volume_{idx}")])
    kb.append([InlineKeyboardButton(text="📚 Оба", callback_data="download_all_volumes")])
    reply_kb = InlineKeyboardMarkup(inline_keyboard=kb)
    await message.answer("📚 Твои томы:", reply_markup=reply_kb)


async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
