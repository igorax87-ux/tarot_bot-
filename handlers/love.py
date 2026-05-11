import random
import httpx
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
LOVE_PRICE_STARS = 250

TAROT_CARDS = [
    "Дурак", "Маг", "Верховная Жрица", "Императрица", "Император",
    "Иерофант", "Влюблённые", "Колесница", "Сила", "Отшельник",
    "Колесо Фортуны", "Справедливость", "Повешенный", "Смерть",
    "Умеренность", "Дьявол", "Башня", "Звезда", "Луна", "Солнце",
    "Суд", "Мир"
]

def draw_cards(n=1):
    cards = []
    for card in random.sample(TAROT_CARDS, n):
        reversed_card = random.choice([True, False])
        cards.append(f"{card}{'(перевёрнутая)' if reversed_card else ''}")
    return cards

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


@router.message(Command("love"))
async def love_start(message: Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="🆓 Одна карта (бесплатно)", callback_data="love_free")
    kb.button(text="💌 Полный расклад — 250 ⭐", callback_data="love_pay")
    kb.adjust(1)
    await message.answer(
        "💌 *Расклад на любовь*\n\n"
        "Карты раскроют тайны твоих отношений:\n"
        "• Что чувствует партнёр?\n"
        "• Куда движутся ваши отношения?\n"
        "• Что мешает любви?\n\n"
        "Выбери вариант 👇",
        parse_mode="Markdown",
        reply_markup=kb.as_markup()
    )


@router.callback_query(F.data == "love_free")
async def love_free(callback: CallbackQuery):
    from config import GROQ_API_KEY
    await callback.answer()
    card = draw_cards(1)[0]
    prompt = (
        f"Ты мистический Таро-мастер. Вытянута карта '{card}' в раскладе на любовь. "
        f"Дай короткое (3-4 предложения) таинственное толкование — что эта карта говорит об отношениях человека. "
        f"В конце добавь интригующий намёк, что полный расклад (3 карты) откроет гораздо больше. "
        f"Пиши по-русски, образно и загадочно."
    )
    await callback.message.answer("🔮 Тяну карту...")
    reading = await ask_groq(prompt, GROQ_API_KEY)

    kb = InlineKeyboardBuilder()
    kb.button(text="💌 Полный расклад — 250 ⭐", callback_data="love_pay")

    await callback.message.answer(
        f"🃏 Твоя карта: *{card}*\n\n{reading}",
        parse_mode="Markdown",
        reply_markup=kb.as_markup()
    )


@router.callback_query(F.data == "love_pay")
async def love_pay(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer_invoice(
        title="💌 Полный расклад на любовь",
        description="3 карты: чувства партнёра, будущее отношений, что мешает любви",
        payload="love_full",
        currency="XTR",
        prices=[LabeledPrice(label="Расклад на любовь", amount=LOVE_PRICE_STARS)],
    )


@router.pre_checkout_query(lambda q: q.invoice_payload == "love_full")
async def love_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment, F.successful_payment.invoice_payload == "love_full")
async def love_paid(message: Message):
    from config import GROQ_API_KEY
    from database import save_payment
    await save_payment(message.from_user.id, "love_full", LOVE_PRICE_STARS)

    cards = draw_cards(3)
    card1, card2, card3 = cards

    prompt = (
        f"Ты опытный Таро-мастер. Сделай полный расклад на любовь из 3 карт:\n"
        f"1. Чувства партнёра: {card1}\n"
        f"2. Будущее отношений: {card2}\n"
        f"3. Что мешает любви: {card3}\n\n"
        f"Для каждой карты дай толкование 3-4 предложения. "
        f"В конце — общий вывод и совет (2-3 предложения). "
        f"Пиши по-русски, таинственно и глубоко, как настоящий мастер Таро."
    )

    await message.answer("💌 Оплата получена! Раскладываю карты...")
    reading = await ask_groq(prompt, GROQ_API_KEY)

    await message.answer(
        f"💌 *Твой расклад на любовь*\n\n"
        f"🃏 Чувства партнёра: *{card1}*\n"
        f"🃏 Будущее отношений: *{card2}*\n"
        f"🃏 Что мешает любви: *{card3}*\n\n"
        f"{reading}",
        parse_mode="Markdown"
    )
