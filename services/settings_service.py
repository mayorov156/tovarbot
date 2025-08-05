"""Сервис для работы с настройками системы"""

import logging
from typing import Optional, List, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import SystemSetting

logger = logging.getLogger(__name__)


class SettingsService:
    """Сервис для управления настройками системы"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_setting(self, key: str, default: Any = None) -> Any:
        """Получить значение настройки"""
        try:
            stmt = select(SystemSetting).where(SystemSetting.key == key)
            result = await self.session.execute(stmt)
            setting = result.scalar_one_or_none()
            
            if not setting:
                return default
            
            # Конвертируем значение в соответствующий тип
            return self._convert_value(setting.value, setting.value_type)
            
        except Exception as e:
            logger.error(f"Error getting setting {key}: {e}")
            return default
    
    async def set_setting(self, key: str, value: Any, description: str = None, category: str = "general", is_editable: bool = True) -> bool:
        """Установить значение настройки"""
        try:
            # Определяем тип значения
            value_type = self._get_value_type(value)
            value_str = str(value)
            
            # Ищем существующую настройку
            stmt = select(SystemSetting).where(SystemSetting.key == key)
            result = await self.session.execute(stmt)
            setting = result.scalar_one_or_none()
            
            if setting:
                # Обновляем существующую
                setting.value = value_str
                setting.value_type = value_type
                if description:
                    setting.description = description
            else:
                # Создаем новую
                setting = SystemSetting(
                    key=key,
                    value=value_str,
                    value_type=value_type,
                    description=description,
                    category=category,
                    is_editable=is_editable
                )
                self.session.add(setting)
            
            await self.session.commit()
            logger.info(f"Setting {key} updated to {value}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting {key}: {e}")
            await self.session.rollback()
            return False
    
    async def get_editable_settings(self, category: str = None) -> List[SystemSetting]:
        """Получить список редактируемых настроек"""
        try:
            stmt = select(SystemSetting).where(SystemSetting.is_editable == True)
            
            if category:
                stmt = stmt.where(SystemSetting.category == category)
                
            stmt = stmt.order_by(SystemSetting.category, SystemSetting.key)
            
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error(f"Error getting editable settings: {e}")
            return []
    
    async def get_setting_by_id(self, setting_id: int) -> Optional[SystemSetting]:
        """Получить настройку по ID"""
        try:
            stmt = select(SystemSetting).where(SystemSetting.id == setting_id)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting setting by id {setting_id}: {e}")
            return None
    
    async def get_categories(self) -> List[str]:
        """Получить список категорий настроек"""
        try:
            stmt = select(SystemSetting.category).distinct().where(SystemSetting.is_editable == True)
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error(f"Error getting setting categories: {e}")
            return []
    
    async def initialize_default_settings(self) -> None:
        """Инициализировать настройки по умолчанию"""
        default_settings = [
            {
                "key": "referral_reward_percent",
                "value": 10.0,
                "description": "Процент реферальной награды",
                "category": "referral",
                "is_editable": True
            },
            {
                "key": "support_username",
                "value": "your_support_username",
                "description": "Username службы поддержки (без @)",
                "category": "contacts",
                "is_editable": True
            },
            {
                "key": "earning_channel",
                "value": "https://t.me/your_earning_channel",
                "description": "Ссылка на канал заработка",
                "category": "contacts",
                "is_editable": True
            },
            {
                "key": "welcome_message",
                "value": "Добро пожаловать в наш магазин! 🛍",
                "description": "Приветственное сообщение",
                "category": "messages",
                "is_editable": True
            },
            {
                "key": "min_withdrawal_amount",
                "value": 100.0,
                "description": "Минимальная сумма для вывода средств",
                "category": "financial",
                "is_editable": True
            }
        ]
        
        for setting_data in default_settings:
            # Проверяем, существует ли уже такая настройка
            existing = await self.get_setting(setting_data["key"])
            if existing is None:
                await self.set_setting(**setting_data)
    
    def _convert_value(self, value_str: str, value_type: str) -> Any:
        """Конвертировать строковое значение в нужный тип"""
        try:
            if value_type == "int":
                return int(value_str)
            elif value_type == "float":
                return float(value_str)
            elif value_type == "bool":
                return value_str.lower() in ("true", "1", "yes", "on")
            else:  # string
                return value_str
        except (ValueError, TypeError):
            return value_str
    
    def _get_value_type(self, value: Any) -> str:
        """Определить тип значения"""
        if isinstance(value, bool):
            return "bool"
        elif isinstance(value, int):
            return "int"
        elif isinstance(value, float):
            return "float"
        else:
            return "string"