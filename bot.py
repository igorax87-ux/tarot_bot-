import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, BotCommand, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import BOT_TOKEN, ADMIN_ID
from database import init_db, save_user, get_stats
from handlers import love, master_chat

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

dp.include_router(love.router)
dp.include_router(master_chat.router)


def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="💌 Расклад на любовь", callback_data="menu_love")
    kb.button(text="🔮 Чат с Селеной", callback_data="menu_chat")
    kb.button(text="🃏 Карта дня", callback_data="menu_card")
    kb.button(text="🌟 Расклад Таро", callback_data="menu_tarot")
    kb.button(text="🔢 Нумерология", callback_data="menu_numerology")
    kb.button(text="⭐ Натальная карта", callback_data="menu_natal")
    kb.adjust(2, 2, 2)
    return kb.as_markup()


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await save_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.first_name or ""
    )
    await message.answer(
        f"🔮 *Добро пожаловать, {message.from_user.first_name}!*\n\n"
        "Я — твой личный Таро-мастер.\n"
        "Звёзды уже ждут тебя... ✨\n\n"
        "Выбери что тебя интересует 👇",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )


@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    await message.answer(
        "🔮 *Главное меню*\n\nВыбери что тебя интересует 👇",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )


@dp.callback_query(F.data == "menu_love")
async def menu_love(callback: CallbackQuery):
    await callback.answer()
    kb = InlineKeyboardBuilder()
    kb.button(text="🆓 Одна карта (бесплатно)", callback_data="love_free")
    kb.button(text="💌 Полный расклад — 250 ⭐", callback_data="love_pay")
    kb.button(text="◀️ Назад", callback_data="back_menu")
    kb.adjust(1)
    await callback.message.edit_text(
        "💌 *Расклад на любовь*\n\n"
        "Карты раскроют тайны твоих отношений:\n"
        "• Что чувствует партнёр?\n"
        "• Куда движутся ваши отношения?\n"
        "• Что мешает любви?\n\n"
        "Выбери вариант 👇",
        parse_mode="Markdown",
        reply_markup=kb.as_markup()
    )


@dp.callback_query(F.data == "menu_chat")
async def menu_chat(callback: CallbackQuery):
    await callback.answer()
    kb = InlineKeyboardBuilder()
    kb.button(text="🔮 Написать Селене — 500 ⭐/мес", callback_data="chat_pay")
    kb.button(text="◀️ Назад", callback_data="back_menu")
    kb.adjust(1)
    await callback.message.edit_text(
        "🔮 *Селена — живая гадалка из Болгарии*\n\n"
        "🇧🇬 Потомственная ясновидящая в 6-м поколении\n"
        "Принимает онлайн через Telegram\n\n"
        "✨ Задавай любые вопросы лично Селене\n"
        "🃏 Расклад карт прямо в переписке\n"
        "💫 Любовь, деньги, здоровье, судьба\n"
        "🌙 Чувствует твою энергию через экран\n\n"
        "Подписка на 30 дней — *500 звёзд*",
        parse_mode="Markdown",
        reply_markup=kb.as_markup()
    )


@dp.callback_query(F.data == "menu_card")
async def menu_card(callback: CallbackQuery):
    await callback.answer()
    from handlers.love import draw_cards, ask_groq
    from config import GROQ_API_KEY
    from database import check_card_of_day

    already = await check_card_of_day(callback.from_user.id)
    if already:
        kb = InlineKeyboardBuilder()
        kb.button(text="◀️ Назад", callback_data="back_menu")
        await callback.message.edit_text(
            "🃏 Ты уже получила карту дня сегодня!\nВозвращайся завтра ✨",
            reply_markup=kb.as_markup()
        )
        return

    await callback.message.edit_text("🔮 Тяну карту дня...")
    card = draw_cards(1)[0]
    prompt = (
        f"Ты Таро-мастер. Карта дня: '{card}'. "
        f"Дай краткое (3-4 предложения) послание на сегодняшний день. "
        f"Образно, вдохновляюще, по-русски."
    )
    reading = await ask_groq(prompt, GROQ_API_KEY)
    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ В меню", callback_data="back_menu")
    await callback.message.answer(
        f"🃏 *Карта дня: {card}*\n\n{reading}",
        parse_mode="Markdown",
        reply_markup=kb.as_markup()
    )


@dp.callback_query(F.data == "menu_tarot")
async def menu_tarot(callback: CallbackQuery):
    await callback.answer()
    from handlers.love import draw_cards, ask_groq
    from config import GROQ_API_KEY

    await callback.message.edit_text("🌟 Раскладываю карты...")
    cards = draw_cards(3)
    prompt = (
        f"Ты Таро-мастер. Расклад Прошлое-Настоящее-Будущее:\n"
        f"Прошлое: {cards[0]}\nНастоящее: {cards[1]}\nБудущее: {cards[2]}\n"
        f"Для каждой карты 2-3 предложения. Итог 1-2 предложения. По-русски, образно."
    )
    reading = await ask_groq(prompt, GROQ_API_KEY)
    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ В меню", callback_data="back_menu")
    await callback.message.answer(
        f"🌟 *Расклад Таро*\n\n"
        f"⏮ Прошлое: *{cards[0]}*\n"
        f"▶️ Настоящее: *{cards[1]}*\n"
        f"⏭ Будущее: *{cards[2]}*\n\n{reading}",
        parse_mode="Markdown",
        reply_markup=kb.as_markup()
    )


@dp.callback_query(F.data == "menu_numerology")
async def menu_numerology(callback: CallbackQuery):
    await callback.answer()
    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Назад", callback_data="back_menu")
    await callback.message.edit_text(
        "🔢 *Нумерология*\n\n"
        "Напиши свою дату рождения в формате:\n"
        "`01.01.1990`\n\n"
        "И я раскрою твоё число судьбы! ✨",
        parse_mode="Markdown",
        reply_markup=kb.as_markup()
    )


@dp.callback_query(F.data == "menu_natal")
async def menu_natal(callback: CallbackQuery):
    await callback.answer()
    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Назад", callback_data="back_menu")
    await callback.message.edit_text(
        "⭐ *Натальная карта*\n\n"
        "Напиши дату и место рождения:\n"
        "`01.01.1990, Киев`\n\n"
        "Я раскрою твои планеты и знаки! 🌙",
        parse_mode="Markdown",
        reply_markup=kb.as_markup()
    )


@dp.callback_query(F.data == "back_menu")
async def back_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "🔮 *Главное меню*\n\nВыбери что тебя интересует 👇",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )


@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа")
        return
    users, payments, stars = await get_stats()
    await message.answer(
        f"👑 *Статистика бота*\n\n"
        f"👥 Пользователей: {users}\n"
        f"💳 Оплат: {payments}\n"
        f"⭐ Звёзд заработано: {stars}\n"
        f"💰 Примерно: ${stars * 0.01:.2f}",
        parse_mode="Markdown"
    )


async def set_commands():
    await bot.set_my_commands([
        BotCommand(command="start", description="🔮 Главное меню"),
        BotCommand(command="menu", description="📋 Открыть меню"),
        BotCommand(command="chat", description="🔮 Чат с Селеной"),
    ])


async def main():
    await init_db()
    await set_commands()
    print("✅ БОТ ЗАПУЩЕН!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
