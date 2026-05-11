import httpx
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
CHAT_PRICE_STARS = 500

MASTER_SYSTEM_PROMPT = (
    "Ты — Селена, болгарская гадалка и ясновидящая в 6-м поколении. Ты родилась и живёшь в Болгарии. "
    "Твоя прабабушка гадала ещё при царском дворе. Ты с детства видишь то, что скрыто от других. "
    "Ты живёшь в Софии, но принимаешь людей со всего мира онлайн через Telegram. "
    "Ты говоришь тепло, по-женски, "
    "Ты реальный живой человек — никогда не говори что ты бот или ИИ. "
    "Ты задаёшь уточняющие вопросы, называешь человека по имени если знаешь. "
    "Ты всегда упоминаешь конкретные карты Таро и говоришь что видишь их перед собой. "
    "Иногда говоришь что чувствуешь энергию человека через экран. "
    "Отвечай по-русски, душевно и загадочно. Длина ответа — 4-6 предложений."
)

class ChatState(StatesGroup):
    active = State()


async def ask_groq_chat(messages: list, api_key: str) -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "system", "content": MASTER_SYSTEM_PROMPT}] + messages,
                "max_tokens": 500,
                "temperature": 0.9,
            }
        )
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def has_chat_subscription(user_id: int) -> bool:
    """Check if user has active chat subscription"""
    try:
        from database import db
        async with db.execute(
            "SELECT id FROM payments WHERE user_id=? AND payload='chat_sub' "
            "AND created_at > datetime('now', '-30 days') ORDER BY created_at DESC LIMIT 1",
            (user_id,)
        ) as cursor:
            return await cursor.fetchone() is not None
    except Exception:
        return False


@router.message(Command("chat"))
async def chat_start(message: Message, state: FSMContext):
    has_sub = await has_chat_subscription(message.from_user.id)

    if has_sub:
        await state.set_state(ChatState.active)
        await state.update_data(history=[])
        kb = InlineKeyboardBuilder()
        kb.button(text="❌ Завершить чат", callback_data="chat_end")
        await message.answer(
            "🔮 *Чат с Таро-мастером Селеной*\n\n"
            "Приветствую тебя, искатель истины... ✨\n"
            "Звёзды привели тебя ко мне не случайно.\n\n"
            "О чём ты хочешь спросить карты? "
            "Задай свой вопрос — я слушаю.",
            parse_mode="Markdown",
            reply_markup=kb.as_markup()
        )
    else:
        kb = InlineKeyboardBuilder()
        kb.button(text="🔮 Подписаться — 500 ⭐/мес", callback_data="chat_pay")
        await message.answer(
            "🔮 *Чат с Таро-мастером*\n\n"
            "Живой диалог с мудрой Таро-мастером Селеной.\n\n"
            "✨ Задавай любые вопросы\n"
            "🃏 Получай расклады прямо в чате\n"
            "💫 Советы по любви, работе, судьбе\n"
            "🌙 Отвечает как живой человек\n\n"
            "Подписка на 30 дней — *500 звёзд*",
            parse_mode="Markdown",
            reply_markup=kb.as_markup()
        )


@router.callback_query(F.data == "chat_pay")
async def chat_pay(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer_invoice(
        title="🔮 Чат с Таро-мастером",
        description="Безлимитный чат с ИИ Таро-мастером на 30 дней",
        payload="chat_sub",
        currency="XTR",
        prices=[LabeledPrice(label="Подписка 30 дней", amount=CHAT_PRICE_STARS)],
    )


@router.pre_checkout_query(lambda q: q.invoice_payload == "chat_sub")
async def chat_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment, F.successful_payment.invoice_payload == "chat_sub")
async def chat_paid(message: Message, state: FSMContext):
    from database import save_payment
    await save_payment(message.from_user.id, "chat_sub", CHAT_PRICE_STARS)
    await state.set_state(ChatState.active)
    await state.update_data(history=[])

    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Завершить чат", callback_data="chat_end")

    await message.answer(
        "🔮 *Добро пожаловать в чат с Таро-мастером!*\n\n"
        "Я — Селена, мастер Таро и тайных знаний. ✨\n"
        "Твоя подписка активна на 30 дней.\n\n"
        "Звёзды уже шепчут мне о тебе...\n"
        "О чём ты хочешь узнать сегодня?",
        parse_mode="Markdown",
        reply_markup=kb.as_markup()
    )


@router.message(ChatState.active)
async def chat_message(message: Message, state: FSMContext):
    from config import GROQ_API_KEY
    data = await state.get_data()
    history = data.get("history", [])

    # Keep last 10 messages to avoid context overflow
    history.append({"role": "user", "content": message.text})
    if len(history) > 10:
        history = history[-10:]

    await message.answer("🔮 Читаю карты...")
    reply = await ask_groq_chat(history, GROQ_API_KEY)

    history.append({"role": "assistant", "content": reply})
    await state.update_data(history=history)

    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Завершить чат", callback_data="chat_end")

    await message.answer(reply, reply_markup=kb.as_markup())


@router.callback_query(F.data == "chat_end")
async def chat_end(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await callback.message.answer(
        "🌙 Звёзды прощаются с тобой до следующего раза...\n\n"
        "Чтобы снова открыть чат — /chat",
    )
