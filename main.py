import os
import logging
import asyncio
import httpx
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
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

if not MAX_BOT_TOKEN:
    raise RuntimeError("MAX_BOT_TOKEN не задан!")

bot = Bot(MAX_BOT_TOKEN)
dp = Dispatcher()

user_states = {}
user_locks = set()

admin_chat_id = int(ADMIN_CHAT_ID) if ADMIN_CHAT_ID else None


async def send_to_max(chat_id, text):
    """Отправка с полным логированием ответа"""
    try:
        result = await bot.send_message(chat_id=chat_id, text=text)
        logger.info(f"MAX RESPONSE: type={type(result)} value={result}")
        return result
    except Exception as e:
        logger.error(f"MAX EXCEPTION: {type(e).__name__}: {e}")
        return None


async def notify_admin(text):
    global admin_chat_id

    if admin_chat_id:
        logger.info(f"Отправляю в MAX на chat_id={admin_chat_id}")
        await send_to_max(admin_chat_id, text)
    else:
        logger.warning("admin_chat_id не задан")

    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
                )
        except Exception as e:
            logger.error(f"TG notify error: {e}")


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
    "• Калитка — от 12 000 ₽/шт\n"
    "• Навес — от 3 800 ₽/м²\n"
    "• Козырёк — от 4 200 ₽/м²\n"
    "• Лестница — от 3 200 ₽/ступень\n"
    "• Ограждение — от 1 800 ₽/пог. м\n"
    "• Забор — от 2 200 ₽/пог. м\n"
    "• Покраска — от 300 ₽/м²\n"
    "• Мангал — от 8 000 ₽\n\n"
    "_Точная цена — после замера._"
)
TEXT_TERMS = (
    "⏱ *Сроки изготовления:*\n\n"
    "• Стандартный заказ — 5–10 рабочих дней\n"
    "• Срочный заказ — от 2 дней (наценка 30%)"
)
TEXT_CONTACT = "📞 *Связаться с оператором:*"
TEXT_WA = "💬 WhatsApp: https://wa.me/79159190508"
TEXT_TG = "✈️ Telegram: https://t.me/SKYHITORED"
TEXT_MAX = "📱 MAX: https://max.ru/u/f9LHodD0cOLt4DlpXkQuKcUA-rwanDwWOPRvmBInmJ1e_HlzRa6DjU1K1gU"
TEXT_CALL = "📱 Позвонить: +7 (915) 919-05-08"
TEXT_CALC_INTRO = "🧮 *Калькулятор стоимости*\n\nВыберите услугу:"
TEXT_FALLBACK = "Пожалуйста, воспользуйтесь кнопками меню ниже 👇"
TEXT_LEAD_FORM = (
    "📝 *Оставить заявку*\n\n"
    "Напишите в одном сообщении:\n\n"
    "*Имя, телефон, что нужно сделать*\n\n"
    "_Пример: Иван, +7 999 123-45-67, ворота 4 на 2_"
)

CALC_SERVICES = {
    "calc_vorota":      {"name": "Откатные ворота", "type": "multi", "question": "Введите ширину и высоту ворот в метрах через пробел.\nНапример: 4.5 2", "price_per_m2": 4500, "desc": "Каркас 60×40×2, направляющая 70×60."},
    "calc_kalitka":     {"name": "Калитка", "type": "single", "question": "Введите ширину калитки в метрах.\nНапример: 1", "price_per_m": 12000, "desc": "Каркас 40×40×2, высота 2 м."},
    "calc_naves":       {"name": "Навес", "type": "multi", "question": "Введите длину и ширину навеса в метрах через пробел.\nНапример: 6 3", "price_per_m2": 3800, "desc": "Каркас 60×40×3, поликарбонат 8–10 мм."},
    "calc_kozyrek":     {"name": "Козырёк", "type": "multi", "question": "Введите длину и ширину козырька в метрах через пробел.\nНапример: 2.5 1", "price_per_m2": 4200, "desc": "Арочный или консольный, поликарбонат 8 мм."},
    "calc_lestnica":    {"name": "Лестница", "type": "single", "question": "Введите количество ступеней.\nНапример: 10", "price_per_step": 3200, "desc": "Подступенок 150–180 мм, проступь 270–300 мм."},
    "calc_ograzhdenie": {"name": "Ограждение / перила", "type": "single", "question": "Введите длину в метрах.\nНапример: 15", "price_per_m": 1800, "desc": "Стойки 40×40×2, поручень Ø50."},
    "calc_zabor":       {"name": "Забор", "type": "single", "question": "Введите длину забора в метрах.\nНапример: 30", "price_per_m": 2200, "desc": "Столбы 60×60×2, лаги 40×20×2."},
    "calc_pokraska":    {"name": "Порошковая покраска", "type": "single", "question": "Введите площадь покраски в м².\nНапример: 8", "price_per_m2": 500, "desc": "Обезжиривание, фосфатирование, полимеризация."},
    "calc_mangal":      {"name": "Мангал", "type": "fixed", "price": 8000, "desc": "Сталь 3 мм (стенки), дно 4 мм."},
    "calc_svarka":      {"name": "Сварочные работы (выезд)", "type": "single", "question": "Введите количество часов работы.\nНапример: 3", "price_per_hour": 1500, "desc": "Ручная дуговая, полуавтомат, аргон."},
}


