import os
import logging
from maxapi import Bot, Dispatcher, F
from maxapi.filters.command import CommandStart
from maxapi.types import (
    MessageCreated,
    MessageCallback,
    CallbackButton,
)
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
    raise RuntimeError("Переменная MAX_BOT_TOKEN не задана!")

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
    """
    Достаёт ID реального пользователя (не бота).
    Пробует несколько мест, пока не найдёт.
    """
    candidates = []

    # 1. callback.user_id (если есть в структуре Callback)
    if hasattr(event, "callback") and event.callback is not None:
        if hasattr(event.callback, "user") and event.callback.user is not None:
            candidates.append(("callback.user.user_id", getattr(event.callback.user, "user_id", None)))

    # 2. event.message.recipient.user_id — для callback, где sender — бот
    if hasattr(event.message, "recipient") and event.message.recipient is not None:
        candidates.append(("message.recipient.user_id", getattr(event.message.recipient, "user_id", None)))

    # 3. event.message.sender.user_id — для обычных сообщений
    if hasattr(event.message, "sender") and event.message.sender is not None:
        candidates.append(("message.sender.user_id", getattr(event.message.sender, "user_id", None)))

    for label, val in candidates:
        if val:
            logger.info(f"USER_ID из {label} = {val}")
            return val

    logger.warning(f"НЕ НАЙДЕН user_id, кандидаты: {candidates}")
    return None


async def notify_admin(text: str):
    if not ADMIN_ID:
        logger.warning("ADMIN_ID не задан")
        return
    try:
        await bot.send_message(chat_id=int(ADMIN_ID), text=text)
    except Exception as e:
        logger.error(f"Не смог отправить админу: {e}")


# ---------- ТЕКСТЫ ----------
TEXT_MENU = (
    "Здравствуйте! Я бот сварочной мастерской СварМастер.\n"
    "Чем могу помочь?\n\n"
    "Выберите пункт меню ниже:"
)

TEXT_SERVICES = (
    "🔧 *Наши услуги:*\n\n"
    "• Сварочные работы\n"
    "• Ворота и калитки\n"
    "• Навесы и козырьки\n"
    "• Лестницы и перила\n"
    "• Порошковая покраска\n"
    "• Мебель из металла\n"
    "• Ограждения и заборы\n"
    "• Изготовление на заказ"
)

TEXT_PRICES = (
    "💰 *Цены:*\n\n"
    "• Сварочные работы — от 1500 ₽/час\n"
    "• Ворота — от 4500 ₽/м²\n"
    "• Навесы — от 3800 ₽/м²\n"
    "• Лестницы — от 2200 ₽/ступень\n"
    "• Порошковая покраска — от 1200 ₽/м²\n\n"
    "Точная стоимость — после замера."
)

TEXT_TERMS = (
    "⏱ *Сроки изготовления:*\n\n"
    "• Стандартный заказ — 5–10 рабочих дней\n"
    "• Срочный заказ — от 2 дней (наценка 30%)\n\n"
    "Сроки фиксируются в договоре."
)

TEXT_CONTACT = "📞 *Связаться с оператором:*\n\nВыберите удобный способ:"

TEXT_WA = "💬 *WhatsApp*\n\nНапишите нам: https://wa.me/79159190508"
TEXT_TG = "✈️ *Telegram*\n\nНапишите нам: https://t.me/SKYHITORED"
TEXT_MAX = "📱 *MAX Messenger*\n\nНапишите нам: https://max.ru/u/f9LHodD0cOLt4DlpXkQuKcUA-rwanDwWOPRvmBInmJ1e_HlzRa6DjU1K1gU"
TEXT_CALL = "📱 *Позвонить*\n\nТелефон: +7 (915) 919-05-08"

TEXT_CALC_INTRO = "🧮 *Калькулятор стоимости*\n\nВыберите услугу — я посчитаю примерную цену:"

TEXT_FALLBACK = "Пожалуйста, воспользуйтесь кнопками меню ниже 👇"

CALC_SERVICES = {
    "calc_vorota":      {"name": "Откатные ворота",    "unit": "м²",       "price": 4500, "question": "Введите площадь ворот в м².\nНапример: 4.5"},
    "calc_naves":       {"name": "Навес",               "unit": "м²",       "price": 3800, "question": "Введите площадь навеса в м².\nНапример: 20"},
    "calc_lestnica":    {"name": "Лестница",            "unit": "ступеней", "price": 2200, "question": "Введите количество ступеней.\nНапример: 10"},
    "calc_ograzhdenie": {"name": "Ограждение / перила", "unit": "пог. м",   "price": 1800, "question": "Введите длину в метрах.\nНапример: 15"},
    "calc_pokraska":    {"name": "Порошковая покраска", "unit": "м²",       "price": 1200, "question": "Введите площадь покраски в м².\nНапример: 8"},
    "calc_mangal":      {"name": "Мангал / барбекю",    "unit": "шт.",      "price": 8000, "question": None},
}


