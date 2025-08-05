import logging
from loguru import logger
import sys
from pathlib import Path


class InterceptHandler(logging.Handler):
    """Перехватчик для стандартного логирования Python"""
    
    def emit(self, record):
        # Получаем соответствующий уровень Loguru
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Находим caller из стека
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging():
    """Настройка системы логирования"""
    
    # Создаем папку для логов
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Удаляем стандартный обработчик loguru
    logger.remove()
    
    # Добавляем вывод в консоль
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    # Добавляем запись в файл
    logger.add(
        logs_dir / "bot.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="1 day",
        retention="7 days",
        compression="zip"
    )
    
    # Добавляем отдельный файл для действий пользователей
    logger.add(
        logs_dir / "user_actions.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {extra[user_id]} | {extra[action]} | {message}",
        filter=lambda record: "user_action" in record["extra"],
        rotation="1 day",
        retention="30 days"
    )
    
    # Перехватываем стандартное логирование Python
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    return logger


def log_user_action(user_id: int, action: str, details: str = ""):
    """Логирование действий пользователя"""
    logger.bind(user_action=True, user_id=user_id, action=action).info(details or action)