def main_menu_kb():
    b = InlineKeyboardBuilder()
    b.row(CallbackButton(text="🔧 Услуги", payload="services"), CallbackButton(text="💰 Цены", payload="prices"))
    b.row(CallbackButton(text="🧮 Калькулятор", payload="calc"))
    b.row(CallbackButton(text="📝 Оставить заявку", payload="lead"))
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


def calc_result_kb(total):
    b = InlineKeyboardBuilder()
    if total >= 50000:
        b.row(CallbackButton(text="🎁 Заявка со скидкой 10%", payload="lead"))
    else:
        b.row(CallbackButton(text="📝 Оставить заявку", payload="lead"))
    b.row(CallbackButton(text="📞 Связаться с оператором", payload="contact"))
    b.row(CallbackButton(text="🧮 Ещё расчёт", payload="calc"))
    b.row(CallbackButton(text="⬅ В меню", payload="back_to_menu"))
    return b.as_markup()


def calculate_result(service_key, text):
    service = CALC_SERVICES[service_key]
    cleaned = text.replace(",", ".").replace("х", " ").replace("x", " ").replace("×", " ")
    parts = cleaned.split()
    try:
        numbers = [float(p) for p in parts]
    except ValueError:
        return None, "Не могу распознать числа."

    if service["type"] == "single":
        if len(numbers) < 1:
            return None, "Введите число."
        x = numbers[0]
        if "price_per_m" in service:
            return int(x * service["price_per_m"]), f"{x} м × {service['price_per_m']} ₽/м"
        if "price_per_step" in service:
            return int(x * service["price_per_step"]), f"{x} ступ. × {service['price_per_step']} ₽"
        if "price_per_m2" in service:
            price = 500 if x < 10 else (400 if x < 100 else 300) if service_key == "calc_pokraska" else service["price_per_m2"]
            return int(x * price), f"{x} м² × {price} ₽/м²"
        if "price_per_hour" in service:
            return int(x * service["price_per_hour"]), f"{x} ч × {service['price_per_hour']} ₽/ч"

    if service["type"] == "multi":
        if len(numbers) < 2:
            return None, "Введите два числа."
        a, b = numbers[0], numbers[1]
        area = a * b
        return int(area * service["price_per_m2"]), f"{a} м × {b} м = {area:.2f} м²"

    if service["type"] == "fixed":
        return service["price"], f"от {service['price']} ₽"

    return None, "Не могу посчитать"


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


def get_chat_id(event):
    r = getattr(event.message, "recipient", None)
    if r and getattr(r, "chat_id", None):
        return r.chat_id
    if hasattr(event.message, "chat_id") and event.message.chat_id:
        return event.message.chat_id
    if r and getattr(r, "user_id", None):
        return r.user_id
    return None


@dp.message_created(CommandStart())
async def cmd_start(event: MessageCreated):
    global admin_chat_id
    user_id = event.message.sender.user_id
    if user_id in user_locks:
        return
    user_locks.add(user_id)
    try:
        if ADMIN_ID and str(user_id) == str(ADMIN_ID):
            cid = get_chat_id(event)
            if cid and cid != admin_chat_id:
                admin_chat_id = cid
                logger.info(f"ADMIN chat_id обновлён: {admin_chat_id}")

        name = event.message.sender.first_name or "—"
        logger.info(f"/start user_id={user_id}")
        await notify_admin(f"🆕 Новый пользователь: {name} (ID {user_id})")
        await event.message.answer(TEXT_MENU, attachments=[main_menu_kb()])
    finally:
        user_locks.discard(user_id)