# ---------- КЛАВИАТУРЫ ----------
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


# ---------- /start ----------
@dp.message_created(CommandStart())
async def cmd_start(event: MessageCreated):
    user_id = event.message.sender.user_id
    name = event.message.sender.first_name or "не указано"
    username = getattr(event.message.sender, "username", None) or "—"
    logger.info(f"CMD /start от user_id={user_id}")

    if user_id not in seen_users:
        seen_users.add(user_id)
        await notify_admin(f"🆕 *Новый пользователь!*\n\nID: `{user_id}`\nИмя: {name}\nUsername: @{username}")

    await event.message.answer(TEXT_MENU, attachments=[main_menu_kb()])


# ---------- CALLBACK ----------
@dp.message_callback()
async def handle_callback(event: MessageCallback):
    try:
        payload = event.callback.payload
    except AttributeError:
        logger.warning("Callback без payload")
        return

    if not payload:
        return

    user_id = get_real_user_id(event)
    logger.info(f"CALLBACK: {payload} от user_id={user_id}")

    name = "—"
    for attr in ("sender", "recipient"):
        obj = getattr(event.message, attr, None)
        if obj and getattr(obj, "first_name", None):
            name = obj.first_name
            break

    # Калькулятор — выбор услуги
    if payload in CALC_SERVICES:
        service = CALC_SERVICES[payload]
        if service["question"] is None:
            await event.message.answer(
                f"🔥 *{service['name']}*\n\nПримерная стоимость: *от {service['price']} ₽*\n\n_Точную цену назовём после обсуждения._",
                attachments=[calc_result_kb()]
            )
            if user_id:
                await notify_admin(f"🔥 *Интерес к мангалу*\n\nID: `{user_id}`\nИмя: {name}")
        else:
            if user_id:
                user_states[user_id] = {"service_key": payload, "step": "waiting_number"}
                logger.info(f"SAVED state for user_id={user_id}: {user_states[user_id]}")
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
            await notify_admin(f"📞 *Клиент хочет связаться!*\n\nID: `{user_id}`\nИмя: {name}")
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


# ---------- ТЕКСТ ----------
@dp.message_created(F.message.body.text)
async def handle_text(event: MessageCreated):
    text = event.message.body.text.strip()
    text_lower = text.lower()

    if text_lower in ALL_PAYLOADS:
        logger.info(f"SKIP payload-as-text: {text_lower}")
        return

    user_id = event.message.sender.user_id
    logger.info(f"MSG от user_id={user_id}: {text}")

    # DEBUG — покажет структуру события
    if text_lower == "/debug":
        info = []
        info.append(f"`sender.user_id` = {getattr(event.message.sender, 'user_id', '—')}")
        info.append(f"`sender.first_name` = {getattr(event.message.sender, 'first_name', '—')}")
        info.append(f"`recipient.user_id` = {getattr(getattr(event.message, 'recipient', None), 'user_id', '—')}")
        info.append(f"`recipient.chat_id` = {getattr(getattr(event.message, 'recipient', None), 'chat_id', '—')}")
        info.append(f"`callback` = {getattr(event, 'callback', None)}")
        await event.message.answer("```\n" + "\n".join(info) + "\n```")
        return

    if text_lower == "/whoami":
        await event.message.answer(f"Ваш user_id: `{user_id}`")
        return

    if text_lower == "/admin_test":
        await notify_admin(f"🔔 Тест от {user_id}")
        await event.message.answer("Уведомление отправлено.")
        return

    # Калькулятор — ожидание числа
    if user_id in user_states and user_states[user_id].get("step") == "waiting_number":
        logger.info(f"Найден state для user_id={user_id}: {user_states[user_id]}")
        try:
            number = float(text.replace(",", "."))
            key = user_states[user_id]["service_key"]
            service = CALC_SERVICES[key]
            total = int(number * service["price"])

            await event.message.answer(
                f"🧮 *Расчёт для: {service['name']}*\n\n"
                f"• Количество: {number} {service['unit']}\n"
                f"• Цена за единицу: {service['price']} ₽\n"
                f"• *Примерная стоимость: ~{total} ₽*\n\n"
                f"_Точную стоимость назовём после замера._",
                attachments=[calc_result_kb()]
            )

            await notify_admin(
                f"🧮 *Расчёт*\n\nID: `{user_id}`\nУслуга: {service['name']}\nКол-во: {number} {service['unit']}\nИтог: *~{total} ₽*"
            )

            del user_states[user_id]
            return
        except ValueError:
            await event.message.answer(
                "Пожалуйста, введите число.\nНапример: `4.5` или `20`",
                attachments=[cancel_kb()]
            )
            return
    else:
        if user_id in user_states:
            logger.info(f"STATE есть, но step не waiting_number: {user_states[user_id]}")
        else:
            logger.info(f"STATE НЕТ для user_id={user_id}. В памяти: {list(user_states.keys())}")

    if "услуг" in text_lower:
        await event.message.answer(TEXT_SERVICES, attachments=[back_kb()])
    elif "цен" in text_lower:
        await event.message.answer(TEXT_PRICES, attachments=[back_kb()])
    elif "срок" in text_lower:
        await event.message.answer(TEXT_TERMS, attachments=[back_kb()])
    elif "оператор" in text_lower or "связаться" in text_lower or "позвонить" in text_lower:
        await event.message.answer(TEXT_CONTACT, attachments=[contact_kb()])
    elif "калькулятор" in text_lower or "расчёт" in text_lower or "расчет" in text_lower:
        await event.message.answer(TEXT_CALC_INTRO, attachments=[calculator_kb()])
    elif "привет" in text_lower or "здравств" in text_lower:
        await event.message.answer(TEXT_MENU, attachments=[main_menu_kb()])
    else:
        await event.message.answer(TEXT_FALLBACK, attachments=[main_menu_kb()])


