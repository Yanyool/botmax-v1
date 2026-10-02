import os
import logging
from maxapi import Bot, Dispatcher, F
from maxapi.filters.command import CommandStart
from maxapi.types import BotStarted, MessageCreated
from dotenv import load_dotenv

# Загружаем переменные окружения (для локального тестирования)
load_dotenv()

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен читаем ТОЛЬКО из переменной окружения
MAX_BOT_TOKEN = os.getenv("MAX_BOT_TOKEN")

if not MAX_BOT_TOKEN:
    raise RuntimeError("Переменная MAX_BOT_TOKEN не задана!")

bot = Bot(MAX_BOT_TOKEN)
dp = Dispatcher()

# Тексты ответов
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

TEXT_MENU = (
    "Здравствуйте! Я бот сварочной мастерской СварМастер.\n"
    "Чем могу помочь?"
)

TEXT_FALLBACK = (
    "Я пока не понимаю такие сообщения.\n"
    "Воспользуйтесь кнопками меню или напишите оператору."
)

# Inline-кнопки для меню
# В библиотеке maxapi кнопки создаются через типы.
# Ниже — универсальный способ через отправку клавиатуры.
# Если синтаксис отличается, посмотри примеры: https://love-apples.github.io/maxapi/examples/


@dp.bot_started()
async def bot_started(event: BotStarted):
    """Обработка нажатия кнопки 'Начать'"""
    await bot.send_message(
        chat_id=event.chat_id,
        text=TEXT_MENU
    )


@dp.message_created(CommandStart())
async def hello(event: MessageCreated):
    """Обработка команды /start"""
    await event.message.answer(TEXT_MENU)


@dp.message_created(F.message.body.text)
async def handle_text(event: MessageCreated):
    """Обработка текстовых сообщений (кнопки и fallback)"""
    text = event.message.body.text.strip().lower()

    if "услуг" in text:
        await event.message.answer(TEXT_SERVICES)
    elif "цен" in text:
        await event.message.answer(TEXT_PRICES)
    elif "срок" in text:
        await event.message.answer(TEXT_TERMS)
    elif "связаться" in text or "оператор" in text:
        await event.message.answer(
            "📞 Связаться с оператором:\n\n"
            "WhatsApp: https://wa.me/79159190508\n"
            "Telegram: https://t.me/SKYHITORED\n"
            "Телефон: +7 (915) 919-05-08"
        )
    else:
        await event.message.answer(TEXT_FALLBACK)


async def main():
    """Запуск бота через webhook (для Railway)"""
    # Railway даёт публичный домен в переменной RAILWAY_PUBLIC_DOMAIN
    public_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")

    if public_domain:
        webhook_url = f"https://{public_domain}"
        logger.info(f"Запуск через webhook: {webhook_url}")
        await dp.handle_webhook(bot)
    else:
        # Локальный запуск через polling (для тестирования)
        logger.info("Запуск через polling (локально)")
        await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
    
