import os
import logging
from maxapi import Bot, Dispatcher, F
from maxapi.filters.command import CommandStart
from maxapi.types import (
    MessageCreated,
    MessageCallback,
    CallbackButton,
    LinkButton,
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

TEXT_FALLBACK = (
    "Пожалуйста, воспользуйтесь кнопками меню ниже 👇"
)

# ---------- КЛАВИАТУРЫ ----------

def main_menu_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="🔧 Услуги", payload="services"),
        CallbackButton(text="💰 Цены", payload="prices"),
    )
    builder.row(
        CallbackButton(text="⏱ Сроки", payload="terms"),
        CallbackButton(text="📞 Оператор", payload="contact"),
    )
    return builder.as_markup()


def contact_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        LinkButton(text="💬 WhatsApp", url="https://wa.me/79159190508")
    )
    builder.row(
        LinkButton(text="✈️ Telegram", url="https://t.me/SKYHITORED")
    )
    builder.row(
        LinkButton(text="📱 Позвонить", url="tel:+79159190508")
    )
    builder.row(
        CallbackButton(text="⬅ Назад", payload="back_to_menu")
    )
    return builder.as_markup()


def back_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="⬅ Назад в меню", payload="back_to_menu")
    )
    return builder.as_markup()


# ---------- ОБРАБОТЧИКИ СООБЩЕНИЙ ----------

@dp.message_created(CommandStart())
async def cmd_start(event: MessageCreated):
    logger.info(f"CMD /start от user_id={event.message.sender.user_id}")
    await event.message.answer(TEXT_MENU, attachments=[main_menu_kb()])


@dp.message_created(F.message.body.text)
async def handle_text(event: MessageCreated):
    text = event.message.body.text.strip().lower()
    logger.info(f"MSG: {text}")

    if "услуг" in text:
        await event.message.answer(TEXT_SERVICES, attachments=[back_kb()])
    elif "цен" in text:
        await event.message.answer(TEXT_PRICES, attachments=[back_kb()])
    elif "срок" in text:
        await event.message.answer(TEXT_TERMS, attachments=[back_kb()])
    elif "оператор" in text or "связаться" in text or "позвонить" in text:
        await event.message.answer(TEXT_CONTACT, attachments=[contact_kb()])
    elif "привет" in text or "здравств" in text:
        await event.message.answer(TEXT_MENU, attachments=[main_menu_kb()])
    else:
        await event.message.answer(TEXT_FALLBACK, attachments=[main_menu_kb()])


# ---------- ОБРАБОТЧИК CALLBACK ----------

@dp.message_callback()
async def handle_callback(event: MessageCallback):
    payload = event.callback.payload
    logger.info(f"CALLBACK: {payload}")

    if payload == "services":
        await event.message.answer(TEXT_SERVICES, attachments=[back_kb()])
    elif payload == "prices":
        await event.message.answer(TEXT_PRICES, attachments=[back_kb()])
    elif payload == "terms":
        await event.message.answer(TEXT_TERMS, attachments=[back_kb()])
    elif payload == "contact":
        await event.message.answer(TEXT_CONTACT, attachments=[contact_kb()])
    elif payload == "back_to_menu":
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