# ---------- ЗАПУСК ----------
async def main():
    public_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
    if not public_domain:
        logger.error("RAILWAY_PUBLIC_DOMAIN не задан! Запуск через polling...")
        await dp.start_polling(bot)
        return

    webhook_url = f"https://{public_domain}/webhook"
    logger.info(f"Регистрирую webhook: {webhook_url}")

    await bot.subscribe_webhook(
        url=webhook_url,
        update_types=[
            UpdateType.MESSAGE_CREATED,
            UpdateType.BOT_STARTED,
            UpdateType.MESSAGE_CALLBACK,
        ],
        secret=WEBHOOK_SECRET
    )
    logger.info("Webhook зарегистрирован")

    await dp.handle_webhook(
        bot=bot, host="0.0.0.0", port=8080,
        path="/webhook", secret=WEBHOOK_SECRET
    )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())ser_id]["service_key"]
            service = CALC_SERVICES[key]
            total = int(number * service["price"])

            await event.message.answer(
                f"🧮 *Расчёт для: {service['name']}*\n\n"
                f"• Количество: {number} {service['unit']}\n"
                f"• Цена за единицу: {service['price']} ₽\n"
                f"• *Примерная стоимость: ~{total} ₽*\n\n"
                f"_Точную стоимость назовём после замера._",
                attachments=[calc_result_kb()]
            )

            await notify_admin(
                f"🧮 *Расчёт в калькуляторе*\n\nID: `{user_id}`\nУслуга: {service['name']}\nКоличество: {number} {service['unit']}\nИтог: *~{total} ₽*"
            )

            del user_states[user_id]
            return
        except ValueError:
            await event.message.answer(
                "Пожалуйста, введите число.\nНапример: `4.5` или `20`",
                attachments=[cancel_kb()]
            )
            return

    # Обычные текстовые команды
    if "услуг" in text_lower:
        await event.message.answer(TEXT_SERVICES, attachments=[back_kb()])
    elif "цен" in text_lower:
        await event.message.answer(TEXT_PRICES, attachments=[back_kb()])
    elif "срок" in text_lower:
        await event.message.answer(TEXT_TERMS, attachments=[back_kb()])
    elif "оператор" in text_lower or "связаться" in text_lower or "позвонить" in text_lower:
        await event.message.answer(TEXT_CONTACT, attachments=[contact_kb()])
    elif "калькулятор" in text_lower or "расчёт" in text_lower or "расчет" in text_lower:
        await event.message.answer(TEXT_CALC_INTRO, attachments=[calculator_kb()])
    elif "привет" in text_lower or "здравств" in text_lower:
        await event.message.answer(TEXT_MENU, attachments=[main_menu_kb()])
    else:
        await event.message.answer(TEXT_FALLBACK, attachments=[main_menu_kb()])


# ---------- ЗАПУСК ----------
async def main():
    public_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
    if not public_domain:
        logger.error("RAILWAY_PUBLIC_DOMAIN не задан! Запуск через polling...")
        await dp.start_polling(bot)
        return

    webhook_url = f"https://{public_domain}/webhook"
    logger.info(f"Регистрирую webhook: {webhook_url}")

    await bot.subscribe_webhook(
        url=webhook_url,
        update_types=[
            UpdateType.MESSAGE_CREATED,
            UpdateType.BOT_STARTED,
            UpdateType.MESSAGE_CALLBACK,
        ],
        secret=WEBHOOK_SECRET
    )
    logger.info("Webhook успешно зарегистрирован")

    await dp.handle_webhook(
        bot=bot, host="0.0.0.0", port=8080,
        path="/webhook", secret=WEBHOOK_SECRET
    )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
