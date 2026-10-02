import os
import logging
from maxapi import Bot, Dispatcher, F
from maxapi.filters.command import CommandStart
from maxapi.types import MessageCreated, MessageCallback, CallbackButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.enums.update import UpdateType
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_BOT_TOKEN = os.getenv("MAX_BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "svarmaster-secret-2025")
ADMIN_ID = os.getenv("ADMIN_ID", "")

if not MAX_BOT_TOKEN:
    raise RuntimeError("MAX_BOT_TOKEN не задан!")

bot = Bot(MAX_BOT_TOKEN)
dp = Dispatcher()
user_states = {}
seen_users = set()

ALL_PAYLOADS = {
    "services", "prices", "terms", "contact", "calc",
    "show_wa", "show_tg", "show_max", "show_call", "back_to_menu",
    "calc_vorota", "calc_naves", "calc_lestnica", "calc_ograzhdenie",
    "calc_pokraska", "calc_mangal",
}

def get_real_user_id(event):
    if hasattr(event, "callback") and event.callback is not None:
        u = getattr(event.callback, "user", None)
        if u and getattr(u, "user_id", None):
            logger.info(f"USER_ID from callback.user = {u.user_id}")
            return u.user_id
    r = getattr(event.message, "recipient", None)
    if r and getattr(r, "user_id", None):
        logger.info(f"USER_ID from recipient = {r.user_id}")
        return r.user_id
    s = getattr(event.message, "sender", None)
    if s and getattr(s, "user_id", None):
        logger.info(f"USER_ID from sender = {s.user_id}")
        return s.user_id
    logger.warning("user_id НЕ найден")
    return None

async def notify_admin(text):
    if not ADMIN_ID:
        return
    try:
        await bot.send_message(chat_id=int(ADMIN_ID), text=text)
    except Exception as e:
        logger.error(f"notify_admin error: {e}")

TEXT_MENU = "Здравствуйте! Я бот сварочной мастерской СварМастер.\nЧем могу помочь?\n\nВыберите пункт меню ниже:"
TEXT_SERVICES = "🔧 *Наши услуги:*\n\n• Сварочные работы\n• Ворота и калитки\n• Навесы и козырьки\n• Лестницы и перила\n• Порошковая покраска\n• Мебель из металла\n• Ограждения и заборы\n• Изготовление на заказ"
TEXT_PRICES = "💰 *Цены:*\n\n• Сварочные работы — от 1500 ₽/час\n• Ворота — от 4500 ₽/м²\n• Навесы — от 3800 ₽/м²\n• Лестницы — от 2200 ₽/ступень\n• Порошковая покраска — от 1200 ₽/м²\n\nТочная стоимость — после замера."
TEXT_TERMS = "⏱ *Сроки:*\n\n• Стандартный — 5–10 рабочих дней\n• Срочный — от 2 дней (наценка 30%)"
TEXT_CONTACT = "📞 *Связаться с оператором:*"
TEXT_WA = "💬 WhatsApp: https://wa.me/79159190508"
TEXT_TG = "✈️ Telegram: https://t.me/SKYHITORED"
TEXT_MAX = "📱 MAX: https://max.ru/u/f9LHodD0cOLt4DlpXkQuKcUA-rwanDwWOPRvmBInmJ1e_HlzRa6DjU1K1gU"
TEXT_CALL = "📱 Позвонить: +7 (915) 919-05-08"
TEXT_CALC_INTRO = "🧮 *Калькулятор стоимости*\n\nВыберите услугу:"
TEXT_FALLBACK = "Пожалуйста, воспользуйтесь кнопками меню ниже 👇"

CALC_SERVICES = {
    "calc_vorota":      {"name": "Откатные ворота",    "unit": "м²",       "price": 4500, "question": "Введите площадь ворот в м².\nНапример: 4.5"},
    "calc_naves":       {"name": "Навес",               "unit": "м²",       "price": 3800, "question": "Введите площадь навеса в м².\nНапример: 20"},
    "calc_lestnica":    {"name": "Лестница",            "unit": "ступеней", "price": 2200, "question": "Введите количество ступеней.\nНапример: 10"},
    "calc_ograzhdenie": {"name": "Ограждение / перила", "unit": "пог. м",   "price": 1800, "question": "Введите длину в метрах.\nНапример: 15"},
    "calc_pokraska":    {"name": "Порошковая покраска", "unit": "м²",       "price": 1200, "question": "Введите площадь покраски в м².\nНапример: 8"},
    "calc_mangal":      {"name": "Мангал / барбекю",    "unit": "шт.",      "price": 8000, "question": None},
}

def main_menu_kb():
    b = InlineKeyboardBuilder()
    b.row(CallbackButton(text="🔧 Услуги", payload="services"), CallbackButton(text="💰 Цены", payload="prices"))
    b.row(CallbackButton(text="🧮 Калькулятор", payload="calc"))
    b.row(CallbackButton(text="⏱ Сроки", payload="terms"), CallbackButton(text="📞 Оператор", payload="contact"))
    return b.as_markup()

def contact_kb():
    b = InlineKeyboardBuilder()
    b.row(CallbackButton(text="💬 WhatsApp", payload="show_wa"))
    b.row(CallbackButton(text="✈️ Telegram", payload="show_tg"))
    b.row(CallbackButton(text="📱 MAX Messenger", payload="show_max"))
    b.row(CallbackButton(text="📞 Позвонить", payload="show_call"))
    b.row(CallbackButton(text="⬅ Назад", payload="back_to_menu"))
    return b.as_markup()

def back_kb():
    b = InlineKeyboardBuilder()
    b.row(CallbackButton(text="⬅ Назад в меню", payload="back_to_menu"))
    return b.as_markup()

def calculator_kb():
    b = InlineKeyboardBuilder()
    b.row(CallbackButton(text="🚪 Откатные ворота", payload="calc_vorota"))
    b.row(CallbackButton(text="🏠 Навес", payload="calc_naves"))
    b.row(CallbackButton(text="🪜 Лестница", payload="calc_lestnica"))
    b.row(CallbackButton(text="🛡 Ограждение", payload="calc_ograzhdenie"))
    b.row(CallbackButton(text="🎨 Покраска", payload="calc_pokraska"))
    b.row(CallbackButton(text="🔥 Мангал", payload="calc_mangal"))
    b.row(CallbackButton(text="⬅ Назад", payload="back_to_menu"))
    return b.as_markup()

def cancel_kb():
    b = InlineKeyboardBuilder()
    b.row(CallbackButton(text="❌ Отмена", payload="back_to_menu"))
    return b.as_markup()

def calc_result_kb():
    b = InlineKeyboardBuilder()
    b.row(CallbackButton(text="📞 Связаться с оператором", payload="contact"))
    b.row(CallbackButton(text="🧮 Ещё расчёт", payload="calc"))
    b.row(CallbackButton(text="⬅ В меню", payload="back_to_menu"))
    return b.as_markup()

@dp.message_created(CommandStart())
async def cmd_start(event: MessageCreated):
    user_id = event.message.sender.user_id
    name = event.message.sender.first_name or "—"
    logger.info(f"/start user_id={user_id}")
    if user_id not in seen_users:
        seen_users.add(user_id)
        await notify_admin(f"🆕 Новый пользователь: {name} (ID {user_id})")
    await event.message.answer(TEXT_MENU, attachments=[main_menu_kb()])

@dp.message_callback()
async def handle_callback(event: MessageCallback):
    try:
        payload = event.callback.payload
    except AttributeError:
        return
    if not payload:
        return
    user_id = get_real_user_id(event)
    name = "—"
    for attr in ("sender", "recipient"):
        obj = getattr(event.message, attr, None)
        if obj and getattr(obj, "first_name", None):
            name = obj.first_name
            break
    logger.info(f"CALLBACK {payload} user_id={user_id}")

    if payload in CALC_SERVICES:
        service = CALC_SERVICES[payload]
        if service["question"] is None:
            await event.message.answer(
                f"🔥 *{service['name']}*\n\nПримерная стоимость: *от {service['price']} ₽*",
                attachments=[calc_result_kb()]
            )
            if user_id:
                await notify_admin(f"🔥 Мангал: {name} (ID {user_id})")
        else:
            if user_id:
                user_states[user_id] = {"service_key": payload, "step": "waiting_number"}
                logger.info(f"SAVED user_id={user_id}")
            await event.message.answer(
                f"🧮 *{service['name']}*\n\n{service['question']}",
                attachments=[cancel_kb()]
            )
        return

    if payload == "services":
        await event.message.answer(TEXT_SERVICES, attachments=[back_kb()])
    elif payload == "prices":
        await event.message.answer(TEXT_PRICES, attachments=[back_kb()])
    elif payload == "terms":
        await event.message.answer(TEXT_TERMS, attachments=[back_kb()])
    elif payload == "contact":
        await event.message.answer(TEXT_CONTACT, attachments=[contact_kb()])
        if user_id:
            await notify_admin(f"📞 Хочет связаться: {name} (ID {user_id})")
    elif payload == "calc":
        await event.message.answer(TEXT_CALC_INTRO, attachments=[calculator_kb()])
    elif payload == "show_wa":
        await event.message.answer(TEXT_WA)
    elif payload == "show_tg":
        await event.message.answer(TEXT_TG)
    elif payload == "show_max":
        await event.message.answer(TEXT_MAX)
    elif payload == "show_call":
        await event.message.answer(TEXT_CALL)
    elif payload == "back_to_menu":
        if user_id and user_id in user_states:
            del user_states[user_id]
        await event.message.answer(TEXT_MENU, attachments=[main_menu_kb()])
    else:
        await event.message.answer(TEXT_FALLBACK, attachments=[main_menu_kb()])

@dp.message_created(F.message.body.text)
async def handle_text(event: MessageCreated):
    text = event.message.body.text.strip()
    text_lower = text.lower()
    if text_lower in ALL_PAYLOADS:
        return
    user_id = event.message.sender.user_id
    logger.info(f"MSG user_id={user_id}: {text}")

    if text_lower == "/debug":
        r = getattr(event.message, "recipient", None)
        await event.message.answer(
            f"sender.user_id = {getattr(event.message.sender, 'user_id', '—')}\n"
            f"recipient.user_id = {getattr(r, 'user_id', '—')}\n"
            f"recipient.chat_id = {getattr(r, 'chat_id', '—')}"
        )
        return

    if text_lower == "/whoami":
        await event.message.answer(f"Ваш ID: {user_id}")
        return

    if text_lower == "/admin_test":
        await notify_admin(f"🔔 Тест от {user_id}")
        await event.message.answer("Отправлено.")
        return

    if user_id in user_states and user_states[user_id].get("step") == "waiting_number":
        logger.info(f"STATE найден user_id={user_id}")
        try:
            number = float(text.replace(",", "."))
            key = user_states[user_id]["service_key"]
            service = CALC_SERVICES[key]
            total = int(number * service["price"])
            await event.message.answer(
                f"🧮 *{service['name']}*\n\n"
                f"• Количество: {number} {service['unit']}\n"
                f"• Цена: {service['price']} ₽\n"
                f"• *Итого: ~{total} ₽*",
                attachments=[calc_result_kb()]
            )
            await notify_admin(f"🧮 Расчёт: {service['name']}, {number} {service['unit']}, ~{total} ₽ (ID {user_id})")
            del user_states[user_id]
            return
        except ValueError:
            await event.message.answer("Введите число. Например: 4.5", attachments=[cancel_kb()])
            return
    else:
        logger.info(f"STATE НЕТ user_id={user_id}. В памяти: {list(user_states.keys())}")

    if "услуг" in text_lower:
        await event.message.answer(TEXT_SERVICES, attachments=[back_kb()])
    elif "цен" in text_lower:
        await event.message.answer(TEXT_PRICES, attachments=[back_kb()])
    elif "срок" in text_lower:
        await event.message.answer(TEXT_TERMS, attachments=[back_kb()])
    elif "оператор" in text_lower or "связаться" in text_lower:
        await event.message.answer(TEXT_CONTACT, attachments=[contact_kb()])
    elif "калькулятор" in text_lower:
        await event.message.answer(TEXT_CALC_INTRO, attachments=[calculator_kb()])
    else:
        await event.message.answer(TEXT_FALLBACK, attachments=[main_menu_kb()])

async def main():
    public_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
    if not public_domain:
        await dp.start_polling(bot)
        return
    webhook_url = f"https://{public_domain}/webhook"
    logger.info(f"Webhook: {webhook_url}")
    await bot.subscribe_webhook(
        url=webhook_url,
        update_types=[
            UpdateType.MESSAGE_CREATED,
            UpdateType.BOT_STARTED,
            UpdateType.MESSAGE_CALLBACK,
        ],
        secret=WEBHOOK_SECRET
    )
    logger.info("Webhook OK")
    await dp.handle_webhook(
        bot=bot, host="0.0.0.0", port=8080,
        path="/webhook", secret=WEBHOOK_SECRET
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
