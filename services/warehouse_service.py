"""Сервис для работы со складом товаров"""

import logging
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.models import Product, Category, User, WarehouseLog, ProductType
from repositories.product_repository import ProductRepository
from repositories.category_repository import CategoryRepository
from repositories.user_repository import UserRepository


logger = logging.getLogger(__name__)


class WarehouseService:
    """Сервис для управления складом"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.product_repo = ProductRepository(session)
        self.category_repo = CategoryRepository(session)
        self.user_repo = UserRepository(session)
    
    async def add_product(
        self,
        name: str,
        category_id: int,
        product_type: str,
        duration: str,
        content: str,
        price: float,
        admin_id: int,
        admin_username: Optional[str] = None
    ) -> Optional[Product]:
        """Добавить новый товар на склад"""
        try:
            # Создаем товар
            product = Product(
                name=name,
                category_id=category_id,
                product_type=product_type,
                duration=duration,
                digital_content=content,
                price=price,
                stock_quantity=1,
                is_active=True
            )
            
            self.session.add(product)
            await self.session.flush()  # Получаем ID продукта
            
            # Логируем добавление
            await self._log_warehouse_action(
                product_id=product.id,
                admin_id=admin_id,
                admin_username=admin_username,
                action="add_product",
                quantity=1,
                description=f"Добавлен товар: {name} ({product_type})"
            )
            
            await self.session.commit()
            
            # Перезагружаем товар с отношениями
            await self.session.refresh(product)
            stmt = select(Product).options(selectinload(Product.category)).where(Product.id == product.id)
            result = await self.session.execute(stmt)
            product = result.scalar_one()
            
            logger.info(f"WAREHOUSE: Added product '{name}' (ID: {product.id}) by admin {admin_id}")
            return product
            
        except Exception as e:
            logger.error(f"Error adding product: {e}")
            await self.session.rollback()
            return None
    
    async def give_product(
        self,
        product_id: int,
        recipient_id: int,
        recipient_username: Optional[str],
        admin_id: int,
        admin_username: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[Product]]:
        """
        Выдать товар пользователю
        
        Returns:
            (success, content, updated_product)
        """
        try:
            # Получаем товар
            product = await self.product_repo.get_by_id(product_id)
            if not product:
                return False, None, None
            
            # Проверяем наличие
            if not product.is_unlimited and product.stock_quantity <= 0:
                return False, None, None
            
            # Получаем содержимое товара
            content = product.digital_content
            if not content:
                return False, None, None
            
            # Уменьшаем остаток (если товар не безлимитный)
            if not product.is_unlimited:
                product.stock_quantity -= 1
            
            # Увеличиваем счетчик продаж
            product.total_sold += 1
            
            # Логируем выдачу
            await self._log_warehouse_action(
                product_id=product_id,
                admin_id=admin_id,
                admin_username=admin_username,
                recipient_id=recipient_id,
                recipient_username=recipient_username,
                action="give_product",
                quantity=1,
                delivered_content=content,
                description=f"Выдан товар: {product.name}"
            )
            
            await self.session.commit()
            await self.session.refresh(product)
            
            logger.info(
                f"WAREHOUSE: Admin {admin_id} gave product '{product.name}' "
                f"to user {recipient_id} (@{recipient_username})"
            )
            
            return True, content, product
            
        except Exception as e:
            logger.error(f"Error giving product: {e}")
            await self.session.rollback()
            return False, None, None
    
    async def get_available_products(self) -> List[Product]:
        """Получить товары доступные для выдачи"""
        return await self.product_repo.get_available_products()
    
    async def get_categories(self) -> List[Category]:
        """Получить все активные категории"""
        return await self.category_repo.get_active_categories()
    
    async def find_user_by_username_or_id(self, identifier: str) -> Optional[User]:
        """Найти пользователя по username или ID"""
        try:
            # Пробуем как ID
            if identifier.isdigit():
                user_id = int(identifier)
                return await self.user_repo.get_by_id(user_id)
            
            # Пробуем как username
            return await self.user_repo.get_by_username(identifier)
            
        except Exception as e:
            logger.error(f"Error finding user: {e}")
            return None
    
    async def validate_product_data(
        self,
        name: str,
        category_id: int,
        product_type: str,
        duration: str,
        content: str,
        price: float
    ) -> Tuple[bool, Optional[str]]:
        """Валидировать данные товара"""
        
        # Проверяем имя
        if not name or len(name.strip()) < 3:
            return False, "Название товара должно содержать минимум 3 символа"
        
        # Проверяем категорию
        category = await self.category_repo.get_by_id(category_id)
        if not category:
            return False, "Категория не найдена"
        
        # Проверяем тип товара
        valid_types = [t.value for t in ProductType]
        if product_type not in valid_types:
            return False, "Неверный тип товара"
        
        # Проверяем длительность
        if not duration or len(duration.strip()) < 1:
            return False, "Длительность не может быть пустой"
        
        # Проверяем содержимое
        if not content or len(content.strip()) < 1:
            return False, "Содержимое товара не может быть пустым"
        
        # Проверяем формат содержимого для аккаунтов
        if product_type == ProductType.ACCOUNT.value:
            if ":" not in content:
                return False, "Для аккаунта используйте формат 'логин:пароль'"
        
        # Проверяем цену
        if price <= 0:
            return False, "Цена должна быть больше 0"
        
        if price > 100000:
            return False, "Цена не может превышать 100,000₽"
        
        return True, None
    
    async def _log_warehouse_action(
        self,
        product_id: int,
        admin_id: int,
        action: str,
        quantity: int = 1,
        admin_username: Optional[str] = None,
        recipient_id: Optional[int] = None,
        recipient_username: Optional[str] = None,
        delivered_content: Optional[str] = None,
        description: Optional[str] = None
    ):
        """Записать действие в лог склада"""
        log_entry = WarehouseLog(
            product_id=product_id,
            admin_id=admin_id,
            admin_username=admin_username,
            recipient_id=recipient_id,
            recipient_username=recipient_username,
            action=action,
            quantity=quantity,
            delivered_content=delivered_content,
            description=description
        )
        
        self.session.add(log_entry)
    
    async def get_warehouse_history(self, limit: int = 50) -> List[WarehouseLog]:
        """Получить историю действий на складе"""
        stmt = (
            select(WarehouseLog)
            .options(selectinload(WarehouseLog.product))
            .order_by(WarehouseLog.created_at.desc())
            .limit(limit)
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_product_with_category(self, product_id: int) -> Optional[Product]:
        """Получить товар с загруженной категорией"""
        stmt = (
            select(Product)
            .options(selectinload(Product.category))
            .where(Product.id == product_id)
        )
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create_category(
        self,
        name: str,
        description: Optional[str],
        admin_id: int,
        admin_username: Optional[str] = None
    ) -> Optional[Category]:
        """Создать новую категорию"""
        try:
            # Проверяем, существует ли категория с таким именем
            existing = await self.category_repo.get_by_name(name)
            if existing:
                return None
            
            # Создаем категорию
            category = Category(
                name=name,
                description=description or "",
                is_active=True,
                sort_order=0
            )
            
            self.session.add(category)
            await self.session.flush()
            
            # Логируем создание
            await self._log_warehouse_action(
                product_id=0,  # Для категорий используем 0
                admin_id=admin_id,
                admin_username=admin_username,
                action="create_category",
                quantity=1,
                description=f"Создана категория: {name}"
            )
            
            await self.session.commit()
            await self.session.refresh(category)
            
            logger.info(f"WAREHOUSE: Created category '{name}' (ID: {category.id}) by admin {admin_id}")
            return category
            
        except Exception as e:
            logger.error(f"Error creating category: {e}")
            await self.session.rollback()
            return None
    
    async def validate_category_data(
        self,
        name: str,
        description: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """Валидировать данные категории"""
        
        # Проверяем имя
        if not name or len(name.strip()) < 2:
            return False, "Название категории должно содержать минимум 2 символа"
        
        # Проверяем уникальность имени
        existing = await self.category_repo.get_by_name(name.strip())
        if existing:
            return False, "Категория с таким названием уже существует"
        
        return True, None
    
    async def has_categories(self) -> bool:
        """Проверить, есть ли хотя бы одна категория"""
        categories = await self.get_categories()
        return len(categories) > 0