import os
import logging
import asyncio
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
user_locks = set()
seen_users = set()

ALL_PAYLOADS = {
    "services", "prices", "terms", "contact", "calc",
    "show_wa", "show_tg", "show_max", "show_call", "back_to_menu",
    "calc_vorota", "calc_kalitka", "calc_naves", "calc_lestnica",
    "calc_ograzhdenie", "calc_pokraska", "calc_mangal", "calc_kozyrek",
    "calc_zabor", "calc_svarka",
}


def get_real_user_id(event):
    if hasattr(event, "callback") and event.callback is not None:
        u = getattr(event.callback, "user", None)
        if u and getattr(u, "user_id", None):
            return u.user_id
    r = getattr(event.message, "recipient", None)
    if r and getattr(r, "user_id", None):
        return r.user_id
    s = getattr(event.message, "sender", None)
    if s and getattr(s, "user_id", None):
        return s.user_id
    return None


async def notify_admin(text):
    if not ADMIN_ID:
        return
    try:
        await bot.send_message(chat_id=int(ADMIN_ID), text=text)
    except Exception as e:
        logger.error(f"notify_admin error: {e}")


# ========== ТЕКСТЫ ==========
TEXT_MENU = "Здравствуйте! Я бот сварочной мастерской СварМастер.\nЧем могу помочь?\n\nВыберите пункт меню ниже:"
TEXT_SERVICES = (
    "🔧 *Наши услуги:*\n\n"
    "• Сварочные работы (выезд)\n"
    "• Откатные и распашные ворота\n"
    "• Калитки\n"
    "• Навесы и козырьки\n"
    "• Лестницы и перила\n"
    "• Ограждения и заборы\n"
    "• Порошковая покраска\n"
    "• Мебель из металла\n"
    "• Мангалы и барбекю\n"
    "• Изготовление на заказ"
)
TEXT_PRICES = (
    "💰 *Ориентировочные цены:*\n\n"
    "• Сварочные работы — от 1 500 ₽/час\n"
    "• Откатные ворота — от 4 500 ₽/м²\n"
    "• Распашные ворота — от 3 800 ₽/м²\n"
    "• Калитка — от 12 000 ₽/шт\n"
    "• Навес — от 3 800 ₽/м²\n"
    "• Козырёк — от 4 200 ₽/м²\n"
    "• Лестница — от 3 200 ₽/ступень\n"
    "• Ограждение — от 1 800 ₽/пог. м\n"
    "• Забор — от 2 200 ₽/пог. м\n"
    "• Покраска — от 300 ₽/м²\n"
    "• Мангал — от 8 000 ₽/шт\n\n"
    "_Точная цена — после замера._"
)
TEXT_TERMS = (
    "⏱ *Сроки изготовления:*\n\n"
    "• Стандартный заказ — 5–10 рабочих дней\n"
    "• Срочный заказ — от 2 дней (наценка 30%)\n"
    "• Сложные проекты — обсуждаем индивидуально\n\n"
    "Сроки фиксируются в договоре."
)
TEXT_CONTACT = "📞 *Связаться с оператором:*"
TEXT_WA = "💬 WhatsApp: https://wa.me/79159190508"
TEXT_TG = "✈️ Telegram: https://t.me/SKYHITORED"
TEXT_MAX = "📱 MAX: https://max.ru/u/f9LHodD0cOLt4DlpXkQuKcUA-rwanDwWOPRvmBInmJ1e_HlzRa6DjU1K1gU"
TEXT_CALL = "📱 Позвонить: +7 (915) 919-05-08"
TEXT_CALC_INTRO = "🧮 *Калькулятор стоимости*\n\nВыберите услугу:"
TEXT_FALLBACK = "Пожалуйста, воспользуйтесь кнопками меню ниже 👇"

