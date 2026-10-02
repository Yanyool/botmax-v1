import os
import logging
from maxapi import Bot, Dispatcher, F
from maxapi.filters.command import CommandStart
from maxapi.types import BotStarted, MessageCreated
from maxapi.enums.update import UpdateType
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен и секрет
MAX_BOT_TOKEN = os.getenv("MAX_BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "svarmaster-secret-2025")

if not MAX_BOT_TOKEN:
    raise RuntimeError("Переменная MAX_BOT_TOKEN не задана!")

bot = Bot(MAX_BOT_TOKEN)
dp = Dispatcher()

# --- Тексты ответов (без изменений) ---
TEXT_SERVICES = "🔧 Наши услуги:\n\n• Сварочные работы\n• Ворота и калитки\n• Навесы и козырьки\n• Лестницы и перила\n• Порошковая покраска\n• Мебель из металла\n• Ограждения и заборы\n• Изготовление на заказ"
TEXT_PRICES = "💰 Цены:\n\n• Сварочные работы — от 1500 ₽/час\n• Ворота — от 4500 ₽/м²\n• Навесы — от 3800 ₽/м²\n• Лестницы — от 2200 ₽/ступень\n• Порошковая покраска — от 1200 ₽/м²\n\nТочная стоимость — после замера."
TEXT_TERMS = "⏱️ Сроки изготовления:\n\n• Стандартный заказ — 5–10 рабочих дней\n• Срочный заказ — от 2 дней (наценка 30%)\n\nСроки фиксируются в договоре."
TEXT_MENU = "Здравствуйте! Я бот сварочной мастерской СварМастер.\nЧем могу помочь?"
TEXT_FALLBACK = "Я пока не понимаю такие сообщения.\nВоспользуйтесь кнопками меню или напишите оператору."

@dp.bot_started()
async def bot_started(event: BotStarted):
    await bot.send_message(chat_id=event.chat_id, text=TEXT_MENU)

@dp.message_created(CommandStart())
async def hello(event: MessageCreated):
    await event.message.answer(TEXT_MENU)

@dp.message_created(F.message.body.text)
async def handle_text(event: MessageCreated):
    text = event.message.body.text.strip().lower()
    if "услуг" in text:
        await event.message.answer(TEXT_SERVICES)
    elif "цен" in text:
        await event.message.answer(TEXT_PRICES)
    elif "срок" in text:
        await event.message.answer(TEXT_TERMS)
    elif "связаться" in text or "оператор" in text:
        await event.message.answer("📞 Связаться с оператором:\n\nWhatsApp: https://wa.me/79159190508\nTelegram: https://t.me/SKYHITORED\nТелефон: +7 (915) 919-05-08")
    else:
        await event.message.answer(TEXT_FALLBACK)

async def main():
    public_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
    if not public_domain:
        logger.error("RAILWAY_PUBLIC_DOMAIN не задан!")
        return

    webhook_url = f"https://{public_domain}"
    logger.info(f"Запуск через webhook: {webhook_url}")

    # 1. СНАЧАЛА ПОДПИСЫВАЕМ БОТА НА ВЕБХУК
    await bot.subscribe_webhook(
        url=webhook_url,
        update_types=[
            UpdateType.MESSAGE_CREATED,
            UpdateType.BOT_STARTED,
            UpdateType.MESSAGE_CALLBACK,
        ],
        secret=WEBHOOK_SECRET
    )

    # 2. ЗАТЕМ ЗАПУСКАЕМ СЕРВЕР
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
