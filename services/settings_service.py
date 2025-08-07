"""
Сервис для работы с системными настройками
"""

from typing import Optional, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import SystemSetting
import json
import logging

logger = logging.getLogger(__name__)


class SettingsService:
    """Сервис для управления системными настройками"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_setting(self, key: str, default: Any = None) -> Any:
        """Получить значение настройки по ключу"""
        try:
            result = await self.session.execute(
                select(SystemSetting).where(SystemSetting.key == key)
            )
            setting = result.scalar_one_or_none()
            
            if not setting:
                return default
            
            # Преобразуем значение в нужный тип
            return self._convert_value(setting.value, setting.value_type)
            
        except Exception as e:
            logger.error(f"Error getting setting {key}: {e}")
            return default
    
    async def set_setting(
        self, 
        key: str, 
        value: Any, 
        description: str = None, 
        category: str = "general",
        is_editable: bool = True
    ) -> bool:
        """Установить значение настройки"""
        try:
            # Определяем тип значения
            value_type = self._get_value_type(value)
            value_str = self._value_to_string(value)
            
            # Проверяем, существует ли настройка
            result = await self.session.execute(
                select(SystemSetting).where(SystemSetting.key == key)
            )
            setting = result.scalar_one_or_none()
            
            if setting:
                # Обновляем существующую настройку
                setting.value = value_str
                setting.value_type = value_type
                if description:
                    setting.description = description
            else:
                # Создаем новую настройку
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
            return True
            
        except Exception as e:
            logger.error(f"Error setting {key}: {e}")
            await self.session.rollback()
            return False
    
    async def get_settings_by_category(self, category: str) -> list[dict]:
        """Получить все настройки по категории"""
        try:
            result = await self.session.execute(
                select(SystemSetting).where(SystemSetting.category == category)
            )
            settings = result.scalars().all()
            
            return [
                {
                    "key": setting.key,
                    "value": self._convert_value(setting.value, setting.value_type),
                    "description": setting.description,
                    "is_editable": setting.is_editable,
                    "value_type": setting.value_type
                }
                for setting in settings
            ]
            
        except Exception as e:
            logger.error(f"Error getting settings for category {category}: {e}")
            return []
    
    async def delete_setting(self, key: str) -> bool:
        """Удалить настройку"""
        try:
            result = await self.session.execute(
                select(SystemSetting).where(SystemSetting.key == key)
            )
            setting = result.scalar_one_or_none()
            
            if setting:
                await self.session.delete(setting)
                await self.session.commit()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting setting {key}: {e}")
            await self.session.rollback()
            return False
    
    def _get_value_type(self, value: Any) -> str:
        """Определить тип значения"""
        if isinstance(value, bool):
            return "bool"
        elif isinstance(value, int):
            return "int"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, (list, dict)):
            return "json"
        else:
            return "string"
    
    def _value_to_string(self, value: Any) -> str:
        """Конвертировать значение в строку для хранения"""
        if isinstance(value, (list, dict)):
            return json.dumps(value, ensure_ascii=False)
        else:
            return str(value)
    
    def _convert_value(self, value_str: str, value_type: str) -> Any:
        """Конвертировать строковое значение в нужный тип"""
        try:
            if value_type == "bool":
                return value_str.lower() in ("true", "1", "yes", "on")
            elif value_type == "int":
                return int(value_str)
            elif value_type == "float":
                return float(value_str)
            elif value_type == "json":
                return json.loads(value_str)
            else:
                return value_str
        except Exception as e:
            logger.error(f"Error converting value '{value_str}' to type {value_type}: {e}")
            return value_str
    
    # Специальные методы для работы с мануалом
    async def get_global_manual_url(self) -> Optional[str]:
        """Получить URL глобального мануала"""
        return await self.get_setting("global_manual_url", None)
    
    async def set_global_manual_url(self, manual_url: str) -> bool:
        """Установить URL глобального мануала"""
        return await self.set_setting(
            "global_manual_url",
            manual_url,
            description="Единая ссылка на инструкцию для всех товаров",
            category="manual",
            is_editable=True
        )
    
    async def get_manual_enabled(self) -> bool:
        """Проверить, включен ли мануал"""
        return await self.get_setting("manual_enabled", True)
    
    async def set_manual_enabled(self, enabled: bool) -> bool:
        """Включить/выключить отправку мануала"""
        return await self.set_setting(
            "manual_enabled",
            enabled,
            description="Отправлять ли инструкцию при выдаче товаров",
            category="manual",
            is_editable=True
        )
    
    async def initialize_default_settings(self):
        """Инициализация настроек по умолчанию"""
        defaults = [
            {
                "key": "global_manual_url",
                "value": "",
                "description": "Единая ссылка на инструкцию для всех товаров",
                "category": "manual"
            },
            {
                "key": "manual_enabled", 
                "value": True,
                "description": "Отправлять ли инструкцию при выдаче товаров",
                "category": "manual"
            }
        ]
        
        for default_setting in defaults:
            # Проверяем, не существует ли уже такая настройка
            existing = await self.get_setting(default_setting["key"])
            if existing is None:
                await self.set_setting(
                    default_setting["key"],
                    default_setting["value"],
                    default_setting["description"],
                    default_setting["category"]
                )