@dp.message_callback()
async def handle_callback(event: MessageCallback):
    global admin_chat_id
    try:
        payload = event.callback.payload
    except AttributeError:
        return
    if not payload:
        return

    user_id = get_real_user_id(event)
    if user_id and user_id in user_locks:
        return
    if user_id:
        user_locks.add(user_id)

    try:
        if ADMIN_ID and str(user_id) == str(ADMIN_ID):
            cid = get_chat_id(event)
            if cid and cid != admin_chat_id:
                admin_chat_id = cid
                logger.info(f"ADMIN chat_id обновлён: {admin_chat_id}")

        name = "—"
        for attr in ("sender", "recipient"):
            obj = getattr(event.message, attr, None)
            if obj and getattr(obj, "first_name", None):
                name = obj.first_name
                break

        if payload in CALC_SERVICES:
            service = CALC_SERVICES[payload]
            if service["type"] == "fixed":
                await event.message.answer(
                    f"🔥 *{service['name']}*\n\nОриентировочно: *от {service['price']} ₽*\n\n_{service.get('desc', '')}_",
                    attachments=[calc_result_kb(service["price"])]
                )
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
        elif payload == "lead":
            if user_id:
                user_states[user_id] = {"step": "waiting_lead"}
            await event.message.answer(TEXT_LEAD_FORM, attachments=[cancel_kb()])
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


@dp.message_created(F.message.body.text)
async def handle_text(event: MessageCreated):
    global admin_chat_id
    text = event.message.body.text.strip()
    text_lower = text.lower()

    if text_lower in ALL_PAYLOADS:
        return

    user_id = event.message.sender.user_id
    if user_id in user_locks:
        return
    user_locks.add(user_id)

    try:
        if ADMIN_ID and str(user_id) == str(ADMIN_ID):
            cid = get_chat_id(event)
            if cid and cid != admin_chat_id:
                admin_chat_id = cid
                logger.info(f"ADMIN chat_id обновлён: {admin_chat_id}")

        name = event.message.sender.first_name or "—"
        logger.info(f"MSG user_id={user_id}: {text}")

        if text_lower == "/whoami":
            cid = get_chat_id(event)
            await event.message.answer(
                f"user_id: `{user_id}`\n"
                f"chat_id: `{cid}`\n"
                f"recipient: `{event.message.recipient}`"
            )
            return
        if text_lower == "/admin_test":
            await notify_admin(f"🔔 Тест от {name} (ID {user_id})")
            await event.message.answer("✅ Отправлено. Проверь MAX и Telegram.")
            return

        if user_id in user_states:
            state = user_states.pop(user_id, None)

            if state and state.get("step") == "waiting_number":
                key = state["service_key"]
                service = CALC_SERVICES[key]
                total, descr = calculate_result(key, text)

                if total is None:
                    await event.message.answer(f"❌ {descr}", attachments=[cancel_kb()])
                    return

                discount = 0.1 if total >= 50000 else 0
                final = int(total * (1 - discount))
                disc_text = f"\n🎁 *Скидка 10%!*\n" if discount else ""
                formatted = f"{final:,}".replace(",", " ")

                await event.message.answer(
                    f"🧮 *{service['name']}*\n\n"
                    f"📐 {descr}\n{disc_text}"
                    f"💰 *~{formatted} ₽*\n\n"
                    f"_Точную стоимость — после замера._",
                    attachments=[calc_result_kb(total)]
                )
                await notify_admin(
                    f"🧮 Расчёт: {service['name']}, {descr}, ~{formatted} ₽ (ID {user_id})"
                )
                return

            if state and state.get("step") == "waiting_lead":
                await notify_admin(f"📝 *ЗАЯВКА!*\n\nОт: {name} (ID `{user_id}`)\n\n{text}")
                await event.message.answer("✅ *Заявка принята!*", attachments=[back_kb()])
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
        elif "заявк" in text_lower:
            user_states[user_id] = {"step": "waiting_lead"}
            await event.message.answer(TEXT_LEAD_FORM, attachments=[cancel_kb()])
        else:
            await event.message.answer(TEXT_FALLBACK, attachments=[main_menu_kb()])
    finally:
        user_locks.discard(user_id)


async def main():
    public_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
    if not public_domain:
        await dp.start_polling(bot)
        return

    try:
        await bot.delete_webhook()
        logger.info("✅ Старые подписки удалены")
    except Exception as e:
        logger.warning(f"⚠️ delete_webhook: {e}")

    await asyncio.sleep(2)

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