CALC_SERVICES = {
    "calc_vorota": {
        "name": "Откатные ворота", "type": "multi",
        "question": "Введите ширину и высоту ворот в метрах через пробел.\nНапример: 4.5 2",
        "price_per_m2": 4500,
        "desc": "Каркас: профтруба 60×40×2 и 40×20×2, направляющая 70×60. Обшивка — профнастил или евроштакетник.",
    },
    "calc_kalitka": {
        "name": "Калитка", "type": "single",
        "question": "Введите ширину калитки в метрах.\nНапример: 1",
        "price_per_m": 12000,
        "desc": "Каркас 40×40×2, стандарт высота 2 м.",
    },
    "calc_naves": {
        "name": "Навес из поликарбоната", "type": "multi",
        "question": "Введите длину и ширину навеса в метрах через пробел.\nНапример: 6 3",
        "price_per_m2": 3800,
        "desc": "Каркас 60×40×3, поликарбонат 8–10 мм. Расчёт под снеговую нагрузку МО (180 кг/м²).",
    },
    "calc_kozyrek": {
        "name": "Козырёк", "type": "multi",
        "question": "Введите длину и ширину козырька в метрах через пробел.\nНапример: 2.5 1",
        "price_per_m2": 4200,
        "desc": "Арочный или консольный. Крепление к стене, поликарбонат 8 мм.",
    },
    "calc_lestnica": {
        "name": "Лестница металлическая", "type": "single",
        "question": "Введите количество ступеней.\nНапример: 10",
        "price_per_step": 3200,
        "desc": "Стандарт: подступенок 150–180 мм, проступь 270–300 мм.",
    },
    "calc_ograzhdenie": {
        "name": "Ограждение / перила", "type": "single",
        "question": "Введите длину в метрах.\nНапример: 15",
        "price_per_m": 1800,
        "desc": "Стойки 40×40×2, поручень Ø50. Высота стандарт 900 мм.",
    },
    "calc_zabor": {
        "name": "Забор", "type": "single",
        "question": "Введите длину забора в метрах.\nНапример: 30",
        "price_per_m": 2200,
        "desc": "Столбы 60×60×2, лаги 40×20×2, обшивка — профнастил/евроштакетник.",
    },
    "calc_pokraska": {
        "name": "Порошковая покраска", "type": "single",
        "question": "Введите площадь покраски в м².\nНапример: 8",
        "price_per_m2": 500,
        "desc": "Обезжиривание, фосфатирование, нанесение порошка, полимеризация 180–200°C.",
    },
    "calc_mangal": {
        "name": "Мангал / барбекю", "type": "fixed",
        "price": 8000,
        "desc": "Сталь 3 мм (стенки), дно 4 мм, ножки 25×25.",
    },
    "calc_svarka": {
        "name": "Сварочные работы (выезд)", "type": "single",
        "question": "Введите количество часов работы.\nНапример: 3",
        "price_per_hour": 1500,
        "desc": "Ручная дуговая, полуавтомат, аргон. Выезд по Москве и МО.",
    },
}


# ========== КЛАВИАТУРЫ ==========
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
    b.row(CallbackButton(text="🚪 Калитка", payload="calc_kalitka"))
    b.row(CallbackButton(text="🏠 Навес", payload="calc_naves"))
    b.row(CallbackButton(text="🏠 Козырёк", payload="calc_kozyrek"))
    b.row(CallbackButton(text="🪜 Лестница", payload="calc_lestnica"))
    b.row(CallbackButton(text="🛡 Ограждение", payload="calc_ograzhdenie"))
    b.row(CallbackButton(text="🛡 Забор", payload="calc_zabor"))
    b.row(CallbackButton(text="🎨 Покраска", payload="calc_pokraska"))
    b.row(CallbackButton(text="🔥 Мангал", payload="calc_mangal"))
    b.row(CallbackButton(text="🔧 Сварочные работы", payload="calc_svarka"))
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


# ========== РАСЧЁТ ==========
def calculate_result(service_key, text):
    service = CALC_SERVICES[service_key]
    cleaned = text.replace(",", ".").replace("х", " ").replace("x", " ").replace("×", " ")
    parts = cleaned.split()
    try:
        numbers = [float(p) for p in parts]
    except ValueError:
        return None, "Не могу распознать числа. Введите цифры, например: 4.5 2"

    if service["type"] == "single":
        if len(numbers) < 1:
            return None, "Введите число."
        x = numbers[0]
        if "price_per_m" in service:
            total = int(x * service["price_per_m"])
            return total, f"{x} м × {service['price_per_m']} ₽/м"
        if "price_per_step" in service:
            total = int(x * service["price_per_step"])
            return total, f"{x} ступ. × {service['price_per_step']} ₽/ступ."
        if "price_per_m2" in service:
            if service_key == "calc_pokraska":
                price = 500 if x < 10 else (400 if x < 100 else 300)
            else:
                price = service["price_per_m2"]
            total = int(x * price)
            return total, f"{x} м² × {price} ₽/м²"
        if "price_per_hour" in service:
            total = int(x * service["price_per_hour"])
            return total, f"{x} ч × {service['price_per_hour']} ₽/ч"

    if service["type"] == "multi":
        if len(numbers) < 2:
            return None, "Введите два числа: длина и ширина.\nНапример: 4.5 2"
        a, b = numbers[0], numbers[1]
        area = a * b
        total = int(area * service["price_per_m2"])
        return total, f"{a} м × {b} м = {area:.2f} м² × {service['price_per_m2']} ₽/м²"

    if service["type"] == "fixed":
        return service["price"], f"от {service['price']} ₽ (фикс)"

    return None, "Не могу посчитать"


# ========== /start ==========
@dp.message_created(CommandStart())
async def cmd_start(event: MessageCreated):
    user_id = event.message.sender.user_id
    if user_id in user_locks:
        return
    user_locks.add(user_id)
    try:
        name = event.message.sender.first_name or "—"
        logger.info(f"/start user_id={user_id}")
        if user_id not in seen_users:
            seen_users.add(user_id)
            await notify_admin(f"🆕 Новый пользователь: {name} (ID {user_id})")
        await event.message.answer(TEXT_MENU, attachments=[main_menu_kb()])
    finally:
        user_locks.discard(user_id)


