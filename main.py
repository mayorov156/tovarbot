import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import ErrorEvent

from config import settings
from database import init_db, get_session
from handlers import user_router, admin_router, callback_router, warehouse_router
from utils import setup_logging

# Настройка логирования
logger = setup_logging()


async def setup_dependencies(dp: Dispatcher):
    """Настройка зависимостей для handlers"""
    # Здесь можно добавить middleware для автоматического внедрения зависимостей
    pass


async def main():
    """Главная функция запуска бота"""
    logger.info("Starting bot...")
    
    # Проверяем токен
    if not settings.BOT_TOKEN:
        logger.error("BOT_TOKEN not found in environment variables")
        return
    
    # Инициализируем базу данных
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return
    
    # Создаем бота и диспетчер
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher(storage=MemoryStorage())
    
    # Настраиваем зависимости
    await setup_dependencies(dp)
    
    # Регистрируем роутеры (специфичные команды должны быть первыми)
    dp.include_router(user_router)
    dp.include_router(admin_router)
    dp.include_router(callback_router)
    dp.include_router(warehouse_router)
    
    # Middleware для автоматического внедрения сессии БД
    @dp.message.middleware()
    @dp.callback_query.middleware()
    async def db_session_middleware(handler, event, data):
        async for session in get_session():
            data['session'] = session
            return await handler(event, data)
    
    # Обработчик ошибок
    @dp.error()
    async def error_handler(event: ErrorEvent):
        # твоя логика логирования
        print(f"Ошибка: {event.exception}")
        return True
    
    # Уведомляем админов о запуске с админ-меню
    from keyboards.inline_keyboards import admin_menu_kb
    for admin_id in settings.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                "🤖 <b>Бот запущен и готов к работе!</b>\n\n"
                "⚙️ Используйте админ-панель для управления:",
                reply_markup=admin_menu_kb()
            )
        except Exception as e:
            logger.warning(f"Failed to notify admin {admin_id}: {e}")
    
    try:
        # Запускаем бота
        logger.info("Bot started successfully")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error during polling: {e}")
    finally:
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")