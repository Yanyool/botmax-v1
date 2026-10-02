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

if not MAX_BOT_TOKEN:
    raise RuntimeError("Переменная MAX_BOT_TOKEN не задана!")

bot = Bot(MAX_BOT_TOKEN)
dp = Dispatcher()

# Хранилище состояний пользователей (для калькулятора)
user_states = {}

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

TEXT_CONTACT = (
    "📞 *Связаться с оператором:*\n\n"
    "Выберите удобный способ:"
)

TEXT_WA = (
    "💬 *WhatsApp*\n\n"
    "Напишите нам: https://wa.me/79159190508"
)

TEXT_TG = (
    "✈️ *Telegram*\n\n"
    "Напишите нам: https://t.me/SKYHITORED"
)

TEXT_MAX = (
    "📱 *MAX Messenger*\n\n"
    "Напишите нам: https://max.ru/u/f9LHodD0cOLt4DlpXkQuKcUA-rwanDwWOPRvmBInmJ1e_HlzRa6DjU1K1gU"
)

TEXT_CALL = (
    "📱 *Позвонить*\n\n"
    "Телефон: +7 (915) 919-05-08"
)

TEXT_CALC_INTRO = (
    "🧮 *Калькулятор стоимости*\n\n"
    "Выберите услугу — я посчитаю примерную цену:"
)

TEXT_FALLBACK = (
    "Пожалуйста, воспользуйтесь кнопками меню ниже 👇"
)

# ---------- УСЛУГИ ДЛЯ КАЛЬКУЛЯТОРА ----------
CALC_SERVICES = {
    "calc_vorota": {
        "name": "Откатные ворота",
        "unit": "м²",
        "price": 4500,
        "question": "Введите площадь ворот в м² (ширина × высота).\nНапример: 4.5",
    },
    "calc_naves": {
        "name": "Навес",
        "unit": "м²",
        "price": 3800,
        "question": "Введите площадь навеса в м² (длина × ширина).\nНапример: 20",
    },
    "calc_lestnica": {
        "name": "Лестница",
        "unit": "ступеней",
        "price": 2200,
        "question": "Введите количество ступеней.\nНапример: 10",
    },
    "calc_ograzhdenie": {
        "name": "Ограждение / перила",
        "unit": "пог. м",
        "price": 1800,
        "question": "Введите длину ограждения в метрах.\nНапример: 15",
    },
    "calc_pokraska": {
        "name": "Порошковая покраска",
        "unit": "м²",
        "price": 1200,
        "question": "Введите площадь покраски в м².\nНапример: 8",
    },
    "calc_mangal": {
        "name": "Мангал / барбекю",
        "unit": "шт.",
        "price": 8000,
        "question": None,  # фикс-цена
    },
}

# ---------- КЛАВИАТУРЫ ----------

def main_menu_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="🔧 Услуги", payload="services"),
        CallbackButton(text="💰 Цены", payload="prices"),
    )
    builder.row(
        CallbackButton(text="🧮 Калькулятор", payload="calc"),
    )
    builder.row(
        CallbackButton(text="⏱ Сроки", payload="terms"),
        CallbackButton(text="📞 Оператор", payload="contact"),
    )
    return builder.as_markup()


def contact_kb():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="💬 WhatsApp", payload="show_wa"))
    builder.row(CallbackButton(text="✈️ Telegram", payload="show_tg"))
    builder.row(CallbackButton(text="📱 MAX Messenger", payload="show_max"))
    builder.row(CallbackButton(text="📞 Позвонить", payload="show_call"))
    builder.row(CallbackButton(text="⬅ Назад", payload="back_to_menu"))
    return builder.as_markup()


def back_kb():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="⬅ Назад в меню", payload="back_to_menu"))
    return builder.as_markup()


def calculator_kb():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="🚪 Откатные ворота", payload="calc_vorota"))
    builder.row(CallbackButton(text="🏠 Навес", payload="calc_naves"))
    builder.row(CallbackButton(text="🪜 Лестница", payload="calc_lestnica"))
    builder.row(CallbackButton(text="🛡 Ограждение", payload="calc_ograzhdenie"))
    builder.row(CallbackButton(text="🎨 Покраска", payload="calc_pokraska"))
    builder.row(CallbackButton(text="🔥 Мангал", payload="calc_mangal"))
    builder.row(CallbackButton(text="⬅ Назад", payload="back_to_menu"))
    return builder.as_markup()


def cancel_kb():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="❌ Отмена", payload="back_to_menu"))
    return builder.as_markup()


def calc_result_kb():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="📞 Связаться с оператором", payload="contact"))
    builder.row(CallbackButton(text="🧮 Ещё расчёт", payload="calc"))
    builder.row(CallbackButton(text="⬅ В меню", payload="back_to_menu"))
    return builder.as_markup()


# ---------- ОБРАБОТЧИКИ СООБЩЕНИЙ ----------

@dp.message_created(CommandStart())
async def cmd_start(event: MessageCreated):
    logger.info(f"CMD /start от user_id={event.message.sender.user_id}")
    await event.message.answer(TEXT_MENU, attachments=[main_menu_kb()])


@dp.message_created(F.message.body.text)
async def handle_text(event: MessageCreated):
    text = event.message.body.text.strip()
    text_lower = text.lower()
    user_id = event.message.sender.user_id
    logger.info(f"MSG: {text}")

    # Сначала проверяем — может пользователь вводит число для калькулятора
    if user_id in user_states and user_states[user_id].get("step") == "waiting_number":
        try:
            number = float(text.replace(",", "."))
            service_key = user_states[user_id]["service_key"]
            service = CALC_SERVICES[service_key]
            total = int(number * service["price"])

            await event.message.answer(
                f"🧮 *Расчёт для: {service['name']}*\n\n"
                f"• Количество: {number} {service['unit']}\n"
                f"• Цена за единицу: {service['price']} ₽\n"
                f"• *Примерная стоимость: ~{total} ₽*\n\n"
                f"_Точную стоимость назовём после замера._",
                attachments=[calc_result_kb()]
            )
            del user_states[user_id]
            return
        except ValueError:
            await event.message.answer(
                "Пожалуйста, введите число.\n"
                "Например: `4.5` или `20`",
                attachments=[cancel_kb()]
            )
            return

    # Обычные команды
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


# ---------- ОБРАБОТЧИК CALLBACK ----------

@dp.message_callback()
async def handle_callback(event: MessageCallback):
    payload = event.callback.payload
    user_id = event.message.sender.user_id
    logger.info(f"CALLBACK: {payload} от user_id={user_id}")

    # Калькулятор: выбор услуги
    if payload in CALC_SERVICES:
        service = CALC_SERVICES[payload]
        if service["question"] is None:
            # Фикс-цена (мангал)
            await event.message.answer(
                f"🔥 *{service['name']}*\n\n"
                f"Примерная стоимость: *от {service['price']} ₽*\n\n"
                f"_Точную цену назовём после обсуждения._",
                attachments=[calc_result_kb()]
            )
        else:
            # Запрашиваем число
            user_states[user_id] = {
                "service_key": payload,
                "step": "waiting_number"
            }
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
        # Чистим состояние, если было
        if user_id in user_states:
            del user_states[user_id]
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
        bot=bot,
        host="0.0.0.0",
        port=8080,
        path="/webhook",
        secret=WEBHOOK_SECRET
    )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
