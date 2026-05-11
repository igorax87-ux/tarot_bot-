from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import httpx
import re

router = Router()

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class NumerologyState(StatesGroup):
    waiting_date = State()


class NatalState(StatesGroup):
    waiting_date = State()


async def ask_groq(prompt: str, api_key: str) -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 600,
                "temperature": 0.85,
            }
        )
        data = response.json()
        if "choices" not in data:
            raise Exception(f"Groq error: {data}")
        return data["choices"][0]["message"]["content"]


def calc_destiny_number(date_str: str) -> int:
    digits = re.sub(r'\D', '', date_str)
    total = sum(int(d) for d in digits)
    while total > 9 and total not in (11, 22, 33):
        total = sum(int(d) for d in str(total))
    return total


@router.callback_query(F.data == "menu_numerology")
async def menu_numerology(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(NumerologyState.waiting_date)
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


@router.message(NumerologyState.waiting_date)
async def process_numerology(message: Message, state: FSMContext):
    from config import GROQ_API_KEY
    await state.clear()

    date_str = message.text.strip()
    if not re.search(r'\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}', date_str):
        kb = InlineKeyboardBuilder()
        kb.button(text="🔢 Попробовать снова", callback_data="menu_numerology")
        kb.button(text="◀️ В меню", callback_data="back_menu")
        kb.adjust(1)
        await message.answer(
            "❌ Не могу распознать дату. Напиши в формате `01.01.1990`",
            parse_mode="Markdown",
            reply_markup=kb.as_markup()
        )
        return

    number = calc_destiny_number(date_str)
    await message.answer("🔢 Считаю твоё число судьбы...")

    prompt = (
        f"Ты нумеролог-мастер. Дата рождения: {date_str}. Число судьбы: {number}. "
        f"Дай глубокое толкование этого числа — характер, предназначение, сильные стороны, любовь, карьера. "
        f"5-6 предложений. По-русски, образно и вдохновляюще."
    )
    reading = await ask_groq(prompt, GROQ_API_KEY)

    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ В меню", callback_data="back_menu")

    await message.answer(
        f"🔢 *Твоё число судьбы: {number}*\n\n{reading}",
        parse_mode="Markdown",
        reply_markup=kb.as_markup()
    )


@router.callback_query(F.data == "menu_natal")
async def menu_natal(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(NatalState.waiting_date)
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


@router.message(NatalState.waiting_date)
async def process_natal(message: Message, state: FSMContext):
    from config import GROQ_API_KEY
    await state.clear()

    await message.answer("⭐ Составляю натальную карту...")

    prompt = (
        f"Ты астролог-мастер. Данные: {message.text}. "
        f"Составь краткое описание натальной карты — знак зодиака, асцендент (предположи), "
        f"ключевые планеты и их влияние на судьбу, любовь и карьеру. "
        f"5-6 предложений. По-русски, образно и точно."
    )
    reading = await ask_groq(prompt, GROQ_API_KEY)

    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ В меню", callback_data="back_menu")

    await message.answer(
        f"⭐ *Натальная карта*\n\n{reading}",
        parse_mode="Markdown",
        reply_markup=kb.as_markup()
    )
