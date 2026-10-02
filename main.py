import os
import logging
from maxapi import Bot, Dispatcher, F
from maxapi.filters.command import CommandStart
from maxapi.types import BotStarted, MessageCreated
from maxapi.enums.update import UpdateType
from dotenv import load_dotenv

# Загружаем переменные окружения (для локального теста)
load_dotenv()

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Переменные окружения
MAX_BOT_TOKEN = os.getenv("MAX_BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "svarmaster-secret-2025")

if not MAX_BOT_TOKEN:
    raise RuntimeError("Переменная MAX_BOT_TOKEN не задана!")

bot = Bot(MAX_BOT_TOKEN)
dp = Dispatcher()

# ---------- ТЕКСТЫ ОТВЕТОВ ----------
TEXT_MENU = (
    "Здравствуйте! Я бот сварочной мастерской СварМастер.\n"
    "Чем могу помочь?\n\n"
    "Напишите:\n"
    "• *услуги* — список услуг\n"
    "• *цены* — прайс-лист\n"
    "• *сроки* — сроки изготовления\n"
    "• *оператор* — связаться с нами"
)

TEXT_SERVICES = (
    "🔧 Наши услуги:\n\n"
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
    "💰 Цены:\n\n"
    "• Сварочные работы — от 1500 ₽/час\n"
    "• Ворота — от 4500 ₽/м²\n"
    "• Навесы — от 3800 ₽/м²\n"
    "• Лестницы — от 2200 ₽/ступень\n"
    "• Порошковая покраска — от 1200 ₽/м²\n\n"
    "Точная стоимость — после замера."
)

TEXT_TERMS = (
    "⏱️ Сроки изготовления:\n\n"
    "• Стандартный заказ — 5–10 рабочих дней\n"
    "• Срочный заказ — от 2 дней (наценка 30%)\n\n"
    "Сроки фиксируются в договоре."
)

TEXT_CONTACT = (
    "📞 Связаться с оператором:\n\n"
    "WhatsApp: https://wa.me/79159190508\n"
    "Telegram: https://t.me/SKYHITORED\n"
    "Телефон: +7 (915) 919-05-08"
)

TEXT_FALLBACK = (
    "Я пока не понимаю такие сообщения.\n\n"
    "Напишите:\n"
    "• *услуги*\n"
    "• *цены*\n"
    "• *сроки*\n"
    "• *оператор*"
)

# ---------- ОБРАБОТЧИКИ ----------

@dp.bot_started()
async def bot_started(event: BotStarted):
    """Нажатие кнопки 'Старт'"""
    logger.info(f"BOT_STARTED от chat_id={event.chat_id}")
    await bot.send_message(chat_id=event.chat_id, text=TEXT_MENU)


@dp.message_created(CommandStart())
async def cmd_start(event: MessageCreated):
    """Команда /start"""
    logger.info(f"CMD /start от user_id={event.message.sender.user_id}")
    await event.message.answer(TEXT_MENU)


@dp.message_created(F.message.body.text)
async def handle_text(event: MessageCreated):
    """Обработка текстовых сообщений"""
    text = event.message.body.text.strip().lower()
    logger.info(f"MSG: {text}")

    if "услуг" in text:
        await event.message.answer(TEXT_SERVICES)
    elif "цен" in text:
        await event.message.answer(TEXT_PRICES)
    elif "срок" in text:
        await event.message.answer(TEXT_TERMS)
    elif "оператор" in text or "связаться" in text or "позвонить" in text:
        await event.message.answer(TEXT_CONTACT)
    elif "привет" in text or "здравств" in text or "start" in text:
        await event.message.answer(TEXT_MENU)
    else:
        await event.message.answer(TEXT_FALLBACK)


# ---------- ЗАПУСК ----------

async def main():
    """Запуск бота через webhook (для Railway)"""
    public_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")

    if not public_domain:
        logger.error("RAILWAY_PUBLIC_DOMAIN не задан! Запуск через polling...")
        await dp.start_polling(bot)
        return

    webhook_url = f"https://{public_domain}/webhook"
    logger.info(f"Регистрирую webhook: {webhook_url}")

    # 1. Подписываем бота на события MAX
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

    # 2. Запускаем сервер, который слушает /webhook
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