# ========== CALLBACK ==========
@dp.message_callback()
async def handle_callback(event: MessageCallback):
    try:
        payload = event.callback.payload
    except AttributeError:
        return
    if not payload:
        return

    user_id = get_real_user_id(event)
    if user_id and user_id in user_locks:
        logger.info(f"CALLBACK {payload} — ПРОПУСК (lock {user_id})")
        return
    if user_id:
        user_locks.add(user_id)

    try:
        name = "—"
        for attr in ("sender", "recipient"):
            obj = getattr(event.message, attr, None)
            if obj and getattr(obj, "first_name", None):
                name = obj.first_name
                break
        logger.info(f"CALLBACK {payload} user_id={user_id}")

        if payload in CALC_SERVICES:
            service = CALC_SERVICES[payload]
            if service["type"] == "fixed":
                text = (
                    f"🔥 *{service['name']}*\n\n"
                    f"Ориентировочно: *от {service['price']} ₽*\n\n"
                    f"_{service.get('desc', '')}_"
                )
                await event.message.answer(text, attachments=[calc_result_kb()])
                if user_id:
                    await notify_admin(f"🔥 {service['name']}: {name} (ID {user_id})")
            else:
                if user_id:
                    user_states[user_id] = {"service_key": payload, "step": "waiting_number"}
                text = f"🧮 *{service['name']}*\n\n{service['question']}"
                if service.get("desc"):
                    text += f"\n\n_📋 {service['desc']}_"
                await event.message.answer(text, attachments=[cancel_kb()])
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
                user_states.pop(user_id, None)
            await event.message.answer(TEXT_MENU, attachments=[main_menu_kb()])
        else:
            await event.message.answer(TEXT_FALLBACK, attachments=[main_menu_kb()])
    finally:
        if user_id:
            user_locks.discard(user_id)


# ========== ТЕКСТ ==========
@dp.message_created(F.message.body.text)
async def handle_text(event: MessageCreated):
    text = event.message.body.text.strip()
    text_lower = text.lower()

    if text_lower in ALL_PAYLOADS:
        return

    user_id = event.message.sender.user_id

    if user_id in user_locks:
        logger.info(f"MSG user_id={user_id} — ПРОПУСК (lock)")
        return
    user_locks.add(user_id)

    try:
        logger.info(f"MSG user_id={user_id}: {text}")

        if text_lower == "/whoami":
            await event.message.answer(f"Ваш ID: {user_id}")
            return
        if text_lower == "/admin_test":
            await notify_admin(f"🔔 Тест от {user_id}")
            await event.message.answer("Отправлено.")
            return

        if user_id in user_states and user_states[user_id].get("step") == "waiting_number":
            state = user_states.pop(user_id, None)
            if state is None:
                return
            key = state["service_key"]
            service = CALC_SERVICES[key]
            total, descr = calculate_result(key, text)

            if total is None:
                await event.message.answer(f"❌ {descr}", attachments=[cancel_kb()])
                return

            formatted_total = f"{total:,}".replace(",", " ")
            await event.message.answer(
                f"🧮 *{service['name']}*\n\n"
                f"📐 Расчёт: {descr}\n"
                f"💰 *Примерная стоимость: ~{formatted_total} ₽*\n\n"
                f"_Точную стоимость назовём после замера._",
                attachments=[calc_result_kb()]
            )
            await notify_admin(
                f"🧮 *Расчёт*\n\n"
                f"ID: `{user_id}`\n"
                f"Услуга: {service['name']}\n"
                f"Расчёт: {descr}\n"
                f"Итог: *~{formatted_total} ₽*"
            )
            return

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
    finally:
        user_locks.discard(user_id)


# ========== ЗАПУСК ==========
async def main():
    public_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
    if not public_domain:
        await dp.start_polling(bot)
        return

    # 1. Снимаем ВСЕ старые подписки
    try:
        await bot.delete_webhook()
        logger.info("✅ Старые подписки удалены")
    except Exception as e:
        logger.warning(f"⚠️ delete_webhook: {e}")

    # 2. Пауза, чтобы MAX обработал удаление
    await asyncio.sleep(2)

    # 3. Подписываемся ТОЛЬКО на свой URL
    webhook_url = f"https://{public_domain}/webhook"
    logger.info(f"🔗 Webhook: {webhook_url}")
    await bot.subscribe_webhook(
        url=webhook_url,
        update_types=[UpdateType.MESSAGE_CREATED, UpdateType.BOT_STARTED, UpdateType.MESSAGE_CALLBACK],
        secret=WEBHOOK_SECRET
    )
    logger.info("✅ Webhook OK")

    await dp.handle_webhook(bot=bot, host="0.0.0.0", port=8080, path="/webhook", secret=WEBHOOK_SECRET)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
